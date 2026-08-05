"""
Lista inicial de termos hawkish/dovish tipicos de comunicacao de bancos
centrais (em ingles, ja que as atas do SARB sao publicadas em ingles).

Pesos: 2 = termo forte/inequivoco, 1 = termo moderado/contextual.
Esta lista e um ponto de partida deliberadamente simples (abordagem
"bag of phrases") para servir de baseline comparavel com a abordagem via
LLM (score_llm.py). Espera-se iterar sobre ela.
"""

HAWKISH_TERMS = {
    # taxa / postura de politica
    "increase the repurchase rate": 2,
    "raise interest rates": 2,
    "rate hike": 2,
    "hiking cycle": 2,
    "further tightening": 2,
    "tighten monetary policy": 2,
    "tightening bias": 2,
    "restrictive stance": 2,
    "less accommodative": 1,
    "withdraw accommodation": 2,
    "normalise policy": 1,
    "normalize policy": 1,
    "remove policy accommodation": 2,
    "vigilant": 1,
    "upside risk": 1,
    "upside risks to inflation": 2,
    "inflation expectations have increased": 2,
    "inflation expectations remain elevated": 1,
    "elevated inflation": 1,
    "persistent inflation": 1,
    "inflation remains too high": 2,
    "above the target range": 1,
    "above target": 1,
    "overheating": 2,
    "robust growth": 1,
    "strong labour market": 1,
    "strong labor market": 1,
    "wage pressure": 1,
    "second-round effects": 1,
    "de-anchoring": 1,
    "not yet done": 1,
    "further increases may be required": 2,
    "committed to price stability": 1,
    "assessed to be on the upside": 2,

    # substantivos/adjetivos gerais
    "hawkish": 2,
    "aggressive tightening": 2,
    "inflationary pressure": 1,
    "inflationary pressures": 1,
}

DOVISH_TERMS = {
    "reduce the repurchase rate": 2,
    "lower interest rates": 2,
    "rate cut": 2,
    "cutting cycle": 2,
    "accommodative stance": 2,
    "accommodative monetary policy": 2,
    "loosen monetary policy": 2,
    "easing bias": 2,
    "pause": 1,
    "on hold": 1,
    "unchanged": 1,
    "downside risk": 1,
    "downside risks to growth": 2,
    "weak growth": 1,
    "weak economic activity": 1,
    "subdued demand": 1,
    "subdued inflation": 2,
    "below the target range": 1,
    "below target": 1,
    "slack in the economy": 1,
    "spare capacity": 1,
    "economic slowdown": 1,
    "soft labour market": 1,
    "soft labor market": 1,
    "supportive of growth": 1,
    "space to pause": 2,
    "space to cut": 2,
    "well anchored": 1,
    "inflation expectations have declined": 2,
    "inflation is moderating": 1,
    "assessed to be on the downside": 2,

    "dovish": 2,
    "stimulate the economy": 2,
    "disinflation": 1,
}
