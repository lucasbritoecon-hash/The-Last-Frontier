"""
Busca a mediana do Focus ANUAL pro IPCA (Boletim Focus, API Olinda/BCB,
recurso "ExpectativasMercadoAnuais"), paginando com "$skip" pra trazer o
historico completo desde o inicio da serie (~2000) -- uma unica chamada com
"$top=10000" trunca silenciosamente e so devolve os ultimos anos. Gera dois
formatos no mesmo JSON: "series" (so a pesquisa mais recente por ano de
referencia -- usado no grafico "Expectativas x Selic" ja existente) e
"historico_por_ano" (TODAS as pesquisas de cada ano de referencia, ordenadas
por data -- usado pra mostrar como a expectativa do mercado foi
mudando/sendo revisada ao longo do tempo, ate o ano fechar). Gera
data/expectativas_anual_data.json, no mesmo padrao dos outros paineis do
CIEM (updated_at / had_failure / series).

Nao confundir com scripts/focus_mensal.py (recurso "ExpectativaMercadoMensais",
mediana POR MES DE REFERENCIA -- usado no grafico de IPCA x Meta).

Rodar:
    python scripts/fetch_expectativas_anual.py

Gerado por GitHub Actions 1x por dia (.github/workflows/update-data.yml).
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_JSON = REPO_ROOT / "data" / "expectativas_anual_data.json"

URL_FOCUS_ANUAL = (
    "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"
    "ExpectativasMercadoAnuais"
)

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; CIEM-dashboard/1.0; +https://github.com/lucasbritoecon-hash)",
}

# mesma janela padrao usada em focus_mensal.py (ultimos 30 dias de pesquisa)
BASE_CALCULO = 0


def _buscar_pagina_focus(skip, top=10000):
    params = {
        "$filter": "Indicador eq 'IPCA'",
        "$orderby": "Data asc",
        "$skip": skip,
        "$top": top,
        "$format": "json",
        "$select": "Indicador,Data,DataReferencia,Mediana,baseCalculo",
    }
    resp = requests.get(
        URL_FOCUS_ANUAL,
        params=urlencode(params, quote_via=quote),
        headers=HEADERS,
        timeout=60,
    )
    try:
        resp.raise_for_status()
    except requests.HTTPError:
        print(f"Corpo da resposta ({resp.status_code}): {resp.text[:1000]}")
        raise
    return resp.json()["value"]


def buscar_focus_anual_ipca(base_calculo: int = BASE_CALCULO):
    """Busca o Focus anual (IPCA) -- PAGINADO -- e devolve dois dicts:

    - mais_recente: {"YYYY": (mediana, data_pesquisa)} so com a pesquisa MAIS
      RECENTE de cada ano de referencia -- usado no grafico "Expectativas x
      Selic" ja existente (compara ano a ano, sem granularidade de tempo).
    - historico: {"YYYY": [(data_pesquisa, mediana), ...]} com TODAS as
      pesquisas de cada ano de referencia, ordenadas por data -- usado pra
      mostrar como a expectativa foi mudando ao longo do tempo (revisao).

    O Focus anual e publicado todo dia util desde ~2000, com varios anos de
    referencia simultaneos (o "$top" maximo da API Olinda e 10000 linhas por
    chamada) -- pedir tudo numa unica chamada, ordenado por data decrescente,
    trunca silenciosamente o historico mais antigo (fica so nos ultimos ~8
    anos). Aqui pagina com "$skip" ate a API parar de devolver linhas, pra
    trazer a serie completa desde o inicio.
    """
    valores = []
    skip = 0
    top = 10000
    while True:
        pagina = _buscar_pagina_focus(skip, top)
        valores.extend(pagina)
        print(f"  -> pagina skip={skip}: {len(pagina)} linhas (total ate agora: {len(valores)}).")
        if len(pagina) < top:
            break
        skip += top

    valores = [
        item for item in valores
        if item.get("baseCalculo") in (base_calculo, str(base_calculo))
    ]

    historico = {}
    for item in valores:
        ano_ref = item["DataReferencia"]  # ja vem como "YYYY"
        data_pesquisa = item["Data"]
        mediana = item["Mediana"]
        if mediana is None:
            continue
        historico.setdefault(ano_ref, []).append((data_pesquisa, mediana))

    for ano in historico:
        historico[ano].sort(key=lambda par: par[0])

    mais_recente = {
        ano: (registros[-1][1], registros[-1][0])  # (mediana, data_pesquisa)
        for ano, registros in historico.items()
    }

    return mais_recente, historico


def horizonte_longo_mensal(historico):
    """Recebe {"YYYY": [(data_pesquisa, mediana), ...], ...} (todo o
    historico Focus) e devolve, pra cada data de pesquisa, a mediana do ano
    de referencia MAIS DISTANTE disponivel naquele dia (maior horizonte
    publicado no momento) -- depois condensa pra 1 ponto por mes (a ultima
    pesquisa do mes). E o que alimenta o grafico "Expectativas x Selic",
    mostrando a expectativa de mais longo prazo mudando mes a mes."""
    por_data = {}  # data_pesquisa -> (ano_mais_distante, mediana)
    for ano_ref, registros in historico.items():
        ano_int = int(ano_ref)
        for data_pesquisa, mediana in registros:
            atual = por_data.get(data_pesquisa)
            if atual is None or ano_int > atual[0]:
                por_data[data_pesquisa] = (ano_int, mediana)

    por_mes = {}
    for data_pesquisa in sorted(por_data):
        ano_alvo, mediana = por_data[data_pesquisa]
        chave = data_pesquisa[:7]  # "YYYY-MM"
        por_mes[chave] = {"data_pesquisa": data_pesquisa, "ano_alvo": ano_alvo, "mediana": mediana}

    return [
        {"data": f"{chave}-01", **por_mes[chave]}
        for chave in sorted(por_mes)
    ]


def main():
    had_failure = False
    try:
        print("Buscando Focus anual (mediana IPCA, API Olinda/BCB)...")
        focus_anual, focus_historico = buscar_focus_anual_ipca()
        print(f"  -> {len(focus_anual)} anos obtidos.")
    except Exception as e:
        print(f"  !! Falha ao acessar o Focus anual ({e}).")
        focus_anual = {}
        focus_historico = {}
        had_failure = True

    anos = sorted(focus_anual)
    expectativa_longo_prazo_mensal = horizonte_longo_mensal(focus_historico)
    print(f"  -> {len(expectativa_longo_prazo_mensal)} meses no horizonte longo.")

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "had_failure": had_failure,
        "series": {
            "anos": anos,
            "expectativa_mediana": [round(focus_anual[a][0], 4) for a in anos],
            "data_pesquisa": [focus_anual[a][1] for a in anos],
        },
        "historico_por_ano": {
            ano: [
                {"data_pesquisa": data_pesquisa, "mediana": round(mediana, 4)}
                for data_pesquisa, mediana in registros
            ]
            for ano, registros in focus_historico.items()
        },
        "expectativa_longo_prazo_mensal": expectativa_longo_prazo_mensal,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Arquivo gerado: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
