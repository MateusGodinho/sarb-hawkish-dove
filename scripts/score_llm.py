"""
ETAPA 3b - Scoring hawkish/dove via API da Anthropic (Claude).

Le o texto de cada ata e pede ao modelo, com um prompt padronizado (arquivo
prompts/hawkish_dove_prompt.txt, editavel sem tocar neste script), uma nota
de -5 (muito dovish) a +5 (muito hawkish) mais uma justificativa curta.

Requer a variavel de ambiente ANTHROPIC_API_KEY configurada.

E resumivel: se data/processed/scores_llm.csv ja existir, reunioes ja
pontuadas sao puladas (identificadas por meeting_date), permitindo rodar em
lotes ou retomar apos uma falha de rede sem re-pagar chamadas ja feitas.
"""

from __future__ import annotations

import csv
import json
import os
import time

import config

MODEL = os.environ.get("SARB_SCORING_MODEL", "claude-sonnet-5")
PROMPT_PATH = config.SCRIPTS_DIR / "prompts" / "hawkish_dove_prompt.txt"
MAX_CHARS_PER_STATEMENT = 12000  # protecao simples contra atas anomalamente longas


def _load_prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _load_already_scored() -> dict[str, dict]:
    if not config.SCORES_LLM_CSV.exists():
        return {}
    with open(config.SCORES_LLM_CSV, encoding="utf-8-sig") as f:
        return {row["meeting_date"]: row for row in csv.DictReader(f)}


def _parse_model_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def score_one(client, prompt_template: str, statement_text: str) -> dict:
    text = statement_text[:MAX_CHARS_PER_STATEMENT]
    prompt = prompt_template.replace("{statement_text}", text)

    message = client.messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(block.text for block in message.content if block.type == "text")
    parsed = _parse_model_json(raw)
    return {
        "llm_score": float(parsed["score"]),
        "llm_rationale": parsed.get("rationale", ""),
    }


def main(limit: int | None = None):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "ANTHROPIC_API_KEY nao esta configurada no ambiente. "
            "Defina a variavel antes de rodar este script."
        )

    try:
        import anthropic
    except ImportError as exc:
        raise SystemExit("Pacote 'anthropic' nao instalado. Rode: pip install anthropic") from exc

    if not config.DATASET_JSON.exists():
        raise SystemExit(
            "data/processed/statements_dataset.json nao encontrado. "
            "Rode antes: python scrape_statements.py"
        )

    records = json.loads(config.DATASET_JSON.read_text(encoding="utf-8"))
    prompt_template = _load_prompt_template()
    already_scored = _load_already_scored()

    client = anthropic.Anthropic()

    rows = list(already_scored.values())
    pending = [
        r for r in records
        if r.get("scrape_status") == "ok" and r.get("meeting_date") not in already_scored
    ]
    if limit:
        pending = pending[:limit]

    print(f"{len(pending)} atas pendentes de scoring via LLM "
          f"({len(already_scored)} ja tinham sido pontuadas antes).")

    for i, r in enumerate(pending, start=1):
        raw_text_file = r.get("raw_text_file")
        text_path = config.PROJECT_ROOT / raw_text_file if raw_text_file else None
        if not text_path or not text_path.exists():
            continue

        statement_text = text_path.read_text(encoding="utf-8")
        print(f"[{i}/{len(pending)}] {r.get('meeting_date')} - {r.get('title')}")

        try:
            result = score_one(client, prompt_template, statement_text)
            row = {
                "meeting_date": r.get("meeting_date"),
                "title": r.get("title"),
                "policy_rate_pct": r.get("policy_rate_pct"),
                "rate_action": r.get("rate_action"),
                "llm_score": result["llm_score"],
                "llm_rationale": result["llm_rationale"],
                "llm_model": MODEL,
            }
            rows.append(row)
            print(f"    score={result['llm_score']}")
        except Exception as exc:  # noqa: BLE001
            print(f"    erro ao pontuar: {exc}")

        # salva incrementalmente para poder retomar caso o processo pare
        _write_rows(rows)
        time.sleep(0.5)

    print(f"\nConcluido. Scores salvos em: {config.SCORES_LLM_CSV}")


def _write_rows(rows: list[dict]):
    if not rows:
        return
    rows_sorted = sorted(rows, key=lambda r: r["meeting_date"] or "")
    with open(config.SCORES_LLM_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows_sorted[0].keys()))
        writer.writeheader()
        writer.writerows(rows_sorted)


if __name__ == "__main__":
    import sys

    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(limit=lim)
