# A Última Fronteira da Independência do Banco Central

Página de divulgação interativa (HTML estático) que ilustra, com gráficos e
linha do tempo, os principais pontos do ensaio "The Last Frontier of Central
Bank Independence", escrito por Mario Serpa.

⚠️ Este site não é conteúdo original — é um material de apoio visual criado
por Lucas Brito para ilustrar, em parte, os dados discutidos no artigo do
autor. Para ler o ensaio completo, acesse o link no site ou o Substack
original de Mario Serpa.

Traz gráficos interativos (IPCA, Selic, Dívida Bruta, expectativas do Focus)
construídos com dados públicos do Banco Central (SGS/BCB) e IBGE, e permite
alternar entre português e inglês.

Página estática (index.html) no mesmo padrão visual do Painel Macro CIEM
(fundo escuro, roxo/azul claro, Space Grotesk + Inter + JetBrains Mono).

## Estrutura

- `index.html` — a página em si (abrir direto no navegador ou publicar via GitHub Pages)
- `data/` — pasta reservada para os dados dos gráficos que você for incluir (ex: `.json` com séries históricas)

## Próximos passos (gráficos)

O projeto já usa Chart.js via CDN no seu painel macro. Quando você definir quais
gráficos quer incluir aqui (ex: evolução da Selic, comparação de autonomia
financeira entre bancos centrais, trajetória do resultado do BACEN), me diga
os dados/fonte e eu adiciono os `<canvas>` + scripts no index.html, seguindo o
mesmo estilo do dashboard.

## Changelog v7

- **Padronização de cores**: byline, todos os `section-label` (exceto "Onde estão
  as divergências reais", agora azul), texto da timeline (exceto os anos, que
  seguem azuis) e o parágrafo final do CTA passaram para branco, seguindo o
  mesmo padrão do resto do texto do ensaio.
- **Controle Inflacionário**: adicionada a banda de meta de inflação (piso/teto
  sombreados + centro pontilhado), com a tabela histórica de metas do CMN
  embutida no `index.html` (2010–2028).
- **Dívida Bruta x Selic**: adicionado toggle `% do PIB` / `R$ milhões`, com a
  nova série 13761 (Dívida Bruta em R$ milhões) incluída em
  `scripts/fetch_macro_selic.py` e em `data/macro_data.json`.
- **Aviso de dados ausentes**: os três gráficos (`Controle Inflacionário`,
  `Dívida Bruta x Selic`, `Expectativas x Selic`) agora mostram um aviso visível
  quando a série correspondente vier vazia, em vez de simplesmente não desenhar
  nada.

### ⚠️ Sobre o bug "a Meta Selic não veio em nenhum gráfico"

Não é um bug de renderização — os três arquivos em `data/` deste pacote são
stubs vazios (`had_failure: true`, arrays `[]`), porque o fetch real (BCB SGS)
nunca foi executado/commitado para esta versão. Isso afeta IPCA, Selic e Dívida
Bruta ao mesmo tempo, não só a Selic. Para popular os dados:

1. Rode `pip install -r requirements.txt` e depois
   `python scripts/fetch_macro_selic.py` e
   `python scripts/fetch_expectativas_anual.py` localmente, e comite os JSONs
   gerados em `data/`; **ou**
2. No GitHub, vá em Actions → "Atualizar dados BCB" → Run workflow, para
   disparar o job manualmente (ele já está agendado para rodar 1x/dia).

A partir de agora, se algum fetch futuro falhar de novo, o aviso amarelo vai
aparecer direto no gráfico afetado — não vai mais passar batido.

## Changelog v9

- **Botão de idioma (PT/EN)**: novo botão "🌐 English" no canto superior
  direito do header. Um clique traduz a página inteira para inglês (textos
  do ensaio, timeline, cards, notas de fonte, tabela completa de presidentes
  do BACEN, avisos de dados ausentes e os textos/tooltips dos 4 gráficos);
  outro clique volta para português. O idioma não é persistido entre
  recarregamentos — a página sempre abre em PT-BR.

## Changelog v8

- **Corrigido o 406 na Meta Selic**: a série 432 (SGS/BCB) é diária desde 1986
  (~14 mil pontos); pedir o histórico completo sem `dataInicial` faz a API do
  BCB devolver `406 Not Acceptable`. `fetch_macro_selic.py` agora limita a
  busca a partir de 01/01/2010 (mesmo período do IPCA), igual às outras séries
  que já funcionavam.
- **Gráfico "IPCA anual x rotatividade na presidência do BACEN"**: LC 179 —
  autonomia agora em linha roxa; Plano Real passou de verde para linha branca.
  Adicionada a mesma banda de meta de inflação (piso/teto sombreados + centro
  pontilhado) usada no gráfico de Controle Inflacionário, a partir de 2005
  (1999–2004 tiveram metas revisadas no meio do ano e foram deixados de fora
  para não simplificar demais esse período). Tooltip ajustado para rotular
  cada linha corretamente (antes, passar o mouse por cima da banda mostrava
  tudo como "IPCA").
