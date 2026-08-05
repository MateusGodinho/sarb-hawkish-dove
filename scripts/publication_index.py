"""
Coleta generica do indice de qualquer secao de publicacoes do site do SARB
via a API JSON interna do site (ver fetch_statement_list.py para a
descoberta original desse endpoint). Reutilizado por fetch_statement_list.py
(tag de MPC statements) e fetch_speech_list.py (tag de speeches).
"""

from __future__ import annotations

import time
from datetime import datetime

import requests

import config


def fetch_page(tag: str, rows: int, start: int, max_retries: int = 4) -> dict:
    params = {
        "operator": "none",
        "tagsListAuthored": tag,
        "childTagSelected": "",
        "parentTag": "Publications",
        "rows": rows,
        "start": start,
        "year": "",
        "sort": "publishDate_desc",
    }
    headers = {"User-Agent": config.USER_AGENT}
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(
                config.SARB_SEARCH_API,
                params=params,
                headers=headers,
                timeout=config.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            last_exc = exc
            wait = 2 ** attempt
            print(f"    aviso: falha ao buscar pagina start={start} (tentativa {attempt}/{max_retries}); aguardando {wait}s")
            time.sleep(wait)
    raise last_exc


def parse_publish_date(raw_date: str) -> str | None:
    """Converte 'Jul 23, 2026, 5:00:00 PM' -> '2026-07-23'."""
    if not raw_date:
        return None
    for fmt in ("%b %d, %Y, %I:%M:%S %p", "%b %d, %Y"):
        try:
            return datetime.strptime(raw_date, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def collect_all(tag: str, url_marker: str, date_corrections: dict | None = None,
                 page_size: int = 100) -> list[dict]:
    """
    Pagina o endpoint de busca do SARB para uma tag de publicacao especifica
    e devolve a lista completa e deduplicada de registros, ordenada por
    data crescente.
    """
    date_corrections = date_corrections or {}
    all_docs: dict[str, dict] = {}
    start = 0
    total = None

    while total is None or start < total:
        payload = fetch_page(tag, rows=page_size, start=start)
        total = payload.get("total", 0)
        docs = payload.get("solrDocumentList", [])
        if not docs:
            break

        for doc in docs:
            url = doc.get("url", "")
            if url_marker not in url:
                continue

            full_url = config.SARB_BASE_URL + url if url.startswith("/") else url
            publish_date = parse_publish_date(doc.get("publishDate", ""))
            if full_url in date_corrections:
                publish_date = date_corrections[full_url]

            record = {
                "publish_date": publish_date,
                "publish_date_raw": doc.get("publishDate"),
                "title": doc.get("title"),
                "description": doc.get("description"),
                "detail_url": full_url,
                "solr_id": doc.get("id"),
                "categories": doc.get("categories"),
            }
            all_docs[record["detail_url"]] = record

        start += page_size
        time.sleep(config.REQUEST_DELAY_SECONDS)

    records = list(all_docs.values())
    records.sort(key=lambda r: r["publish_date"] or "")
    return records
