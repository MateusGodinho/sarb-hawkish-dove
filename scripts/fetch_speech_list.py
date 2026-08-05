"""
ETAPA 1a (speeches) - Coleta o indice de todos os discursos (speeches) de
Governor/Deputy Governors e outros publicados no site do SARB.

Mesmo endpoint/API do MPC statements (ver fetch_statement_list.py para a
descoberta original), so muda a tag: SARB:Publications/speeches. Reutiliza
a logica generica de paginacao em publication_index.py.

Salva o indice bruto em data/raw/speeches_index.json.
"""

from __future__ import annotations

import json

import config
import publication_index


def main():
    print("Coletando indice de speeches no site do SARB...")
    records = publication_index.collect_all(config.SPEECHES_TAG, config.SPEECHES_URL_MARKER)
    print(f"Total de registros unicos coletados: {len(records)}")

    if records:
        print(f"Periodo coberto: {records[0]['publish_date']} a {records[-1]['publish_date']}")

    config.SPEECHES_INDEX_JSON.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Indice salvo em: {config.SPEECHES_INDEX_JSON}")


if __name__ == "__main__":
    main()
