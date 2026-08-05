"""
ETAPA 1b (speeches) - Visita cada pagina de discurso listada em
data/raw/speeches_index.json, extrai o texto completo (HTML ou PDF,
reutilizando a mesma logica de scrape_common.py usada para as atas do
MPC), e salva:

  - um .txt por discurso em data/raw_texts/speeches/
  - o dataset consolidado em data/processed/speeches_dataset.(json|csv)

Diferente das atas do MPC, discursos nao tem decisao de taxa nem votacao
para extrair -- o dataset aqui e so texto + metadados (data, titulo,
palestrante estimado a partir do titulo).
"""

from __future__ import annotations

import csv
import json
import re
import time
import traceback

import config
from scrape_common import extract_page_text, sanitize_filename

_SPEAKER_RE = re.compile(
    r"\bby\s+(?:Mr\s+|Ms\s+|Dr\s+|Mrs\s+)?([A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+){0,3})",
)


def _guess_speaker(title: str) -> str | None:
    if not title:
        return None
    m = _SPEAKER_RE.search(title)
    if m:
        return m.group(1).strip().rstrip(",")
    # formato "Nome Sobrenome | Titulo do discurso"
    if "|" in title:
        candidate = title.split("|", 1)[0].strip()
        if candidate and len(candidate.split()) <= 4:
            return candidate
    return None


def scrape_one(record: dict) -> dict:
    out = dict(record)
    out.update({
        "text_source": None,
        "pdf_url": None,
        "full_text_chars": 0,
        "speaker_guess": _guess_speaker(record.get("title")),
        "raw_text_file": None,
        "scrape_status": "error",
        "error_message": None,
    })

    try:
        page_result = extract_page_text(record["detail_url"])
        out["text_source"] = page_result["text_source"]
        out["full_text"] = page_result["full_text"]
        out["pdf_url"] = page_result["pdf_url"]

        full_text = out.get("full_text")
        if full_text:
            out["full_text_chars"] = len(full_text)
            out["scrape_status"] = "ok"
        else:
            out["scrape_status"] = "no_text_found"

    except Exception as exc:  # noqa: BLE001
        out["scrape_status"] = "error"
        out["error_message"] = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()

    return out


def _save_raw_text(record: dict) -> str | None:
    full_text = record.get("full_text")
    if not full_text:
        return None
    date_part = record.get("publish_date") or "unknown-date"
    solr_suffix = (record.get("solr_id") or "").rsplit("/", 1)[-1]
    filename = f"{date_part}_{solr_suffix}.txt" if solr_suffix else f"{date_part}.txt"
    filename = sanitize_filename(filename)
    path = config.SPEECHES_RAW_TEXTS_DIR / filename

    header = (
        f"Titulo: {record.get('title')}\n"
        f"Data: {record.get('publish_date')}\n"
        f"Palestrante (estimado): {record.get('speaker_guess')}\n"
        f"URL: {record.get('detail_url')}\n"
        f"Fonte do texto: {record.get('text_source')}"
        + (f" ({record.get('pdf_url')})" if record.get("pdf_url") else "")
        + "\n"
        + "-" * 70
        + "\n\n"
    )
    path.write_text(header + full_text, encoding="utf-8")
    return str(path.relative_to(config.PROJECT_ROOT))


def main(limit: int | None = None, start_at: int = 0):
    if not config.SPEECHES_INDEX_JSON.exists():
        raise SystemExit(
            "data/raw/speeches_index.json nao encontrado. "
            "Rode antes: python fetch_speech_list.py"
        )

    records = json.loads(config.SPEECHES_INDEX_JSON.read_text(encoding="utf-8"))
    records = records[start_at:]
    if limit:
        records = records[:limit]

    # resumivel: carrega resultados ja salvos (por URL) para nao rebaixar
    # o que ja foi processado, caso o processo seja interrompido.
    existing: dict[str, dict] = {}
    if config.SPEECHES_DATASET_JSON.exists():
        for r in json.loads(config.SPEECHES_DATASET_JSON.read_text(encoding="utf-8")):
            existing[r["detail_url"]] = r

    results = list(existing.values())
    processed_urls = set(existing.keys())

    for i, record in enumerate(records, start=1):
        if record["detail_url"] in processed_urls:
            continue
        print(f"[{i}/{len(records)}] {record.get('publish_date')} - {record.get('title')}")
        result = scrape_one(record)
        result["raw_text_file"] = _save_raw_text(result)
        result_for_dataset = {k: v for k, v in result.items() if k != "full_text"}
        results.append(result_for_dataset)
        print(f"    status={result['scrape_status']} fonte={result['text_source']} "
              f"palestrante={result['speaker_guess']}")
        time.sleep(config.REQUEST_DELAY_SECONDS)

        if i % 25 == 0:
            _save(results)

    _save(results)

    ok = sum(1 for r in results if r["scrape_status"] == "ok")
    print(f"\nConcluido: {ok}/{len(results)} speeches com texto extraido com sucesso.")
    print(f"Dataset salvo em: {config.SPEECHES_DATASET_JSON} e {config.SPEECHES_DATASET_CSV}")


def _save(results: list[dict]):
    results_sorted = sorted(results, key=lambda r: r.get("publish_date") or "")
    config.SPEECHES_DATASET_JSON.write_text(
        json.dumps(results_sorted, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if results_sorted:
        with open(config.SPEECHES_DATASET_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(results_sorted[0].keys()))
            writer.writeheader()
            writer.writerows(results_sorted)


if __name__ == "__main__":
    import sys

    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(limit=lim)
