"""
ETAPA 6 (continuacao) - Reproduz o Figure 6 do paper (du Rand, Erasmus,
Hollander, Reid & van Lill, 2021): um painel de barras horizontais por
tema, com os termos mais associados ao topico no eixo Y e a frequencia
relativa do termo dentro do topico no eixo X (peso normalizado da linha de
lda.components_, nao apenas ranking -- e o que da a escala do Figure 6).

Reconstroi o mesmo modelo de topic_modeling_lda.py (k=12, uni+bigramas,
min_df=40, seed=99, sem "cent" no vocabulario) para ter acesso aos pesos
brutos de lda.components_ (o CSV de saida so guarda a lista de palavras,
sem peso). Usa o mesmo mapeamento de temas finais de
build_topic_evolution_bars.py -- 6 temas, um deles (Inflation: Targeting
& Outlook) fundindo 3 topicos brutos (os vetores de palavras sao somados
antes de normalizar, dando um unico ranking combinado).
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS

import config
from topic_modeling_lda import load_docs, SARB_BOILERPLATE, N_TOPICS, RANDOM_STATE
from build_topic_evolution_bars import TOPIC_GROUPS, COLORS, PANEL_ORDER

N_WORDS = 10

OUT_PNG = config.PROJECT_ROOT.parent / "personal_site" / "public" / "images" / "topic-words-bars.png"


def main():
    speeches = load_docs(config.SPEECHES_DATASET_JSON, "publish_date")
    texts = [d["text"] for d in speeches]

    vectorizer = CountVectorizer(
        lowercase=True,
        token_pattern=r"\b[a-zA-Z]{3,}\b",
        stop_words=list(ENGLISH_STOP_WORDS) + SARB_BOILERPLATE,
        min_df=40,
        ngram_range=(1, 2),
    )
    dtm = vectorizer.fit_transform(texts)
    feature_names = vectorizer.get_feature_names_out()

    lda = LatentDirichletAllocation(
        n_components=N_TOPICS, random_state=RANDOM_STATE,
        learning_method="batch", max_iter=50,
    )
    lda.fit(dtm)

    fig, axes = plt.subplots(3, 2, figsize=(11, 10), dpi=200)
    fig.patch.set_facecolor("#fcfcfb")

    for ax, theme in zip(axes.flat, PANEL_ORDER):
        topic_idxs = TOPIC_GROUPS[theme]
        combined = np.sum(lda.components_[topic_idxs, :], axis=0)
        combined = combined / combined.sum()

        top_indices = combined.argsort()[::-1][:N_WORDS]
        top_words = [feature_names[i] for i in top_indices]
        top_weights = [combined[i] for i in top_indices]

        # maior peso no topo
        color = COLORS[theme]
        y_pos = list(range(N_WORDS))[::-1]
        ax.barh(y_pos, top_weights, color=color, zorder=3)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(top_words, fontsize=8.5, color="#3a3a38")

        ax.set_facecolor("#ffffff")
        ax.set_title(theme, fontsize=10.5, fontweight="bold", color=color, pad=10, loc="left")

        ax.tick_params(axis="x", labelsize=7.5, colors="#8a8983")
        ax.set_xlim(0, max(top_weights) * 1.15)

        for spine in ("left", "right", "bottom"):
            ax.spines[spine].set_visible(False)
        ax.spines["top"].set_visible(True)
        ax.spines["top"].set_color(color)
        ax.spines["top"].set_linewidth(2.5)
        ax.grid(axis="x", color="#e7e5df", linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)

    fig.text(0.5, 0.01, "Relative frequency of term occurrence within topic",
              ha="center", fontsize=10.5, color="#242322")
    fig.suptitle("SARB speeches: top 10 terms per topic (LDA, k=12, uni+bigrams, 6 themes)",
                  fontsize=13, fontweight="bold", color="#0b0b0b", x=0.06, ha="left", y=0.995)

    plt.tight_layout(rect=(0.02, 0.02, 1.0, 0.97))
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUT_PNG, facecolor=fig.get_facecolor())
    print("wrote", OUT_PNG)

    repo_copy = config.PROJECT_ROOT / "charts" / OUT_PNG.name
    repo_copy.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(repo_copy, facecolor=fig.get_facecolor())
    print("wrote", repo_copy)


if __name__ == "__main__":
    main()
