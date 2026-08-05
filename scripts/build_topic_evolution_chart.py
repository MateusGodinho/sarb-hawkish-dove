"""
ETAPA 6 (continuacao) - Grafico estatico da evolucao dos 5 temas finais
(selecionados qualitativamente pelo usuario a partir dos 10 topicos LDA,
ver topic_modeling_lda.py) por ano, para embutir no artigo (Secao 2).

Mapeamento topico LDA -> tema final (seed=99, ver topic_modeling_lda.py):
  9 -> Exchange Rate Policy
  4 -> Financial Stability
  5 -> Growth & Labor Market
  8 -> Inflation (targeting + expectations, o LDA nao separa os dois)
  6 -> Geopolitical & External Risk (rotulo do usuario; o topico bruto
       misturava "fiscal" com crise/divida global e nao saiu limpo como
       "Fiscal Policy" em nenhuma semente testada)

Metrica: replica exatamente a Figure 7 do paper -- peso medio de
probabilidade de cada topico por discurso (a distribuicao LDA completa do
documento, nao so o topico dominante/argmax), com a media tirada sobre os
discursos de cada ano.
"""

from __future__ import annotations

import csv
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config

TOPIC_LABELS = {
    9: "Exchange Rate Policy",
    4: "Financial Stability",
    5: "Growth & Labor Market",
    8: "Inflation (targeting + expectations)",
    6: "Geopolitical & External Risk",
}

COLORS = {
    9: "#2a78d6",
    4: "#1baf7a",
    5: "#eb6834",
    8: "#8a4ac9",
    6: "#e34948",
}

OUT_PNG = config.PROJECT_ROOT.parent / "personal_site" / "public" / "images" / "topic-evolution.png"
OUT_CSV = config.PROCESSED_DIR / "topic_evolution_final5.csv"


def main():
    rows = defaultdict(dict)
    with open(config.PROCESSED_DIR / "lda_topic_probweight_by_year_speeches.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            topic = int(r["topic"])
            if topic not in TOPIC_LABELS:
                continue
            rows[r["year"]][topic] = float(r["avg_probability_weight"])

    years = sorted(rows)

    # salva um CSV so com os 5 temas finais, ja rotulados
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["year"] + [TOPIC_LABELS[t] for t in TOPIC_LABELS])
        for year in years:
            writer.writerow([year] + [rows[year].get(t, 0.0) for t in TOPIC_LABELS])
    print("wrote", OUT_CSV)

    fig, ax = plt.subplots(figsize=(9.5, 5.2), dpi=200)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")

    x = list(range(len(years)))
    for topic, label in TOPIC_LABELS.items():
        y = [rows[year].get(topic, 0.0) for year in years]
        ax.plot(x, y, color=COLORS[topic], linewidth=2, marker="o", markersize=3, label=label)

    ax.set_xticks(x[::2])
    ax.set_xticklabels(years[::2], fontsize=8.5, color="#52514e", rotation=0)
    ax.tick_params(axis="y", labelsize=8.5, colors="#52514e")
    ax.set_ylabel("Average topic probability weight", fontsize=9.5, color="#52514e")
    ax.set_ylim(0, max(max(rows[y].values(), default=0) for y in years) * 1.15)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    for spine in ["left", "bottom"]:
        ax.spines[spine].set_color("#c3c2b7")

    ax.grid(axis="y", color="#e1e0d9", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", frameon=False, fontsize=8.5, ncol=2)
    ax.set_title("SARB speeches: evolution of 5 selected topics (LDA, k=10)", fontsize=12,
                 fontweight="bold", color="#0b0b0b", pad=14, loc="left")

    plt.tight_layout()
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT_PNG, facecolor=fig.get_facecolor())
    print("wrote", OUT_PNG)


if __name__ == "__main__":
    main()
