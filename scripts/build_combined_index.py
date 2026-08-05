"""
Combina atas do MPC (statements) e discursos (speeches) num unico indicador
hawkish/dove, na granularidade original do projeto: **por reuniao**, nao por
ano. Cada reuniao do MPC vira um ponto/barra; os discursos feitos entre a
reuniao anterior e essa reuniao (exclusive/inclusive) sao agregados e
"anexados" aquela reuniao -- e assim que o paper original pensa o problema
(uma janela de comunicacao entre duas decisoes de politica monetaria).

Usa o score Henry (2008), ja calculado separadamente para cada corpus
(scores_henry.csv / speeches_scores_henry.csv).

Metodologia da agregacao por reuniao M (decomposicao exata, pra permitir
"barras de contribuicao" por tipo de documento):

  janela(M) = (data da reuniao anterior, data de M]
              (para a 1a reuniao do MPC, janela = so a propria reuniao;
              discursos anteriores a criacao do MPC nao pertencem a nenhuma
              janela e ficam de fora dessa analise combinada)

  n_stmt = 1 (a propria ata de M)
  n_speech = numero de discursos dentro da janela(M)
  avg_stmt = henry_index da propria ata de M
  avg_speech = media do henry_index dos discursos da janela (0 se n_speech=0)
  n_total = n_stmt + n_speech

  contrib_statement = (n_stmt   / n_total) * avg_stmt
  contrib_speech    = (n_speech / n_total) * avg_speech
  combined_index    = contrib_statement + contrib_speech

Por construcao, contrib_statement + contrib_speech = combined_index
exatamente -- cada barra do grafico pode ser decomposta nessas duas
parcelas, com sinal preservado.
"""

from __future__ import annotations

import csv

import config

OUT_CSV = config.PROCESSED_DIR / "combined_index_by_meeting.csv"


def _load_rows(path, date_field: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            date = r.get(date_field)
            if not date:
                continue
            rows.append({"date": date, "index": float(r["henry_index"]), "title": r.get("title")})
    rows.sort(key=lambda r: r["date"])
    return rows


def main():
    meetings = _load_rows(config.PROCESSED_DIR / "scores_henry.csv", "meeting_date")
    speeches = _load_rows(config.PROCESSED_DIR / "speeches_scores_henry.csv", "publish_date")

    out_rows = []
    prev_date = None
    speech_i = 0  # ponteiro na lista de discursos (ja ordenada), avança sem retroceder

    for meeting in meetings:
        meeting_date = meeting["date"]

        window_scores = []
        while speech_i < len(speeches) and speeches[speech_i]["date"] <= meeting_date:
            # so conta o discurso se ha uma reuniao anterior definindo o
            # inicio da janela -- discursos antes da 1a reuniao do MPC nao
            # pertencem a janela nenhuma (sao consumidos aqui mas ignorados).
            if prev_date is not None and speeches[speech_i]["date"] > prev_date:
                window_scores.append(speeches[speech_i]["index"])
            speech_i += 1

        n_stmt = 1
        n_speech = len(window_scores)
        n_total = n_stmt + n_speech

        avg_stmt = meeting["index"]
        avg_speech = sum(window_scores) / n_speech if n_speech else 0.0

        contrib_stmt = (n_stmt / n_total) * avg_stmt
        contrib_speech = (n_speech / n_total) * avg_speech
        combined_index = contrib_stmt + contrib_speech

        out_rows.append({
            "meeting_date": meeting_date,
            "title": meeting["title"],
            "window_start": prev_date,
            "n_speeches_in_window": n_speech,
            "statement_index": round(avg_stmt, 4),
            "avg_speech_index": round(avg_speech, 4) if n_speech else None,
            "contrib_statement": round(contrib_stmt, 4),
            "contrib_speech": round(contrib_speech, 4),
            "combined_index": round(combined_index, 4),
        })

        prev_date = meeting_date

    # discursos que sobraram depois da ultima reuniao (nao pertencem a
    # nenhuma janela fechada ainda) e os anteriores a 1a reuniao ficam de
    # fora por definicao -- reportamos quantos para transparencia.
    leftover_before_first = sum(1 for s in speeches if s["date"] <= meetings[0]["date"])
    leftover_after_last = len(speeches) - speech_i

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)

    total_speeches_used = sum(r["n_speeches_in_window"] for r in out_rows)
    print(f"Indice combinado por reuniao calculado para {len(out_rows)} reunioes.")
    print(f"Discursos usados (dentro de alguma janela): {total_speeches_used}/{len(speeches)}")
    print(f"Discursos anteriores a 1a reuniao do MPC (fora de escopo): {leftover_before_first}")
    print(f"Discursos posteriores a ultima reuniao (janela ainda aberta, nao inclusos): {leftover_after_last}")
    print(f"Salvo em: {OUT_CSV}")


if __name__ == "__main__":
    main()
