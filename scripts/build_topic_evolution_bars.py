"""
ETAPA 6 (continuacao) - Versao final em barras (small multiples) da
evolucao dos temas de speeches, no layout do Figure 7 do paper: um painel
por tema, cada um com sua propria escala de eixo Y, barra = peso medio de
probabilidade do tema naquele ano.

Modelo subjacente: LDA k=12, uni+bigramas, min_df=40, seed=99, sem "cent"
no vocabulario (ver topic_modeling_lda.py para o historico completo de
calibracao).

Mapeamento topico LDA -> tema final:
  10        -> Exchange Rate Policy
  11        -> Financial Stability
  7         -> Financial and Payment System
  8         -> Growth, Development & Labour Market
  4         -> Global Crisis, Debt & Fiscal Risk
  1 + 2 + 6 -> Inflation: Targeting & Outlook (fusao final -- tentamos
               separar o desenho/mandato do regime (topico 1) da leitura
               corrente de inflacao (topicos 2+6) em varias configuracoes
               (k=10, k=12, k=15), mas a separacao nunca ficou robusta o
               suficiente para sustentar uma narrativa confiavel; por
               decisao do usuario, tratamos como um so tema)

Descartados (ruido/redundancia): topicos 0 (bond/capital markets), 3
(integracao financeira internacional generica), 5 (money supply,
regime monetario historico pre-2000), 9 (boilerplate de discurso).
"""

from __future__ import annotations

import csv
from collections import defaultdict

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config

TOPIC_GROUPS = {
    "Exchange Rate Policy": [10],
    "Financial Stability": [11],
    "Financial and Payment System": [7],
    "Growth, Development & Labour Market": [8],
    "Global Crisis, Debt & Fiscal Risk": [4],
    "Inflation: Targeting & Outlook": [1, 2, 6],
}

COLORS = {
    "Exchange Rate Policy": "#0f766e",
    "Financial Stability": "#0369a1",
    "Financial and Payment System": "#92400e",
    "Growth, Development & Labour Market": "#15803d",
    "Global Crisis, Debt & Fiscal Risk": "#be123c",
    "Inflation: Targeting & Outlook": "#7c3aed",
}

# layout 3x2, 6 temas, sem posicoes vazias
PANEL_ORDER = [
    "Exchange Rate Policy", "Inflation: Targeting & Outlook",
    "Financial Stability", "Global Crisis, Debt & Fiscal Risk",
    "Financial and Payment System", "Growth, Development & Labour Market",
]

OUT_PNG = config.PROJECT_ROOT.parent / "personal_site" / "public" / "images" / "topic-evolution-bars.png"
OUT_CSV = config.PROCESSED_DIR / "topic_evolution_final6.csv"


def main():
    by_year_topic = {}
    with open(config.PROCESSED_DIR / "lda_topic_probweight_by_year_speeches.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            by_year_topic[(r["year"], int(r["topic"]))] = float(r["avg_probability_weight"])

    years = sorted({y for (y, _) in by_year_topic})

    rows = defaultdict(dict)
    for year in years:
        for theme, topic_idxs in TOPIC_GROUPS.items():
            rows[year][theme] = sum(by_year_topic.get((year, t), 0.0) for t in topic_idxs)

    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["year"] + list(TOPIC_GROUPS))
        for year in years:
            writer.writerow([year] + [rows[year][theme] for theme in TOPIC_GROUPS])
    print("wrote", OUT_CSV)

    x = list(range(len(years)))
    tick_years = [y for y in years if y.endswith("0") or y.endswith("5")]
    tick_positions = [years.index(y) for y in tick_years]

    fig, axes = plt.subplots(3, 2, figsize=(10.5, 10), dpi=200)
    fig.patch.set_facecolor("#fcfcfb")

    for ax, theme in zip(axes.flat, PANEL_ORDER):
        color = COLORS[theme]
        y = [rows[year][theme] for year in years]
        ax.bar(x, y, color=color, width=0.78, zorder=3)

        ax.set_facecolor("#ffffff")
        ax.set_title(theme, fontsize=10.5, fontweight="bold", color=color, pad=10, loc="left")

        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_years, fontsize=8, color="#8a8983")
        ax.tick_params(axis="y", labelsize=8, colors="#8a8983")
        ax.set_ylim(0, max(y) * 1.15 if max(y) > 0 else 1)

        for spine in ("left", "right", "bottom"):
            ax.spines[spine].set_visible(False)
        ax.spines["top"].set_visible(True)
        ax.spines["top"].set_color(color)
        ax.spines["top"].set_linewidth(2.5)
        ax.grid(axis="y", color="#e7e5df", linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)

    fig.text(0.04, 0.5, "Average weight of topic", va="center", rotation="vertical",
              fontsize=11, color="#242322")
    fig.suptitle("SARB speeches: evolution of 6 selected topics (LDA, k=12, uni+bigrams)",
                  fontsize=13, fontweight="bold", color="#0b0b0b", x=0.06, ha="left", y=0.995)

    plt.tight_layout(rect=(0.06, 0.0, 1.0, 0.97))
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT_PNG, facecolor=fig.get_facecolor())
    print("wrote", OUT_PNG)

    repo_copy = config.PROJECT_ROOT / "charts" / OUT_PNG.name
    repo_copy.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(repo_copy, facecolor=fig.get_facecolor())
    print("wrote", repo_copy)


if __name__ == "__main__":
    main()
