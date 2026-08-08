"""
Cruza o dataset de atas com a serie diaria oficial da SARB Policy Rate
(data/raw/sarb_policy_rate_daily.csv, fornecida pelo usuario) para obter uma
fonte de verdade para:

  - o nivel da taxa decidido em cada reuniao (policy_rate_pct)
  - a direcao da decisao (hike/cut/hold) -> muito mais confiavel do que o
    regex sobre o texto da ata, que falhava em ~40% das reunioes.

Metodologia por reuniao:
  1. before_rate = valor da serie no ultimo dia ANTES da data da reuniao
  2. after_rate  = valor da serie no primeiro dia NA OU APOS a data da reuniao
  3. se after_rate != before_rate -> a reuniao mudou a taxa (hike se subiu,
     cut se desceu); o novo nivel (after_rate) e o policy_rate_pct da reuniao.
     se sao iguais -> hold.

Essa comparacao "antes vs depois" e auto-contida por reuniao (nao depende de
encadear o resultado da reuniao anterior), e funciona tanto para o caso em
que o SARB aplica a nova taxa no mesmo dia do anuncio quanto no dia seguinte
(ambos os padroes aparecem na serie historica).

Escopo: conforme combinado, so faz sentido comparar a partir do inicio do
regime de metas de inflacao (fev/2000) -- config.INFLATION_TARGETING_START.
A serie fornecida comeca em 2002-01-02, entao reunioes entre fev/2000 e
jan/2002 ficam marcadas como "sem cobertura da serie" (usam o valor do
regex como esta, sem verificacao independente).

Saida: data/processed/policy_rate_verified.csv, com o valor por regex lado a
lado com o valor pela serie, para voce conferir as discrepancias.
"""

from __future__ import annotations

import csv
import json
from bisect import bisect_left

import config


def load_series() -> tuple[list[str], list[float]]:
    dates, values = [], []
    with open(config.POLICY_RATE_DAILY_CSV, encoding="utf-8-sig") as f:
        lines = f.readlines()

    # o CSV tem um cabecalho de descricao antes da tabela real (Date,Value)
    start = next(i for i, line in enumerate(lines) if line.strip() == "Date,Value") + 1
    rows = [line.strip() for line in lines[start:] if line.strip()]

    parsed = []
    for row in rows:
        date_str, value_str = row.split(",")
        parsed.append((date_str.strip(), float(value_str.strip())))
    parsed.sort(key=lambda p: p[0])

    dates = [p[0] for p in parsed]
    values = [p[1] for p in parsed]
    return dates, values


def lookup_before_after(dates: list[str], values: list[float], meeting_date: str):
    """
    Retorna (before_rate, after_rate) usando busca binaria na serie ordenada.

    A serie da SARB reflete a nova taxa a partir do dia SEGUINTE ao anuncio
    (o dia da propria reuniao ainda mostra a taxa antiga) -- confirmado
    comparando varias reunioes conhecidas (ex.: 2015-11-19 -> 6,00% no dia
    19, 6,25% a partir do dia 20; 2025-01-30 -> 7,75% no dia 30, 7,50% a
    partir do dia 31). Por isso:
      - before_rate = valor NA data da reuniao (ou no ultimo dia disponivel
        antes dela, se a data exata nao estiver na serie)
      - after_rate  = valor no primeiro dia ESTRITAMENTE POSTERIOR a ela
    """
    idx = bisect_left(dates, meeting_date)
    if idx < len(dates) and dates[idx] == meeting_date:
        before_rate = values[idx]
        after_idx = idx + 1
    else:
        before_rate = values[idx - 1] if idx > 0 else None
        after_idx = idx
    after_rate = values[after_idx] if after_idx < len(dates) else None
    return before_rate, after_rate


