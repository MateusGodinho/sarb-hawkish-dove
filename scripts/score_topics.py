"""
ETAPA 6 - Evolucao de topicos (Secao 2 do artigo): conta ocorrencias das
frases de cada tema (topics_lexicon.py) no corpus combinado (atas + discursos),
agregado por ano, normalizado pela densidade de palavras (por 1000 palavras)
-- mesma logica de normalizacao do score_lexicon.py.

Le direto dos .txt ja salvos (nao recalcula nada da Etapa 1). Saida:
data/processed/topics_by_year.csv, formato longo (year, topic, docs, density).
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict

import config
from topics_lexicon import TOPICS


def count_topics(text: str) -> tuple[dict[str, int], int]:
    text_lower = text.lower()
    word_count = max(len(text_lower.split()), 1)
    counts = {}
    for topic, terms in TOPICS.items():
        total = 0
        for term in terms:
            pattern = r"\b" + re.escape(term) + r"\b"
            total += len(re.findall(pattern, text_lower))
        counts[topic] = total
    return counts, word_count


def iter_docs():
    stmts = json.loads(config.DATASET_JSON.read_text(encoding="utf-8"))
    for r in stmts:
        if r.get("scrape_status") == "ok" and r.get("raw_text_file"):
            yield r["meeting_date"], r["raw_text_file"], "statement"

    speeches = json.loads(config.SPEECHES_DATASET_JSON.read_text(encoding="utf-8"))
    for r in speeches:
        if r.get("scrape_status") == "ok" and r.get("raw_text_file"):
            yield r["publish_date"], r["raw_text_file"], "speech"


def main():
    year_topic_counts = defaultdict(lambda: defaultdict(int))
    year_word_counts = defaultdict(int)
    year_doc_counts = defaultdict(int)

    n = 0
    for date, raw_text_file, kind in iter_docs():
        if not date:
            continue
        text_path = config.PROJECT_ROOT / raw_text_file
        if not text_path.exists():
            continue
        text = text_path.read_text(encoding="utf-8")
        counts, word_count = count_topics(text)

        year = date[:4]
        for topic, c in counts.items():
            year_topic_counts[year][topic] += c
        year_word_counts[year] += word_count
        year_doc_counts[year] += 1
        n += 1

    rows = []
    for year in sorted(year_word_counts):
        words = year_word_counts[year]
        for topic in TOPICS:
            count = year_topic_counts[year][topic]
            density = count / (words / 1000.0)
            rows.append({
                "year": year,
                "topic": topic,
                "count": count,
                "docs": year_doc_counts[year],
                "words": words,
                "density_per_1000_words": round(density, 4),
            })

    out_path = config.PROCESSED_DIR / "topics_by_year.csv"
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Processados {n} documentos (atas + discursos).")
    print(f"Salvo em: {out_path}")


if __name__ == "__main__":
    main()
