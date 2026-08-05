"""
ETAPA 7 (Apendice do artigo) - Statements e speeches, separadamente, contra
o movimento de juros decidido em cada reuniao -- por pedido do usuario,
pra entender qual dos dois canais de comunicacao acompanha melhor a
decisao real, e se o tom dos discursos entre reunioes antecipa
satisfatoriamente a proxima decisao.

Escopo: a partir do inicio do regime de metas de inflacao (fev/2000,
config.INFLATION_TARGETING_START), mesmo corte usado na validacao de taxa
contra a serie oficial (build_rate_from_series.py).

Metodologia:
  1. statement_index: henry_index da propria ata daquela reuniao
     (data/processed/scores_henry.csv) -- e 1-para-1 com a decisao daquela
     reuniao, por construcao.
  2. avg_speech_index: media do henry_index dos discursos na janela
     (reuniao anterior, esta reuniao] -- ja calculado em
     build_combined_index.py (data/processed/combined_index_by_meeting.csv,
     coluna avg_speech_index). Reunioes sem nenhum discurso na janela sao
     excluidas dessa parte (nao ha sinal de discurso pra correlacionar).
  3. Para cada corpus, dois cortes:
     a. Correlacao de Pearson entre o indice e a variacao de taxa em bps
        (policy_rate_final atual - anterior) -- variavel continua, capta
        magnitude alem de direcao.
     b. Media do indice por categoria de decisao (hike/hold/cut) -- mesmo
        formato ja usado pro indice combinado (Secao 3), agora separado
        por canal.

Saida: data/processed/speech_statement_correlation.csv (long format) +
print no console com o resumo usado no texto do Apendice.
"""

from __future__ import annotations

import csv
from collections import defaultdict

import config


def read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    return cov / (vx * vy) ** 0.5 if vx and vy else float("nan")


def main():
    statements = read_csv(config.DATASET_CSV)
    statements_by_date = {r["meeting_date"]: r for r in statements}

    statement_scores = read_csv(config.PROCESSED_DIR / "scores_henry.csv")
    statement_index_by_date = {r["meeting_date"]: float(r["henry_index"]) for r in statement_scores}

    combined = read_csv(config.PROCESSED_DIR / "combined_index_by_meeting.csv")

    dates_sorted = sorted(r["meeting_date"] for r in statements if r.get("meeting_date"))
    rate_by_date = {r["meeting_date"]: r.get("policy_rate_final") for r in statements}

    def bps_change(date: str) -> float | None:
        i = dates_sorted.index(date)
        if i == 0:
            return None
        prev_rate = rate_by_date.get(dates_sorted[i - 1])
        cur_rate = rate_by_date.get(date)
        if not prev_rate or not cur_rate:
            return None
        return (float(cur_rate) - float(prev_rate)) * 100

    scope_start = config.INFLATION_TARGETING_START  # "2000-02-01"

    stmt_pairs, stmt_actions = [], defaultdict(list)
    speech_pairs, speech_actions = [], defaultdict(list)
    rows_out = []

    for r in combined:
        date = r["meeting_date"]
        if date < scope_start:
            continue
        action = statements_by_date.get(date, {}).get("rate_action_final")
        change = bps_change(date)

        s_idx = statement_index_by_date.get(date)
        if s_idx is not None and change is not None:
            stmt_pairs.append((s_idx, change))
        if s_idx is not None and action:
            stmt_actions[action].append(s_idx)

        n_speeches = int(r["n_speeches_in_window"]) if r.get("n_speeches_in_window") else 0
        p_idx = float(r["avg_speech_index"]) if n_speeches > 0 and r.get("avg_speech_index") else None
        if p_idx is not None and change is not None:
            speech_pairs.append((p_idx, change))
        if p_idx is not None and action:
            speech_actions[action].append(p_idx)

        rows_out.append({
            "meeting_date": date,
            "rate_action_final": action,
            "bps_change": change,
            "statement_index": s_idx,
            "avg_speech_index": p_idx,
            "n_speeches_in_window": n_speeches,
        })

    out_path = config.PROCESSED_DIR / "speech_statement_correlation.csv"
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        writer.writeheader()
        writer.writerows(rows_out)
    print("wrote", out_path)

    def mean(xs):
        return sum(xs) / len(xs)

    print(f"\nScope: meetings from {scope_start} onward, n={len(rows_out)}")

    print(f"\nStatements (n={len(stmt_pairs)} with known bps change):")
    print(f"  Pearson r(statement_index, bps_change) = {pearson(*zip(*stmt_pairs)):.3f}")
    for action in ("hike", "hold", "cut"):
        vals = stmt_actions.get(action, [])
        if vals:
            print(f"  {action:5s}  n={len(vals):3d}  mean statement_index={mean(vals):.3f}")

    print(f"\nSpeeches, between-meeting window (n={len(speech_pairs)} windows with speeches and known bps change):")
    print(f"  Pearson r(avg_speech_index, bps_change) = {pearson(*zip(*speech_pairs)):.3f}")
    for action in ("hike", "hold", "cut"):
        vals = speech_actions.get(action, [])
        if vals:
            print(f"  {action:5s}  n={len(vals):3d}  mean avg_speech_index={mean(vals):.3f}")


if __name__ == "__main__":
    main()
