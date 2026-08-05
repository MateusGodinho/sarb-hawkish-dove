"""
Reprocessa rate_action / policy_rate_pct / votacao a partir dos .txt ja
salvos em data/raw_texts/, sem precisar baixar nada de novo da internet.
Util para iterar rapido em ajustes de parsers.py.
"""

from __future__ import annotations

import json

import config
import parsers
from scrape_statements import _forward_fill_hold_rates, _write_csv

HEADER_SEP = "-" * 70


def _read_full_text(raw_text_file: str) -> str | None:
    path = config.PROJECT_ROOT / raw_text_file
    if not path.exists():
        return None
    content = path.read_text(encoding="utf-8")
    idx = content.find(HEADER_SEP)
    if idx == -1:
        return content
    return content[idx + len(HEADER_SEP):].lstrip("\n")


def main():
    records = json.loads(config.DATASET_JSON.read_text(encoding="utf-8"))

    changed = 0
    for r in records:
        if not r.get("raw_text_file"):
            continue
        full_text = _read_full_text(r["raw_text_file"])
        if not full_text:
            continue

        rate_info = parsers.extract_rate_decision(full_text)
        vote_info = parsers.extract_vote_outcome(full_text)

        new_action = rate_info["action"]
        new_rate = rate_info["new_rate_pct"] or r.get("repo_rate_widget_pct")

        if new_action != r.get("rate_action") or new_rate != r.get("policy_rate_pct"):
            changed += 1

        r["rate_action"] = new_action
        r["rate_change_bps"] = rate_info["change_bps"]
        r["rate_raw_sentence"] = rate_info["raw_sentence"]
        r["policy_rate_pct"] = new_rate
        r["vote_unanimous"] = vote_info["unanimous"]
        r["vote_breakdown_json"] = json.dumps(vote_info["vote_breakdown"], ensure_ascii=False)
        r["vote_raw_sentence"] = vote_info["raw_sentence"]

    records.sort(key=lambda r: r["meeting_date"] or "")
    _forward_fill_hold_rates(records)

    config.DATASET_JSON.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(records)

    print(f"Reprocessado. {changed} registros tiveram rate_action/policy_rate_pct alterados.")


if __name__ == "__main__":
    main()
