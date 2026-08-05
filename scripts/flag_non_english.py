"""
Aplica detect_language.is_english() a cada documento ja escrito em
data/raw_texts/ (atas e discursos) e grava um campo booleano
"is_english" de volta em statements_dataset.json e speeches_dataset.json
(e nos respectivos .csv).

O SARB publica traducoes de alguns discursos (a "Governor's Address" anual
aos acionistas) em outras linguas oficiais da Africa do Sul; o scraper
indexa cada traducao como um documento separado, o que contamina qualquer
analise textual em ingles (scoring hawkish/dovish, topic modeling, ate
contagem de volume). Rode este script depois de qualquer (re)scrape e antes
de qualquer script de scoring/topico.
"""

from __future__ import annotations

import csv
import json

import config
from detect_language import is_english


def _flag(dataset_json, dataset_csv):
    records = json.loads(dataset_json.read_text(encoding="utf-8"))
    n_flagged = 0
    for r in records:
        if r.get("scrape_status") != "ok" or not r.get("raw_text_file"):
            r["is_english"] = None
            continue
        text_path = config.PROJECT_ROOT / r["raw_text_file"]
        text = text_path.read_text(encoding="utf-8") if text_path.exists() else ""
        english = is_english(text) if text else None
        r["is_english"] = english
        if english is False:
            n_flagged += 1

    dataset_json.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    if records:
        with open(dataset_csv, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
            writer.writeheader()
            writer.writerows(records)

    return n_flagged, len(records)


def main():
    n, total = _flag(config.DATASET_JSON, config.DATASET_CSV)
    print(f"Statements: {n}/{total} sinalizados como nao-ingles")

    n, total = _flag(config.SPEECHES_DATASET_JSON, config.SPEECHES_DATASET_CSV)
    print(f"Speeches: {n}/{total} sinalizados como nao-ingles")


if __name__ == "__main__":
    main()
