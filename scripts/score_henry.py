"""
ETAPA 3 - Replica a abordagem de Erasmus & Hollander (2020): bag-of-words
com a biblioteca de sentimento financeiro do Henry (2008) (lexicon_henry.py,
transcrita do paper original). Este e o metodo de sentimento usado em
todos os resultados finais do artigo.

Metodologia:
  1. O texto e tokenizado em palavras individuais (bag-of-words, sem peso
     por termo -- cada ocorrencia conta 1, sem frases multi-palavra).
  2. Cada palavra e comparada com a lista de positivas (hawkish, ligada a
     perspectiva economica positiva) e negativas (dovish) do Henry (2008).
  3. Index = (hawkish_matches - dovish_matches) / (hawkish_matches + dovish_matches),
     escalado por um fator de 2 -> intervalo [-2, +2].
     +2 = mais hawkish possivel, -2 = mais dovish possivel.
  4. Repetido para cada ata do corpus.
"""

from __future__ import annotations

import csv
import json
import re

import config
from lexicon_henry import NEGATIVE_WORDS, POSITIVE_WORDS

_WORD_RE = re.compile(r"[a-z]+")


def score_text(text: str) -> dict:
    tokens = _WORD_RE.findall(text.lower())

    pos_hits: dict[str, int] = {}
    neg_hits: dict[str, int] = {}

    for tok in tokens:
        if tok in POSITIVE_WORDS:
            pos_hits[tok] = pos_hits.get(tok, 0) + 1
        elif tok in NEGATIVE_WORDS:
            neg_hits[tok] = neg_hits.get(tok, 0) + 1

    hawkish_count = sum(pos_hits.values())
    dovish_count = sum(neg_hits.values())
    total = hawkish_count + dovish_count

    index = 2 * (hawkish_count - dovish_count) / total if total else 0.0

    return {
        "henry_index": round(index, 4),
        "henry_hawkish_count": hawkish_count,
        "henry_dovish_count": dovish_count,
        "henry_total_words": len(tokens),
        "henry_hawkish_hits": json.dumps(pos_hits, ensure_ascii=False),
        "henry_dovish_hits": json.dumps(neg_hits, ensure_ascii=False),
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
            "policy_rate_final": r.get("policy_rate_final"),
            "rate_action_final": r.get("rate_action_final"),
            "in_scope_inflation_targeting": r.get("in_scope_inflation_targeting"),
            **scores,
        })

    rows.sort(key=lambda r: r["meeting_date"] or "")

    out_path = config.PROCESSED_DIR / "scores_henry.csv"
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Scores (Henry 2008 bag-of-words) calculados para {len(rows)} atas.")
    print(f"Salvo em: {out_path}")


if __name__ == "__main__":
    main()
