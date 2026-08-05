"""
ETAPA 3a - Scoring hawkish/dove por contagem ponderada de termos-chave.

Metodologia:
  1. Conta ocorrencias de cada termo hawkish e dovish (lexicon_terms.py) no
     texto, ponderadas pelo peso do termo.
  2. Calcula a densidade liquida = (soma hawkish - soma dovish) / (numero de
     palavras do texto / 1000). Isso normaliza atas longas vs curtas.
  3. Espreme a densidade liquida para a escala fixa [-5, +5] com
     5 * tanh(densidade / K), onde K e uma constante de calibracao
     (LEXICON_SCALE_K abaixo). tanh garante que o score nunca estoure a
     escala mesmo em atas com densidade de termos muito alta.

Este e um baseline simples e 100% determinístico/local (sem custo de API),
pensado para comparar com a abordagem via LLM (score_llm.py).
"""

from __future__ import annotations

import csv
import json
import math
import re

import config
from lexicon_terms import DOVISH_TERMS, HAWKISH_TERMS

# constante de calibracao da funcao de squashing (tanh). Quanto menor, mais
# facil o score satura em +-5. Ajuste conforme observar a distribuicao real.
LEXICON_SCALE_K = 3.0


def _count_weighted(text_lower: str, terms: dict) -> tuple[float, dict]:
    total = 0.0
    hits = {}
    for term, weight in terms.items():
        pattern = r"\b" + re.escape(term) + r"\b"
        n = len(re.findall(pattern, text_lower))
        if n:
            hits[term] = n
            total += n * weight
    return total, hits


def score_text(text: str) -> dict:
    text_lower = text.lower()
    word_count = max(len(text_lower.split()), 1)

    hawkish_total, hawkish_hits = _count_weighted(text_lower, HAWKISH_TERMS)
    dovish_total, dovish_hits = _count_weighted(text_lower, DOVISH_TERMS)

    density_per_1000_words = (hawkish_total - dovish_total) / (word_count / 1000.0)
    score = 5 * math.tanh(density_per_1000_words / LEXICON_SCALE_K)

    return {
        "lexicon_score": round(score, 3),
        "lexicon_hawkish_weighted_count": hawkish_total,
        "lexicon_dovish_weighted_count": dovish_total,
        "lexicon_word_count": word_count,
        "lexicon_hawkish_hits": json.dumps(hawkish_hits, ensure_ascii=False),
        "lexicon_dovish_hits": json.dumps(dovish_hits, ensure_ascii=False),
    }


def main():
    if not config.DATASET_JSON.exists():
        raise SystemExit(
            "data/processed/statements_dataset.json nao encontrado. "
            "Rode antes: python scrape_statements.py"
        )

    records = json.loads(config.DATASET_JSON.read_text(encoding="utf-8"))

    rows = []
    for r in records:
        raw_text_file = r.get("raw_text_file")
        if not raw_text_file or r.get("scrape_status") != "ok":
            continue

        text_path = config.PROJECT_ROOT / raw_text_file
        if not text_path.exists():
            continue

        text = text_path.read_text(encoding="utf-8")
        scores = score_text(text)

        rows.append({
            "meeting_date": r.get("meeting_date"),
            "title": r.get("title"),
            "policy_rate_pct": r.get("policy_rate_pct"),
            "rate_action": r.get("rate_action"),
            "policy_rate_final": r.get("policy_rate_final"),
            "rate_action_final": r.get("rate_action_final"),
            "rate_source_final": r.get("rate_source_final"),
            "in_scope_inflation_targeting": r.get("in_scope_inflation_targeting"),
            **scores,
        })

    rows.sort(key=lambda r: r["meeting_date"] or "")

    with open(config.SCORES_LEXICON_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Scores (lexicon) calculados para {len(rows)} atas.")
    print(f"Salvo em: {config.SCORES_LEXICON_CSV}")


if __name__ == "__main__":
    main()
