"""
ETAPA 6 - Evolucao de topicos (Secao 2 do artigo), replicando a metodologia
de du Rand, Erasmus, Hollander, Reid & van Lill (2021): Latent Dirichlet
Allocation (LDA), seguindo Coco & Viegi (2020) na escolha do numero de
topicos. Os proprios autores relatam que essa abordagem estatistica/
agnostica e informativa para os discursos mas NAO para as atas do MPC
(texto demais focado/consistente pra o algoritmo separar em topicos uteis)
-- confirmamos o mesmo padrao rodando os dois corpora separadamente antes
desta versao, entao esta rodada e so para os discursos.

Historico de calibracao (por pedido do usuario):
  1. k=10 (mais granular que os 6 do paper), selecao qualitativa de 5 temas.
  2. Teste de sanidade com k=6 (replicando o paper ao pe da letra) confirmou
     que a pipeline reproduz os 6 temas do paper de forma robusta a seed.
  3. Ao inspecionar o k=6, "Growth/Development/Inflation" saiu misturado
     (crescimento e inflacao no mesmo topico) e "Inflation Targeting" saiu
     generico demais (mistura framework/mandato com leitura corrente de
     inflacao). Testamos k=12 e k=15, com e sem bigramas -- bigramas
     (ngram_range=(1,2)) resolveram os dois problemas, pois permitem ao LDA
     tratar frases como "inflation targeting" / "target range" como termos
     atomicos, distintos de "inflation"/"target" isolados.
  4. k=15, uni+bigramas, min_df=40, seed=99 gerou 8 temas finais (2 topicos
     brutos de crise financeira internacional fundidos em "Global Crisis,
     Debt & Fiscal Risk").
  5. Testamos reduzir para k=10 (mesmos bigramas/min_df) em varias seeds: a
     separacao Growth-vs-Inflation fica instavel entre seeds, e pior --
     Financial Stability e Global Crisis colam num so topico em varias
     seeds (perda em relacao ao k=15). Na seed=99 especificamente, Growth
     ficava limpo mas Global Crisis saia contaminado com vocabulario
     generico de discurso ("people", "speeches", "public").
  6. k=12 (mesmos bigramas/min_df=40), seed=99: resolve o problema acima --
     Financial Stability e Global Crisis saem limpos e mutuamente
     distintos pela primeira vez fora do k=15. O bloco de inflacao se
     rearranja em 3 topicos brutos (em vez de 2): dois se sobrepoem em
     "targeting" (fundidos no tema final "Inflation Targeting & Central
     Bank Mandate") e um terceiro sai sem nenhuma palavra de
     "target/targeting", puro outlook/dado corrente ("Inflation Outlook &
     Expectations"). Configuracao final adotada: k=12, uni+bigramas,
     min_df=40, seed=99 -- 12 topicos brutos, 7 temas finais (2 fundidos
     em Inflation Targeting & Central Bank Mandate; ver
     build_topic_evolution_bars.py para o mapeamento completo).

Metodologia:
  1. CountVectorizer (bag-of-words + bigramas, stopwords em ingles + lista
     propria de termos de boilerplate do SARB que aparecem em todo
     documento e nao ajudam a diferenciar topicos), min_df para cortar
     termos raros demais.
  2. LatentDirichletAllocation(n_components=N_TOPICS), sklearn, batch method.
  3. Top palavras por topico (pra rotular/interpretar cada topico -- LDA nao
     da nome aos topicos, isso e trabalho humano).
  4. Topico dominante por documento (argmax da distribuicao) e serie de
     participacao (share) de cada topico por ano, pra ver a evolucao.
  5. Documentos nao-ingleses (is_english == False -- traducoes para outras
     linguas oficiais da SARB) sao excluidos, ver flag_non_english.py.

Saida: data/processed/lda_topics_words_<corpus>.csv (top palavras por topico)
       data/processed/lda_topic_probweight_by_year_<corpus>.csv (evolucao)
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict

import numpy as np
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS

import config

N_TOPICS = 12
# seed escolhida apos testar varias (0,1,7,42,99,123): a que deu a separacao
# mais limpa dos temas de interesse.
RANDOM_STATE = 99

# Termos de "boilerplate" institucional que aparecem em quase todo
# documento (saudacoes, nome do orador, nome da instituicao) e por isso nao
# ajudam a diferenciar topicos -- removidos alem das stopwords padrao do
# ingles.
SARB_BOILERPLATE = [
    "south", "african", "africa", "reserve", "bank", "sarb", "governor",
    "deputy", "monetary", "policy", "committee", "mpc", "mr", "ms", "dr",
    "chairperson", "ladies", "gentlemen", "thank", "today", "would", "like",
    "also", "one", "two", "three", "said", "say", "well", "much", "many",
    "years", "year", "let", "us", "good", "morning", "afternoon", "evening",
    # ruido de rodape/URL do PDF
    "www", "https", "http", "pdf", "page", "quot", "resbank", "co", "za",
    # "cent" e residuo de "per cent" (grafia sul-africana/britanica de
    # percentual): o token_pattern so aceita letras, entao numeros somem e
    # "per" ja e stopword padrao do ingles, sobrando "cent" isolado toda vez
    # que um numero e citado -- nao e uma palavra com significado proprio.
    "cent",
    # nomes de Governors/Deputy Governors -- assinatura, nao topico
    "kganyago", "lesetja", "mboweni", "tito", "marcus", "gill", "stals",
    "chris", "tshazibana", "fundi", "cassim", "rashad", "mminele", "daniel",
    "groepe", "francois", "van", "der", "merwe", "die",
]


def load_docs(dataset_json, date_field):
    records = json.loads(dataset_json.read_text(encoding="utf-8"))
    docs = []
    for r in records:
        if r.get("scrape_status") != "ok" or not r.get("raw_text_file"):
            continue
        if r.get("is_english") is False:
            continue
        text_path = config.PROJECT_ROOT / r["raw_text_file"]
        if not text_path.exists():
            continue
        text = text_path.read_text(encoding="utf-8")
        docs.append({"date": r.get(date_field), "text": text, "title": r.get("title")})
    return docs


def run_lda(docs, corpus_label):
    texts = [d["text"] for d in docs]

    vectorizer = CountVectorizer(
        lowercase=True,
        token_pattern=r"\b[a-zA-Z]{3,}\b",
        stop_words=list(ENGLISH_STOP_WORDS) + SARB_BOILERPLATE,
        # du Rand et al. (2021), nota de rodape 25: cortam termos pouco
        # frequentes "to speed up the algorithm... and avoid confounding the
        # topic identification by many terms that are infrequently used" --
        # o texto principal diz "at least 50%" mas a matematica deles (22.552
        # -> 13.697 termos) so bate com um corte por CONTAGEM ABSOLUTA de
        # documentos, nao uma fracao de 50% do corpus. Ajustado para 40 (em
        # vez dos 50 originais) para compensar o vocabulario extra gerado
        # pelos bigramas sem perder termos-frase uteis mas pouco frequentes.
        min_df=40,
        # bigramas permitem ao LDA tratar frases como "inflation targeting"
        # ou "target range" como termos atomicos -- essencial para separar
        # o tema do REGIME/mandato de metas da leitura corrente de inflacao
        # (ver historico de calibracao no docstring do modulo).
        ngram_range=(1, 2),
    )
    dtm = vectorizer.fit_transform(texts)
    feature_names = vectorizer.get_feature_names_out()
    print(f"[{corpus_label}] vocabulario apos min_df=40 + bigramas: {len(feature_names)} termos")

    lda = LatentDirichletAllocation(
        n_components=N_TOPICS,
        random_state=RANDOM_STATE,
        learning_method="batch",
        max_iter=50,
    )
    doc_topic = lda.fit_transform(dtm)

    # top palavras por topico
    top_words_rows = []
    for topic_idx, topic in enumerate(lda.components_):
        top_indices = topic.argsort()[::-1][:15]
        top_words = [feature_names[i] for i in top_indices]
        top_words_rows.append({
            "corpus": corpus_label,
            "topic": topic_idx,
            "top_words": ", ".join(top_words),
        })

    # metodologia do paper (Figure 7): peso medio de probabilidade de cada
    # topico por documento, depois medio sobre os discursos de cada ano --
    # NAO e "topico dominante", e a media da distribuicao suave do LDA.
    year_prob_sums = defaultdict(lambda: np.zeros(N_TOPICS))
    year_prob_counts = defaultdict(int)
    for d, probs in zip(docs, doc_topic):
        year = (d["date"] or "")[:4]
        if not year:
            continue
        year_prob_sums[year] += probs
        year_prob_counts[year] += 1

    prob_rows = []
    for year in sorted(year_prob_counts):
        avg = year_prob_sums[year] / year_prob_counts[year]
        for topic_idx in range(N_TOPICS):
            prob_rows.append({
                "corpus": corpus_label,
                "year": year,
                "topic": topic_idx,
                "n_docs": year_prob_counts[year],
                "avg_probability_weight": round(float(avg[topic_idx]), 4),
            })

    return top_words_rows, prob_rows


def write_csv(rows, path):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote", path)


def main():
    speeches = load_docs(config.SPEECHES_DATASET_JSON, "publish_date")
    print(f"{len(speeches)} speeches (excluindo nao-ingles)")

    top_words, probs = run_lda(speeches, "speeches")
    write_csv(top_words, config.PROCESSED_DIR / f"lda_topics_words_speeches.csv")
    write_csv(probs, config.PROCESSED_DIR / f"lda_topic_probweight_by_year_speeches.csv")
    print(f"\n=== SPEECHES — top words per topic (k={N_TOPICS}) ===")
    for row in top_words:
        print(f"Topic {row['topic']}: {row['top_words']}")


if __name__ == "__main__":
    main()
