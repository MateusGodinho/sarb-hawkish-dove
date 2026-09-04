"""
Central Bank Hawkish/Dovish Classifier — dictionary method demo.

Paste a paragraph of central bank communication (an MPC statement, a
speech excerpt, an FOMC/ECB/BoE press release — anything) and see it
scored on a hawkish/dovish scale using the Henry (2008) bag-of-words
dictionary, replicating the method used in Erasmus & Hollander (2020) and
du Rand et al. (2021) for the South African Reserve Bank.

This is the demo companion to a research project that replicates and
extends that paper through 2026: [link to article] / [link to repo].

Self-contained: only depends on `lexicon_henry.py` (the transcribed word
lists) in this same folder, plus `streamlit`. Ready to deploy as-is on
Streamlit Community Cloud (main file: app.py).
"""

from __future__ import annotations

import html
import re

import streamlit as st

from lexicon_henry import NEGATIVE_WORDS, POSITIVE_WORDS

_WORD_RE = re.compile(r"[a-zA-Z]+")

EXAMPLE_HAWKISH = (
    "The Committee judges that inflation risks remain tilted to the upside. "
    "Given the strength of recent growth and the continued increase in price "
    "pressures, the Committee agreed that a firmer policy stance is warranted "
    "to keep inflation expectations anchored."
)

EXAMPLE_DOVISH = (
    "Growth has weakened further and downside risks have increased. Given "
    "the deteriorating outlook and the decline in underlying demand, the "
    "Committee judged that a more accommodative stance would support the "
    "recovery without jeopardising the inflation target."
)


def score_text(text: str) -> dict:
    """Identical logic to scripts/score_henry.py's score_text() — see that
    module for the full methodology note. Reproduced here so this app has
    no dependency on the rest of the repo."""
    tokens = _WORD_RE.findall(text.lower())

    pos_hits: dict[str, int] = {}
    neg_hits: dict[str, int] = {}
    for tok in tokens:
        if tok in POSITIVE_WORDS:
            pos_hits[tok] = pos_hits.get(tok, 0) + 1
        elif tok in NEGATIVE_WORDS:
            neg_hits[tok] = neg_hits.get(tok, 0) + 1

    hawkish_count = sum(pos_hits.values())
    dovish_count = sum(neg_hits.values())
    total = hawkish_count + dovish_count
    index = 2 * (hawkish_count - dovish_count) / total if total else 0.0

    return {
        "index": round(index, 3),
        "hawkish_count": hawkish_count,
        "dovish_count": dovish_count,
        "total_words": len(tokens),
        "hawkish_hits": pos_hits,
        "dovish_hits": neg_hits,
    }


def label_for(index: float) -> tuple[str, str]:
    """Returns (label, color) for a given index value in [-2, 2]."""
    if index >= 0.75:
        return "Strongly hawkish", "#d95926"
    if index >= 0.15:
        return "Leaning hawkish", "#eb6834"
    if index > -0.15:
        return "Neutral", "#898781"
    if index > -0.75:
        return "Leaning dovish", "#1baf7a"
    return "Strongly dovish", "#199e70"


def highlight_html(text: str) -> str:
    """Wraps hawkish/dovish word matches in colored <span>s for display."""
    tokens = re.findall(r"[a-zA-Z]+|[^a-zA-Z]+", text)
    out = []
    for tok in tokens:
        low = tok.lower()
        if low in POSITIVE_WORDS:
            out.append(f'<span style="background:#eb683433;border-radius:3px;">{html.escape(tok)}</span>')
        elif low in NEGATIVE_WORDS:
            out.append(f'<span style="background:#1baf7a33;border-radius:3px;">{html.escape(tok)}</span>')
        else:
            out.append(html.escape(tok))
    return "".join(out)


st.set_page_config(page_title="Hawkish/Dovish Classifier", page_icon="🦅", layout="wide")

st.title("🦅 Central Bank Hawkish/Dovish Classifier")
st.caption(
    "Dictionary-based sentiment scoring for central bank communication, replicating "
    "Henry (2008) / Erasmus & Hollander (2020) — the same method used in a "
    "[full replication of du Rand et al. (2021) for the SARB](#) "
    "([code + data](#))."
)

col_input, col_examples = st.columns([3, 1])
with col_examples:
    st.markdown("**Try an example:**")
    if st.button("Hawkish example"):
        st.session_state["text_input"] = EXAMPLE_HAWKISH
    if st.button("Dovish example"):
        st.session_state["text_input"] = EXAMPLE_DOVISH

with col_input:
    text = st.text_area(
        "Paste a statement, speech excerpt, or press release:",
        key="text_input",
        height=180,
        placeholder="e.g. an FOMC statement, an ECB press conference excerpt, an MPC statement...",
    )

analyze = st.button("Analyze", type="primary")

if analyze and text.strip():
    result = score_text(text)
    label, color = label_for(result["index"])

    left, right = st.columns(2)

    with left:
        st.subheader("📖 Dictionary method (Henry 2008)")
        st.markdown(
            f'<div style="font-size:2.2rem;font-weight:700;color:{color};">'
            f'{result["index"]:+.2f} &nbsp; <span style="font-size:1.1rem;font-weight:600;">{label}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )
        st.caption("Scale: −2 (most dovish) to +2 (most hawkish). Formula: 2 × (hawkish − dovish) / (hawkish + dovish).")

        m1, m2, m3 = st.columns(3)
        m1.metric("Hawkish words", result["hawkish_count"])
        m2.metric("Dovish words", result["dovish_count"])
        m3.metric("Total words", result["total_words"])

        if result["total_words"] == 0:
            st.warning("No text to analyze.")
        elif result["hawkish_count"] + result["dovish_count"] == 0:
            st.info("No dictionary words matched — the index defaults to 0.0 (neutral) by construction, "
                    "not necessarily because the text itself is neutral in tone.")

        st.markdown("**Matched text** (orange = hawkish, green = dovish):")
        st.markdown(
            f'<div style="line-height:1.7;padding:12px;border:1px solid #33333322;border-radius:8px;">'
            f"{highlight_html(text)}</div>",
            unsafe_allow_html=True,
        )

        if result["hawkish_hits"] or result["dovish_hits"]:
            with st.expander("Word-level breakdown"):
                if result["hawkish_hits"]:
                    st.write("Hawkish:", result["hawkish_hits"])
                if result["dovish_hits"]:
                    st.write("Dovish:", result["dovish_hits"])

    with right:
        st.subheader("🤖 LLM classifier")
        st.markdown(
            '<div style="padding:24px;border:1px solid #89878166;border-radius:8px;'
            'color:#4c5b6b;text-align:center;">'
            "✅ <b>Built, in a separate repo</b><br><br>"
            "A second, LLM-based scoring method (Claude Haiku 4.5, reading for stance "
            "rather than counting words) is done and validated — try the "
            "<a href='https://sarb-hawkish-dove-llm-59qcmhguxqvpvab9kldq2q.streamlit.app/' target='_blank'>"
            "live demo</a> (both methods side by side) or see the code at "
            "<a href='https://github.com/MateusGodinho/sarb-hawkish-dove-llm' target='_blank'>"
            "sarb-hawkish-dove-llm</a>."
            "</div>",
            unsafe_allow_html=True,
        )

elif analyze:
    st.warning("Paste some text first.")

st.divider()
st.caption(
    "This is a simple bag-of-words dictionary lookup — no context, no negation-handling, "
    "no sarcasm-detection. It's a research/educational demo, not investment or policy "
    "advice, and shouldn't be the sole basis for any decision. "
    "Methodology and full results: [link to article]. Code: [link to repo]."
)
