"""
Aplica as duas abordagens de scoring (lexico ponderado e Henry 2008
bag-of-words) ja implementadas para as atas do MPC (score_lexicon.py /
score_henry.py) tambem ao corpus de speeches. Reutiliza a mesma funcao
score_text() de cada modulo -- a logica de pontuacao e identica, so muda a
fonte dos documentos (data/processed/speeches_dataset.json em vez de
statements_dataset.json).
"""

from __future__ import annotations

import csv
import json

import config
import score_henry
import score_lexicon


def _iter_speech_texts(records: list[dict]):
    for r in records:
        raw_text_file = r.get("raw_text_file")
        if not raw_text_file or r.get("scrape_status") != "ok":
            continue
        if r.get("is_english") is False:
            # traducao para outra lingua oficial (isiXhosa/isiZulu/Xitsonga)
            # do mesmo discurso ja contado na versao em ingles -- ver
            # flag_non_english.py / detect_language.py
            continue
        text_path = config.PROJECT_ROOT / raw_text_file
        if not text_path.exists():
            continue
        yield r, text_path.read_text(encoding="utf-8")


def run_lexicon(records: list[dict]):
    rows = []
    for r, text in _iter_speech_texts(records):
        scores = score_lexicon.score_text(text)
        rows.append({
            "publish_date": r.get("publish_date"),
            "title": r.get("title"),
            "speaker_guess": r.get("speaker_guess"),
            "text_source": r.get("text_source"),
            **scores,
        })
    rows.sort(key=lambda r: r["publish_date"] or "")
    with open(config.SPEECHES_SCORES_LEXICON_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Scores (lexico) calculados para {len(rows)} speeches -> {config.SPEECHES_SCORES_LEXICON_CSV}")


def run_henry(records: list[dict]):
    rows = []
    for r, text in _iter_speech_texts(records):
        scores = score_henry.score_text(text)
        rows.append({
            "publish_date": r.get("publish_date"),
            "title": r.get("title"),
            "speaker_guess": r.get("speaker_guess"),
            "text_source": r.get("text_source"),
            **scores,
        })
    rows.sort(key=lambda r: r["publish_date"] or "")
    with open(config.SPEECHES_SCORES_HENRY_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Scores (Henry 2008) calculados para {len(rows)} speeches -> {config.SPEECHES_SCORES_HENRY_CSV}")


def main():
    if not config.SPEECHES_DATASET_JSON.exists():
        raise SystemExit(
            "data/processed/speeches_dataset.json nao encontrado. "
            "Rode antes: python fetch_speech_list.py && python scrape_speeches.py"
        )
    records = json.loads(config.SPEECHES_DATASET_JSON.read_text(encoding="utf-8"))
    run_lexicon(records)
    run_henry(records)


if __name__ == "__main__":
    main()
