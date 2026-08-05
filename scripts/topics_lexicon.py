"""
Listas de palavras-chave por tema, para a Seção 2 do artigo (evolucao dos
topicos na comunicacao do SARB). Mesma logica de contagem ponderada usada
no score hawkish/dovish (lexicon_terms.py) -- transparente e facil de
auditar, em vez de topic modeling tipo LDA.

Termos com "*" no comentario indicam que varias formas foram escritas por
extenso (sem stemming), seguindo o mesmo padrao do lexicon_terms.py.
"""

TOPICS = {
    "Inflation": [
        "inflation", "cpi", "consumer price index", "disinflation", "deflation",
        "price pressures", "price stability",
    ],
    "Exchange rate": [
        "rand", "exchange rate", "currency", "depreciation", "appreciation",
        "pass-through", "pass through",
    ],
    "Financial stability": [
        "financial stability", "systemic risk", "macroprudential", "banking sector",
        "financial sector", "financial system",
    ],
    "Fiscal policy": [
        "fiscal policy", "fiscal deficit", "government debt", "budget deficit",
        "national treasury", "public finances", "fiscal consolidation",
    ],
    "Global spillovers": [
        "global economy", "global growth", "federal reserve", "emerging markets",
        "global financial crisis", "pandemic", "covid", "geopolitical",
    ],
    "The target itself": [
        "target range", "midpoint", "mid-point", "point target", "inflation targeting",
        "inflation target",
    ],
}
