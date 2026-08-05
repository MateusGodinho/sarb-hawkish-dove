"""
Orquestra o pipeline completo, do inicio ao fim:

  1. fetch_statement_list.py  -> data/raw/statements_index.json
  2. scrape_statements.py     -> data/raw_texts/*.txt + data/processed/statements_dataset.*
  3. enrich_macro.py          -> preenche campos macro no dataset
  4. score_lexicon.py         -> data/processed/scores_lexicon.csv
  5. score_llm.py             -> data/processed/scores_llm.csv (SOMENTE se
                                  ANTHROPIC_API_KEY estiver configurada;
                                  senao, essa etapa e pulada com um aviso)

Uso:
    python run_pipeline.py            # roda tudo
    python run_pipeline.py --skip-llm # pula a etapa de scoring via LLM
    python run_pipeline.py --limit 10 # limita numero de atas (rapido, p/ teste)
"""

from __future__ import annotations

import argparse
import os

import enrich_macro
import fetch_statement_list
import score_lexicon
import score_llm
import scrape_statements


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-llm", action="store_true", help="pula a etapa 3b (scoring via Claude)")
    parser.add_argument("--limit", type=int, default=None, help="limita numero de atas (para teste rapido)")
    args = parser.parse_args()

    print("=" * 70)
    print("ETAPA 1a - coletando indice de atas")
    print("=" * 70)
    fetch_statement_list.main()

    print("\n" + "=" * 70)
    print("ETAPA 1b - extraindo texto/decisao/votacao de cada ata")
    print("=" * 70)
    scrape_statements.main(limit=args.limit)

    print("\n" + "=" * 70)
    print("ETAPA 2 - enriquecendo com dados macro")
    print("=" * 70)
    enrich_macro.main()

    print("\n" + "=" * 70)
    print("ETAPA 3a - scoring por lexico (contagem ponderada de termos)")
    print("=" * 70)
    score_lexicon.main()

    if args.skip_llm or not os.environ.get("ANTHROPIC_API_KEY"):
        print("\nETAPA 3b pulada (ANTHROPIC_API_KEY nao configurada ou --skip-llm usado).")
    else:
        print("\n" + "=" * 70)
        print("ETAPA 3b - scoring via API da Anthropic (Claude)")
        print("=" * 70)
        score_llm.main()

    print("\nPipeline concluido.")


if __name__ == "__main__":
    main()
