"""
ETAPA 1b - Visita cada pagina de ata do MPC listada em
data/raw/statements_index.json, extrai o texto completo (HTML ou PDF,
dependendo da era do site), tenta identificar a decisao de taxa e o
resultado da votacao, e salva:

  - um .txt por reuniao em data/raw_texts/
  - o dataset estruturado consolidado em data/processed/statements_dataset.(json|csv)

Duas eras de template foram identificadas no site do SARB:
  - >= 2024 (aprox.): a pagina HTML contem o texto completo da declaracao
    dentro de blocos "richtext", alem de widgets com a taxa repo e a
    inflacao vigentes no momento da publicacao.
  - < 2024: a pagina HTML e so uma casca; o texto completo esta em um PDF
    linkado (ex.: "Statement of the Monetary Policy Committee May 2023.pdf").

O scraper tenta HTML primeiro e cai para PDF automaticamente. Erros de rede,
PDFs corrompidos ou paginas fora do padrao sao capturados por registro -- o
scraper nunca aborta o lote inteiro por causa de uma ata problematica.
"""

from __future__ import annotations

import json
import re
import time
import traceback

import config
import parsers
from scrape_common import extract_page_text


def scrape_one(record: dict) -> dict:
    out = dict(record)
    out.update({
        "text_source": None,
        "pdf_url": None,
        "full_text_chars": 0,
        "repo_rate_widget_pct": None,
        "inflation_headline_widget_pct": None,
        "rate_action": None,
        "rate_change_bps": None,
        "policy_rate_pct": None,
        "rate_raw_sentence": None,
        "vote_unanimous": None,
        "vote_breakdown_json": None,
        "vote_raw_sentence": None,
        "raw_text_file": None,
        "scrape_status": "error",
        "error_message": None,
    })

    try:
        page_result = extract_page_text(record["detail_url"])
        out["text_source"] = page_result["text_source"]
        out["full_text"] = page_result["full_text"]
        out["pdf_url"] = page_result["pdf_url"]
        out["repo_rate_widget_pct"] = page_result["repo_rate_widget_pct"]
        out["inflation_headline_widget_pct"] = page_result["inflation_headline_widget_pct"]

        full_text = out.get("full_text")
        if full_text:
            out["full_text_chars"] = len(full_text)

            rate_info = parsers.extract_rate_decision(full_text)
            out["rate_action"] = rate_info["action"]
            out["rate_change_bps"] = rate_info["change_bps"]
            out["rate_raw_sentence"] = rate_info["raw_sentence"]
            out["policy_rate_pct"] = rate_info["new_rate_pct"] or out["repo_rate_widget_pct"]

            vote_info = parsers.extract_vote_outcome(full_text)
            out["vote_unanimous"] = vote_info["unanimous"]
            out["vote_breakdown_json"] = json.dumps(vote_info["vote_breakdown"], ensure_ascii=False)
            out["vote_raw_sentence"] = vote_info["raw_sentence"]

            out["scrape_status"] = "ok"
        else:
            out["scrape_status"] = "no_text_found"

    except Exception as exc:  # noqa: BLE001 - queremos capturar qualquer falha por registro
        out["scrape_status"] = "error"
        out["error_message"] = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()

    return out


def _save_raw_text(record: dict) -> str | None:
    full_text = record.get("full_text")
    if not full_text:
        return None
    date_part = record.get("meeting_date") or "unknown-date"
    solr_suffix = (record.get("solr_id") or "").rsplit("/", 1)[-1]
    filename = f"{date_part}_{solr_suffix}.txt" if solr_suffix else f"{date_part}.txt"
    filename = re.sub(r'[<>:"/\\|?*]', "-", filename)
    path = config.RAW_TEXTS_DIR / filename

    header = (
        f"Titulo: {record.get('title')}\n"
        f"Data da reuniao: {record.get('meeting_date')}\n"
        f"URL: {record.get('detail_url')}\n"
        f"Fonte do texto: {record.get('text_source')}"
        + (f" ({record.get('pdf_url')})" if record.get("pdf_url") else "")
        + "\n"
        + "-" * 70
        + "\n\n"
    )
    path.write_text(header + full_text, encoding="utf-8")
    return str(path.relative_to(config.PROJECT_ROOT))


def main(limit: int | None = None):
    if not config.STATEMENTS_INDEX_JSON.exists():
        raise SystemExit(
            "data/raw/statements_index.json nao encontrado. "
            "Rode antes: python fetch_statement_list.py"
        )

    records = json.loads(config.STATEMENTS_INDEX_JSON.read_text(encoding="utf-8"))
    if limit:
        records = records[:limit]

    results = []
    for i, record in enumerate(records, start=1):
        print(f"[{i}/{len(records)}] {record.get('meeting_date')} - {record.get('title')}")
        result = scrape_one(record)
        result["raw_text_file"] = _save_raw_text(result)
        # nao guardamos o texto completo no CSV para nao inflar o arquivo -
        # ele ja foi salvo em .txt separadamente.
        result_for_dataset = {k: v for k, v in result.items() if k != "full_text"}
        results.append(result_for_dataset)
        print(f"    status={result['scrape_status']} fonte={result['text_source']} "
              f"taxa={result['policy_rate_pct']} acao={result['rate_action']}")
        time.sleep(config.REQUEST_DELAY_SECONDS)

    _forward_fill_hold_rates(results)

    config.DATASET_JSON.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    _write_csv(results)

    ok = sum(1 for r in results if r["scrape_status"] == "ok")
    print(f"\nConcluido: {ok}/{len(results)} atas com texto extraido com sucesso.")
    print(f"Dataset salvo em: {config.DATASET_JSON} e {config.DATASET_CSV}")


def _forward_fill_hold_rates(results: list[dict]):
    """
    Algumas atas dizem so 'manteve a repo rate inalterada' sem restatar o
    nivel numerico. Nesses casos (rate_action == 'hold' e policy_rate_pct
    ausente), preenche com o ultimo nivel conhecido de reuniao anterior.
    Assume que `results` ja esta em ordem cronologica ascendente.
    """
    last_known_rate = None
    for r in results:
        if r.get("policy_rate_pct") is not None:
            last_known_rate = r["policy_rate_pct"]
            r["policy_rate_source"] = "extracted"
        elif r.get("rate_action") == "hold" and last_known_rate is not None:
            r["policy_rate_pct"] = last_known_rate
            r["policy_rate_source"] = "forward_filled_from_previous_meeting"
        else:
            r["policy_rate_source"] = None


def _write_csv(results: list[dict]):
    import csv

    if not results:
        return
    fieldnames = list(results[0].keys())
    with open(config.DATASET_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)


if __name__ == "__main__":
    import sys

    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(limit=lim)
