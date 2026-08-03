"""
Busca no SGS/BCB: IPCA mensal (433, usado pra calcular o acumulado em 12
meses), Meta Selic definida pelo Copom (432, serie diaria, condensada aqui
pro ultimo valor de cada mes) e Divida Bruta do Governo Geral (13762, % do
PIB). Gera data/macro_data.json, consumido pelos graficos "Controle
Inflacionario" e "Divida Bruta x Selic" do index.html.

Rodar:
    python scripts/fetch_macro_selic.py

Pensado pra rodar 1x por dia via GitHub Actions (.github/workflows/update-data.yml).
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_JSON = REPO_ROOT / "data" / "macro_data.json"

SGS_IPCA_MENSAL = 433
SGS_SELIC_META = 432
SGS_DIVIDA_BRUTA_PCT = 13762
SGS_DIVIDA_BRUTA_BRL = 13761  # Divida Bruta do Governo Geral, R$ milhoes (valor nominal)

BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; CIEM-dashboard/1.0; +https://github.com/lucasbritoecon-hash)",
}


def buscar_serie(codigo, data_inicial=None, data_final=None, tries=3, wait=8):
    import time
    url = BASE_URL.format(codigo=codigo)
    params = {"formato": "json"}
    if data_inicial:
        params["dataInicial"] = data_inicial
    if data_final:
        params["dataFinal"] = data_final
    last_err = None
    for attempt in range(1, tries + 1):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"[serie {codigo}] tentativa {attempt}/{tries} falhou: {e}")
            if attempt < tries:
                time.sleep(wait)
    raise RuntimeError(f"falha definitiva na serie {codigo}: {last_err}")


def buscar_serie_paginada(codigo, data_inicial, tries=3, wait=8, passo_anos=9):
    """Pra series diarias longas (ex: 432 desde 2010), o SGS/BCB rejeita com
    406 se o intervalo pedido numa unica chamada passar de ~10 anos. Quebra
    o periodo em janelas de `passo_anos` anos e concatena os resultados --
    assim continua funcionando conforme o tempo passa e a janela cresce."""
    inicio = datetime.strptime(data_inicial, "%d/%m/%Y")
    fim = datetime.now()
    resultado = []
    cursor = inicio
    while cursor <= fim:
        try:
            proximo = cursor.replace(year=cursor.year + passo_anos)
        except ValueError:  # 29/fev caindo num ano nao-bissexto
            proximo = cursor.replace(year=cursor.year + passo_anos, day=28)
        proximo = min(proximo, fim)
        trecho = buscar_serie(
            codigo,
            data_inicial=cursor.strftime("%d/%m/%Y"),
            data_final=proximo.strftime("%d/%m/%Y"),
            tries=tries, wait=wait,
        )
        resultado.extend(trecho)
        cursor = proximo + timedelta(days=1)
    return resultado


def ultimo_por_mes(raw):
    """Recebe a lista bruta da API SGS (formato [{"data": "dd/mm/yyyy",
    "valor": "x,xx"}, ...], em ordem cronologica) e devolve so o ultimo
    ponto disponivel de cada mes -- pro mes corrente (ainda incompleto),
    fica o dado mais recente publicado ate agora."""
    por_mes = {}
    for item in raw:
        if item.get("valor") in (None, ""):
            continue
        dia, mes, ano = item["data"].split("/")
        chave = f"{ano}-{mes}"
        por_mes[chave] = item  # sobrescreve; assume raw em ordem cronologica

    chaves_ordenadas = sorted(por_mes)
    return [por_mes[k] for k in chaves_ordenadas]


def ipca_acum12_mensal(data_inicial="01/01/2010"):
    """Retorna [{"data": "YYYY-MM-01", "valor": pct}, ...] com o IPCA
    acumulado em 12 meses, mes a mes."""
    raw = buscar_serie(SGS_IPCA_MENSAL, data_inicial)
    mensal = {}
    for item in raw:
        d, m, y = item["data"].split("/")
        mensal[f"{y}-{m}-01"] = float(item["valor"]) / 100

    datas = sorted(mensal)
    resultado = []
    for i, data_str in enumerate(datas):
        if i < 11:
            continue
        janela = [mensal[datas[j]] for j in range(i - 11, i + 1)]
        acumulado = 1.0
        for v in janela:
            acumulado *= (1 + v)
        resultado.append({"data": data_str, "valor": round((acumulado - 1) * 100, 4)})
    return resultado


def main():
    had_failure = False

    print("Calculando IPCA acumulado em 12 meses (SGS 433)...")
    try:
        ipca_acum12 = ipca_acum12_mensal()
        print(f"  -> {len(ipca_acum12)} meses.")
    except Exception as e:
        print(f"  !! Falha: {e}")
        ipca_acum12 = []
        had_failure = True

    print("Buscando Meta Selic mensal (SGS 432)...")
    try:
        # A serie 432 e diaria desde 1986; o regime de Meta Selic (Copom
        # anunciando a taxa-alvo) comeca em 1999 -- usamos isso como
        # dataInicial pra pegar o maior horizonte possivel. O SGS/BCB devolve
        # 406 (Not Acceptable) se o intervalo pedido numa unica chamada
        # passar de uns 10 anos, e 1999-hoje ultrapassa isso de sobra.
        # buscar_serie_paginada quebra em janelas menores e concatena.
        # Depois condensamos pra 1 ponto por mes (o ultimo disponivel -- pro
        # mes corrente, o valor mais recente publicado ate agora), o que
        # deixa o JSON bem mais leve e ja no mesmo grao dos outros graficos.
        selic_diaria = buscar_serie_paginada(SGS_SELIC_META, data_inicial="01/01/1999")
        selic_raw = ultimo_por_mes(selic_diaria)
        print(f"  -> {len(selic_diaria)} pontos diarios -> {len(selic_raw)} pontos mensais.")
    except Exception as e:
        print(f"  !! Falha: {e}")
        selic_raw = []
        had_failure = True

    print("Buscando Divida Bruta % PIB (SGS 13762)...")
    try:
        divida_raw = buscar_serie(SGS_DIVIDA_BRUTA_PCT)
        print(f"  -> {len(divida_raw)} pontos.")
    except Exception as e:
        print(f"  !! Falha: {e}")
        divida_raw = []
        had_failure = True

    print("Buscando Divida Bruta R$ milhoes (SGS 13761)...")
    try:
        divida_brl_raw = buscar_serie(SGS_DIVIDA_BRUTA_BRL)
        print(f"  -> {len(divida_brl_raw)} pontos.")
    except Exception as e:
        print(f"  !! Falha: {e}")
        divida_brl_raw = []
        had_failure = True

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "had_failure": had_failure,
        "series": {
            "ipca_acum12": ipca_acum12,
            "selic_meta_mensal": [
                {"data": item["data"], "valor": float(str(item["valor"]).replace(",", "."))}
                for item in selic_raw if item.get("valor") not in (None, "")
            ],
            "divida_bruta_pct": [
                {"data": item["data"], "valor": float(str(item["valor"]).replace(",", "."))}
                for item in divida_raw if item.get("valor") not in (None, "")
            ],
            "divida_bruta_brl": [
                {"data": item["data"], "valor": float(str(item["valor"]).replace(",", "."))}
                for item in divida_brl_raw if item.get("valor") not in (None, "")
            ],
        },
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Arquivo gerado: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
