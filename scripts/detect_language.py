"""
Heuristica leve pra detectar se um documento esta em ingles -- o SARB
publica traducoes de alguns discursos (tipicamente a "Governor's Address"
anual aos acionistas) em outras linguas oficiais da Africa do Sul (isiXhosa,
isiZulu, Xitsonga, etc.), que o scraper indexa como documentos separados.
Esses textos nao tem nenhum termo do dicionario Henry/lexicon em ingles e
contaminam scoring e topic modeling.

Metodologia: conta a frequencia combinada de stopwords muito comuns do
ingles ("the", "and", "of", "to", "in", "is", "that", "for", "on", "with",
"as", "at", "by", "from"). Em texto ingles real essas palavras tipicamente
somam 25%+ das palavras totais (so "the" ja fica em ~5-7%). Em texto de
outra lingua, essa soma fica perto de zero.
"""

from __future__ import annotations

import re

_COMMON_ENGLISH_WORDS = {
    "the", "and", "of", "to", "in", "is", "that", "for", "on", "with",
    "as", "at", "by", "from", "this", "it", "be", "was", "are",
}

MIN_ENGLISH_WORD_SHARE = 0.02  # limiar calibrado empiricamente: traducoes reais (isiXhosa/
# isiZulu/Xitsonga) medem 0.001-0.006; ate um discurso ingles muito esparso em prosa
# (slides so com tabelas numericas) mediu 0.044 -- o limiar fica confortavelmente entre os dois.


def english_word_share(text: str) -> float:
    tokens = re.findall(r"[a-zA-Z']+", text.lower())
    if not tokens:
        return 0.0
    common = sum(1 for t in tokens if t in _COMMON_ENGLISH_WORDS)
    return common / len(tokens)


def is_english(text: str) -> bool:
    return english_word_share(text) >= MIN_ENGLISH_WORD_SHARE
