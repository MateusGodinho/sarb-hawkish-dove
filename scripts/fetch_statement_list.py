"""
ETAPA 1a - Coleta o indice de todas as declaracoes do MPC (Monetary Policy
Committee) publicadas no site do SARB.

O site do SARB (resbank.co.za) e um Adobe Experience Manager (AEM) que carrega
a listagem de publicacoes via uma API JSON interna (Solr) em vez de HTML
estatico. Esse endpoint foi identificado inspecionando o bundle JS do site
(clientlibs-site.min.js, funcao loadPublications):

    GET /bin/sarb/solr/searchForPublication
        ?operator=none
        &tagsListAuthored=SARB:Publications/statements/monetary-policy-statements
        &childTagSelected=
        &parentTag=Publications
        &rows=<N>
        &start=<offset>
        &year=<opcional, filtra por ano>
        &sort=publishDate_desc

Retorna JSON com {"total": int, "solrDocumentList": [...], "yearList": [...]}.

Este script pagina esse endpoint ate esgotar os resultados e salva um indice
bruto em data/raw/statements_index.json. Esse indice e usado depois pelo
scrape_statements.py para visitar cada pagina de ata individualmente.
"""

from __future__ import annotations

import json
import time
from datetime import datetime

import requests

import config


def fetch_page(rows: int, start: int) -> dict:
    params = {
        "operator": "none",
        "tagsListAuthored": config.MPC_TAG,
        "childTagSelected": "",
        "parentTag": "Publications",
        "rows": rows,
        "start": start,
        "year": "",
        "sort": "publishDate_desc",
    }
    headers = {"User-Agent": config.USER_AGENT}
    resp = requests.get(
        config.SARB_SEARCH_API,
        params=params,
        headers=headers,
        timeout=config.REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


# Correcoes manuais para casos onde o metadado publishDate do indice do
# SARB diverge da data real da reuniao (que aparece no titulo/corpo da
# propria ata). Confirmado cruzando com a serie oficial da SARB Policy Rate:
# a mudanca de taxa de nov/2010 ocorre em 19/11 (efetiva no dia seguinte a
# reuniao), consistente com reuniao em 18/11, nao 11/11 como o indice indica.
KNOWN_MEETING_DATE_CORRECTIONS = {
    "https://www.resbank.co.za/en/home/publications/publication-detail-pages/statements/monetary-policy-statements/2010/3566": "2010-11-18",
}


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


def collect_all_statements(page_size: int = 100) -> list[dict]:
    all_docs: dict[str, dict] = {}
    start = 0
    total = None

    while total is None or start < total:
        payload = fetch_page(rows=page_size, start=start)
        total = payload.get("total", 0)
        docs = payload.get("solrDocumentList", [])
        if not docs:
            break

        for doc in docs:
            url = doc.get("url", "")
            # Filtra itens que aparecem no indice por compartilhar a tag mas
            # que na verdade sao outro tipo de publicacao (ex.: comunicados
            # de nomeacao cross-tagueados como "Monetary Policy Statements").
            if config.MPC_URL_MARKER not in url:
                continue

            meeting_date = parse_publish_date(doc.get("publishDate", ""))
            full_url = config.SARB_BASE_URL + url if url.startswith("/") else url
            if full_url in KNOWN_MEETING_DATE_CORRECTIONS:
                meeting_date = KNOWN_MEETING_DATE_CORRECTIONS[full_url]
            record = {
                "meeting_date": meeting_date,
                "publish_date_raw": doc.get("publishDate"),
                "title": doc.get("title"),
                "description": doc.get("description"),
                "detail_url": config.SARB_BASE_URL + url if url.startswith("/") else url,
                "solr_id": doc.get("id"),
                "categories": doc.get("categories"),
            }
            # dedup por URL (o indice as vezes repete o mesmo documento)
            all_docs[record["detail_url"]] = record

        start += page_size
        time.sleep(config.REQUEST_DELAY_SECONDS)

    records = list(all_docs.values())
    records.sort(key=lambda r: r["meeting_date"] or "")
    return records


def main():
    print("Coletando indice de declaracoes do MPC no site do SARB...")
    records = collect_all_statements()
    print(f"Total de registros unicos coletados: {len(records)}")

    if records:
        print(f"Periodo coberto: {records[0]['meeting_date']} a {records[-1]['meeting_date']}")

    with open(config.STATEMENTS_INDEX_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Indice salvo em: {config.STATEMENTS_INDEX_JSON}")


if __name__ == "__main__":
    main()