def main():
    dates, values = load_series()
    print(f"Serie carregada: {len(dates)} pontos, de {dates[0]} a {dates[-1]}")

    all_records = json.loads(config.DATASET_JSON.read_text(encoding="utf-8"))
    all_records.sort(key=lambda r: r["meeting_date"] or "")

    for r in all_records:
        r["in_scope_inflation_targeting"] = (r.get("meeting_date") or "") >= config.INFLATION_TARGETING_START
        r["policy_rate_final"] = None
        r["rate_action_final"] = None
        r["rate_source_final"] = "out_of_scope_pre_inflation_targeting" if not r["in_scope_inflation_targeting"] else None

    records = [r for r in all_records if r["in_scope_inflation_targeting"]]
    print(f"{len(records)} reunioes no escopo (>= {config.INFLATION_TARGETING_START}, regime de metas de inflacao)")

    rows = []
    for r in records:
        meeting_date = r["meeting_date"]
        before, after = lookup_before_after(dates, values, meeting_date)

        if before is None or after is None:
            series_rate = None
            series_action = None
            series_change_bps = None
            note = "sem_cobertura_da_serie" if meeting_date < dates[0] else "fora_do_range_da_serie"
        else:
            series_rate = after
            series_change_bps = round((after - before) * 100)
            if after > before:
                series_action = "hike"
            elif after < before:
                series_action = "cut"
            else:
                series_action = "hold"
            note = ""

        regex_rate = r.get("policy_rate_pct")
        regex_action = r.get("rate_action")

        # a serie oficial e a fonte de verdade quando disponivel; o regex
        # so e usado como fallback para o hiato fev/2000-jan/2002, que a
        # serie fornecida nao cobre.
        if series_action is not None:
            r["policy_rate_final"] = series_rate
            r["rate_action_final"] = series_action
            r["rate_source_final"] = "official_series"
        elif regex_rate not in (None, "", "TODO") or regex_action:
            r["policy_rate_final"] = regex_rate
            r["rate_action_final"] = regex_action
            r["rate_source_final"] = "regex_fallback_no_series_coverage"
        else:
            r["policy_rate_final"] = None
            r["rate_action_final"] = None
            r["rate_source_final"] = "no_data"

        def _rate_match():
            if series_rate is None or regex_rate in (None, "", "TODO"):
                return None
            try:
                return abs(float(regex_rate) - series_rate) < 0.01
            except (TypeError, ValueError):
                return None

        rows.append({
            "meeting_date": meeting_date,
            "title": r.get("title"),
            "regex_rate": regex_rate,
            "regex_action": regex_action,
            "series_before_rate": before,
            "series_after_rate": series_rate,
            "series_action": series_action,
            "series_change_bps": series_change_bps,
            "rate_match": _rate_match(),
            "action_match": (regex_action == series_action) if series_action else None,
            "note": note,
        })

    with open(config.POLICY_RATE_VERIFIED_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    n_covered = sum(1 for r in rows if r["series_action"] is not None)
    n_action_mismatch = sum(1 for r in rows if r["action_match"] is False)
    n_rate_mismatch = sum(1 for r in rows if r["rate_match"] is False)
    print(f"Cobertura da serie: {n_covered}/{len(rows)} reunioes")
    print(f"Divergencias regex x serie -> acao: {n_action_mismatch}, taxa: {n_rate_mismatch}")
    print(f"Salvo em: {config.POLICY_RATE_VERIFIED_CSV}")

    # grava policy_rate_final / rate_action_final / rate_source_final /
    # in_scope_inflation_targeting de volta no dataset principal, para os
    # proximos scripts (score_henry, build_combined_index) usarem a
    # versao mais confiavel.
    config.DATASET_JSON.write_text(json.dumps(all_records, ensure_ascii=False, indent=2), encoding="utf-8")
    if all_records:
        with open(config.DATASET_CSV, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_records[0].keys()))
            writer.writeheader()
            writer.writerows(all_records)
    n_final_covered = sum(1 for r in records if r.get("rate_action_final"))
    print(f"policy_rate_final/rate_action_final gravados no dataset principal "
          f"({n_final_covered}/{len(records)} reunioes no escopo com decisao final resolvida)")


if __name__ == "__main__":
    main()
