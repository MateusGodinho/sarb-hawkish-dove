"""Caminhos e constantes compartilhados por todo o pipeline."""

from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

RAW_DIR = DATA_DIR / "raw"
RAW_TEXTS_DIR = DATA_DIR / "raw_texts"
PROCESSED_DIR = DATA_DIR / "processed"

STATEMENTS_INDEX_JSON = RAW_DIR / "statements_index.json"
DATASET_JSON = PROCESSED_DIR / "statements_dataset.json"
DATASET_CSV = PROCESSED_DIR / "statements_dataset.csv"
SCORES_LLM_CSV = PROCESSED_DIR / "scores_llm.csv"

# Serie diaria da SARB Policy Rate fornecida pelo usuario (fonte: pagina de
# indicadores do proprio SARB). Usada como fonte de verdade para a taxa e
# para a direcao da decisao (hike/cut/hold) em cada reuniao, no lugar de
# depender so do regex sobre o texto da ata.
POLICY_RATE_DAILY_CSV = RAW_DIR / "sarb_policy_rate_daily.csv"
POLICY_RATE_VERIFIED_CSV = PROCESSED_DIR / "policy_rate_verified.csv"

# O regime de metas de inflacao (inflation targeting) comecou em fev/2000.
# Reunioes anteriores a isso (as 5 primeiras, ainda sob o regime antigo) sao
# fora do escopo da analise de trajetoria de juros.
INFLATION_TARGETING_START = "2000-02-01"

# --- Speeches (discursos de Governor/Deputy Governors etc.) ---
SPEECHES_TAG = "SARB:Publications/speeches"
SPEECHES_URL_MARKER = "/speeches/"

SPEECHES_RAW_TEXTS_DIR = RAW_TEXTS_DIR / "speeches"
SPEECHES_INDEX_JSON = RAW_DIR / "speeches_index.json"
SPEECHES_DATASET_JSON = PROCESSED_DIR / "speeches_dataset.json"
SPEECHES_DATASET_CSV = PROCESSED_DIR / "speeches_dataset.csv"
SPEECHES_SCORES_HENRY_CSV = PROCESSED_DIR / "speeches_scores_henry.csv"

SPEECHES_RAW_TEXTS_DIR.mkdir(parents=True, exist_ok=True)

# --- Graficos finais (HTML standalone, formato "paper") ---
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

SARB_BASE_URL = "https://www.resbank.co.za"
SARB_SEARCH_API = f"{SARB_BASE_URL}/bin/sarb/solr/searchForPublication"

# Tag usado pelo site do SARB para marcar as atas do MPC no índice de busca.
MPC_TAG = "SARB:Publications/statements/monetary-policy-statements"

# Caminho de URL que confirma que o resultado é de fato uma pagina de ata
# (o indice de busca as vezes devolve conteudo relacionado com a mesma tag).
MPC_URL_MARKER = "/statements/monetary-policy-statements/"

REQUEST_TIMEOUT = 30
REQUEST_DELAY_SECONDS = 1.0  # intervalo entre requisicoes, para nao sobrecarregar o site
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) sarb-hawkish-dove-research-bot/0.1 "
    "(uso academico/pessoal; contato: mateus.godinho0704@gmail.com)"
)

for _dir in (RAW_DIR, RAW_TEXTS_DIR, PROCESSED_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
