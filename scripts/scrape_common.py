"""
Funcoes de scraping compartilhadas entre scrape_statements.py e
scrape_speeches.py: download com retry, extracao de texto de paginas HTML
(com fallback pra PDF) do site do SARB. Ver scrape_statements.py para a
descricao completa das eras de template identificadas no site.
"""

from __future__ import annotations

import io
import re
import time

import requests
from bs4 import BeautifulSoup

import config

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None

HEADERS = {"User-Agent": config.USER_AGENT}

PDF_SKIP_HINTS = ("forecast", "assumption", "table", "fan", "scenario", "annexure")


def get_with_retries(url: str, max_retries: int = 3, **kwargs) -> requests.Response:
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=config.REQUEST_TIMEOUT, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            wait = 2 ** attempt
            print(f"    aviso: tentativa {attempt}/{max_retries} falhou ({exc}); aguardando {wait}s")
            time.sleep(wait)
    raise last_exc


def _dedup_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def choose_main_pdf(pdf_urls: list[str]) -> str | None:
    candidates = _dedup_preserve_order(pdf_urls)
    if not candidates:
        return None

    def score(url: str) -> int:
        name = url.rsplit("/", 1)[-1].lower()
        if any(hint in name for hint in PDF_SKIP_HINTS):
            return -10
        # "mpc" sozinho e generico demais (bate em "MPC fan ....pdf" tanto
        # quanto no documento real) -- so "statement"/"speech" contam como
        # sinal positivo forte.
        if "statement" in name or "speech" in name:
            return 10
        return 0

    # empate: prefere o nome de arquivo mais longo (anexos costumam ter
    # nomes curtos e genericos; o documento principal tende a ser descritivo)
    candidates.sort(key=lambda u: (score(u), len(u.rsplit("/", 1)[-1])), reverse=True)
    return candidates[0]


def extract_html_page(soup: BeautifulSoup) -> dict:
    """
    Extrai texto (+ widgets de taxa/inflacao quando presentes) de uma
    pagina HTML do site do SARB. Funciona tanto para atas do MPC (que tem
    widgets e um bloco iniciando com "Statement of the Monetary Policy
    Committee") quanto para speeches (que normalmente sao um unico bloco
    richtext sem widgets, capturado pelo fallback "maior bloco de texto").
    """
    blocks = soup.select('[class*="richtext"]')
    texts = [b.get_text(" ", strip=True) for b in blocks]

    repo_rate_widget = None
    inflation_widget = None
    main_text = None

    skip_prefixes = (
        "current repo rate", "current inflation rate", "inflation target",
        "upcoming announcements",
    )
    extra_blocks = []

    for t in texts:
        low = t.lower()
        if low.startswith("current repo rate"):
            m = re.search(r"([\d]+(?:[.,]\d+)?)\s*%", t)
            if m:
                repo_rate_widget = float(m.group(1).replace(",", "."))
        elif low.startswith("current inflation rate"):
            m = re.search(r"([\d]+(?:[.,]\d+)?)\s*%", t)
            if m:
                inflation_widget = float(m.group(1).replace(",", "."))
        elif low.startswith("statement of the monetary policy committee") and len(t) > 500:
            main_text = t
        elif not any(low.startswith(p) for p in skip_prefixes):
            extra_blocks.append(t)

    if main_text is None:
        long_blocks = [t for t in texts if len(t) > 500]
        if long_blocks:
            main_text = max(long_blocks, key=len)

    full_text = main_text
    if full_text and extra_blocks:
        full_text = full_text + "\n" + "\n".join(extra_blocks)

    return {
        "full_text": full_text,
        "repo_rate_widget_pct": repo_rate_widget,
        "inflation_headline_widget_pct": inflation_widget,
    }


def extract_pdf_page(soup: BeautifulSoup) -> dict:
    """Baixa e extrai texto do PDF principal linkado numa pagina (fallback quando nao ha HTML)."""
    pdf_links = [
        a["href"] for a in soup.find_all("a", href=True) if a["href"].lower().endswith(".pdf")
    ]
    pdf_links = [
        (config.SARB_BASE_URL + href) if href.startswith("/") else href for href in pdf_links
    ]
    chosen = choose_main_pdf(pdf_links)
    if chosen is None:
        return {"full_text": None, "pdf_url": None}

    if pdfplumber is None:
        raise RuntimeError("pdfplumber nao esta instalado (pip install pdfplumber)")

    resp = get_with_retries(chosen)
    with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    return {"full_text": text.strip() or None, "pdf_url": chosen}


def extract_page_text(detail_url: str) -> dict:
    """
    Ponto de entrada unico: baixa a pagina de detalhe, tenta HTML, cai para
    PDF. Devolve dict com full_text, text_source ('html'|'pdf'|None),
    pdf_url, repo_rate_widget_pct, inflation_headline_widget_pct.
    """
    resp = get_with_retries(detail_url)
    soup = BeautifulSoup(resp.text, "lxml")

    html_result = extract_html_page(soup)
    if html_result["full_text"]:
        return {
            "full_text": html_result["full_text"],
            "text_source": "html",
            "pdf_url": None,
            "repo_rate_widget_pct": html_result["repo_rate_widget_pct"],
            "inflation_headline_widget_pct": html_result["inflation_headline_widget_pct"],
        }

    pdf_result = extract_pdf_page(soup)
    return {
        "full_text": pdf_result["full_text"],
        "text_source": "pdf" if pdf_result["full_text"] else None,
        "pdf_url": pdf_result.get("pdf_url"),
        "repo_rate_widget_pct": None,
        "inflation_headline_widget_pct": None,
    }


def sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "-", name)
