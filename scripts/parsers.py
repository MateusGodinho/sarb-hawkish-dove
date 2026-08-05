"""
Funcoes de extracao (regex, best-effort) aplicadas ao texto de uma ata para
identificar a decisao de taxa de juros e o resultado da votacao do MPC.

Estas atas nao tem um formato 100% padronizado ao longo de 25+ anos, entao
estas funcoes sao heuristicas: elas cobrem a fraseologia mais comum usada
pelo SARB ("the MPC decided to increase/reduce/keep the repurchase rate...",
"Four members preferred an increase, while two members favoured..."), mas
podem falhar silenciosamente (retornando None) em atas com redacao atipica
-- principalmente as mais antigas (1999-2000). Sempre confira `raw_sentence`
/ `raw_matches` no dataset final antes de usar os valores numericos.
"""

from __future__ import annotations

import re

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

HIKE_WORDS = r"increase[sd]?|raise[sd]?|hike[sd]?|higher"
CUT_WORDS = r"reduce[sd]?|reduction|lower(?:ed)?|cut|decrease[sd]?"
HOLD_WORDS = r"keep|kept|leave|left|maintain(?:ed)?|unchanged|on hold"

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    return _SENTENCE_SPLIT_RE.split(text)


def _to_float(raw: str) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def extract_rate_decision(full_text: str) -> dict:
    """
    Retorna um dict:
        {
            "action": "hike" | "cut" | "hold" | None,
            "change_bps": int | None,
            "new_rate_pct": float | None,
            "raw_sentence": str | None,
        }
    """
    result = {
        "action": None,
        "change_bps": None,
        "new_rate_pct": None,
        "raw_sentence": None,
    }

    sentences = [s for s in _split_sentences(full_text) if "repurchase rate" in s.lower()]
    if not sentences:
        return result

    # Atas mais longas costumam recapitular decisoes de reunioes ANTERIORES
    # antes de declarar a decisao desta reuniao (normalmente na secao final,
    # tipo "MONETARY POLICY STANCE"). Por isso percorremos as sentencas da
    # ULTIMA para a PRIMEIRA -- a decisao mais recente/atual tende a estar
    # mais perto do fim do texto.
    sentences = list(reversed(sentences))

    rate_num = r"(\d+(?:[.,]\d+)?)"

    pattern_change = re.compile(
        rf"repurchase rate\s+by\s+(\d+)\s+basis points?\s+to\s+{rate_num}\s*(?:per\s*cent|%)",
        re.IGNORECASE,
    )
    pattern_to = re.compile(
        rf"repurchase rate\s+to\s+{rate_num}\s*(?:per\s*cent|%)",
        re.IGNORECASE,
    )
    pattern_unchanged = re.compile(
        rf"repurchase rate\s+unchanged\s+at\s+{rate_num}\s*(?:per\s*cent|%)",
        re.IGNORECASE,
    )
    pattern_current_level = re.compile(
        rf"repurchase rate\s+at\s+its\s+current\s+level\s+of\s+{rate_num}\s*(?:per\s*cent|%)",
        re.IGNORECASE,
    )

    for sentence in sentences:
        low = sentence.lower()

        m = pattern_change.search(sentence)
        if m:
            result["change_bps"] = int(m.group(1))
            result["new_rate_pct"] = _to_float(m.group(2))
            result["raw_sentence"] = sentence.strip()
            if re.search(HIKE_WORDS, low):
                result["action"] = "hike"
            elif re.search(CUT_WORDS, low):
                result["action"] = "cut"
            return result

        m = pattern_unchanged.search(sentence) or pattern_current_level.search(sentence)
        if m:
            result["action"] = "hold"
            result["change_bps"] = 0
            result["new_rate_pct"] = _to_float(m.group(1))
            result["raw_sentence"] = sentence.strip()
            return result

        m = pattern_to.search(sentence)
        if m and re.search(HIKE_WORDS + "|" + CUT_WORDS + "|" + HOLD_WORDS, low):
            result["new_rate_pct"] = _to_float(m.group(1))
            result["raw_sentence"] = sentence.strip()
            if re.search(HIKE_WORDS, low):
                result["action"] = "hike"
            elif re.search(CUT_WORDS, low):
                result["action"] = "cut"
            else:
                result["action"] = "hold"
            return result

    # segunda passada: nenhuma sentenca tinha um numero junto (ex.: "the MPC
    # decided to keep the repurchase rate unchanged for now", sem restatar o
    # nivel). Ainda assim da para inferir a ACAO (hike/cut/hold) pelo verbo,
    # mesmo sem o valor numerico -- o nivel pode ser preenchido depois por
    # forward-fill a partir da reuniao anterior (ver scrape_statements.py).
    for sentence in sentences:
        low = sentence.lower()
        if re.search(HOLD_WORDS, low):
            result["action"] = "hold"
            result["change_bps"] = 0
            result["raw_sentence"] = sentence.strip()
            return result
        if re.search(HIKE_WORDS, low):
            result["action"] = "hike"
            result["raw_sentence"] = sentence.strip()
            return result
        if re.search(CUT_WORDS, low):
            result["action"] = "cut"
            result["raw_sentence"] = sentence.strip()
            return result

    # nada casou com os padroes conhecidos - devolve a 1a sentenca como pista
    result["raw_sentence"] = sentences[0].strip()
    return result


def extract_vote_outcome(full_text: str) -> dict:
    """
    Retorna um dict:
        {
            "unanimous": bool | None,
            "vote_breakdown": [{"count": int, "position": str}, ...],
            "raw_sentence": str | None,
        }
    """
    result = {"unanimous": None, "vote_breakdown": [], "raw_sentence": None}

    sentences = _split_sentences(full_text)

    vote_part_re = re.compile(
        r"\b(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)\s+members?\s+"
        r"(?:preferred|favoured|favored|supported|voted for)\s+([^.;]+)",
        re.IGNORECASE,
    )

    for sentence in sentences:
        matches = list(vote_part_re.finditer(sentence))
        if matches:
            result["unanimous"] = False
            result["raw_sentence"] = sentence.strip()
            for m in matches:
                count = NUMBER_WORDS.get(m.group(1).lower())
                position = m.group(2).strip().rstrip(",")
                result["vote_breakdown"].append({"count": count, "position": position})
            return result

        if re.search(r"\bunanimous(?:ly)?\b", sentence, re.IGNORECASE) and (
            "mpc" in sentence.lower() or "decision" in sentence.lower() or "vote" in sentence.lower()
        ):
            result["unanimous"] = True
            result["raw_sentence"] = sentence.strip()
            return result

    return result
