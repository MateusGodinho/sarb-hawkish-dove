"""
ETAPA 2 - Enriquecimento com dados macro (inflacao e taxa repo vigentes em
cada reuniao).

O que ja vem "de graca" da propria pagina do SARB (scrape_statements.py):
  - policy_rate_pct: nivel da taxa repo apos a decisao daquela reuniao
    (extraido do texto da ata via regex, com fallback para o widget "Current
    Repo Rate" nas paginas >= 2024).
  - inflation_headline_widget_pct: inflacao headline (CPI) vigente no momento
    da publicacao, mas SO disponivel nas paginas >= 2024, que tem o widget
    "Current Inflation Rate". Para reunioes mais antigas isso fica None.

O que este script faz:
  1. Copia inflation_headline_widget_pct para inflation_headline_pct quando
     disponivel.
  2. Se existir um arquivo data/raw/external_macro_series.csv (fornecido
     manualmente pelo usuario, com colunas: date,cpi_headline,cpi_core),
     usa-o para preencher os buracos (match pela data <= meeting_date mais
     proxima, "as of" a reuniao).
  3. Onde nao houver dado nenhum, mantem o campo como "TODO" explicito, para
     deixar claro que ainda falta preencher (ex.: via SARB API / Stats SA /
     FRED) numa proxima iteracao.

Fontes sugeridas para preencher o TODO depois:
  - SARB Online Statistical Query (BA900 / KBP series) - inflacao e repo rate
    historicos: https://www.resbank.co.za/en/home/what-we-do/statistics
  - Stats SA (CPI headline e core oficiais): https://www.statssa.gov.za
  - FRED (serie "South Africa Consumer Price Index"): https://fred.stlouisfed.org
"""

from __future__ import annotations

import csv
import json
from bisect import bisect_right

import config

EXTERNAL_MACRO_CSV = config.RAW_DIR / "external_macro_series.csv"


def _load_external_series() -> list[tuple[str, dict]]:
    if not EXTERNAL_MACRO_CSV.exists():
        return []
    rows = []
    with open(EXTERNAL_MACRO_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append((row["date"], row))
    rows.sort(key=lambda r: r[0])
    return rows


def _lookup_as_of(series: list[tuple[str, dict]], date: str) -> dict | None:
    if not series or not date:
        return None
    dates = [d for d, _ in series]
    idx = bisect_right(dates, date) - 1
    if idx < 0:
        return None
    return series[idx][1]


def enrich(records: list[dict]) -> list[dict]:
    external_series = _load_external_series()
    if external_series:
        print(f"Serie macro externa encontrada: {EXTERNAL_MACRO_CSV} ({len(external_series)} pontos)")
    else:
        print(
            f"Nenhuma serie macro externa em {EXTERNAL_MACRO_CSV}. "
            "Campos sem dado do widget do SARB ficarao como TODO."
        )

    for r in records:
        widget_infl = r.get("inflation_headline_widget_pct")
        ext = _lookup_as_of(external_series, r.get("meeting_date"))

        if widget_infl not in (None, ""):
            r["inflation_headline_pct"] = widget_infl
            r["inflation_headline_source"] = "sarb_website_widget"
        elif ext and ext.get("cpi_headline"):
            r["inflation_headline_pct"] = ext["cpi_headline"]
            r["inflation_headline_source"] = "external_macro_series.csv"
        else:
            r["inflation_headline_pct"] = "TODO"
            r["inflation_headline_source"] = "TODO"

        if ext and ext.get("cpi_core"):
            r["inflation_core_pct"] = ext["cpi_core"]
            r["inflation_core_source"] = "external_macro_series.csv"
        else:
            r["inflation_core_pct"] = "TODO"
            r["inflation_core_source"] = "TODO"

        # policy_rate_pct ja vem do scraper (extraido da propria ata); so
        # marcamos TODO explicito quando nao foi possivel extrair.
        if r.get("policy_rate_pct") in (None, ""):
            r["policy_rate_pct"] = "TODO"

    return records


def main():
    if not config.DATASET_JSON.exists():
        raise SystemExit(
            "data/processed/statements_dataset.json nao encontrado. "
            "Rode antes: python scrape_statements.py"
        )

    records = json.loads(config.DATASET_JSON.read_text(encoding="utf-8"))
    records = enrich(records)

    config.DATASET_JSON.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    if records:
        fieldnames = list(records[0].keys())
        with open(config.DATASET_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

    print(f"Dataset enriquecido salvo em: {config.DATASET_JSON} e {config.DATASET_CSV}")


if __name__ == "__main__":
    main()
