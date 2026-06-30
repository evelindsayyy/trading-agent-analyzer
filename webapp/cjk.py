"""Helpers that make Chinese (CJK) text render correctly in the Streamlit UI.

Two unrelated problems both show up as "the Chinese font looks weird":

1. Streamlit ships no CJK font, so the browser falls back per-character to
   whatever the OS happens to pick — giving uneven weights/sizes and the odd
   serif glyph. ``inject_fonts`` pins one clean CJK sans-serif stack.

2. CommonMark emphasis (``**bold**``) silently fails to parse when a ``**`` run
   is hugged by a CJK character on the outside and ASCII punctuation on the
   inside — e.g. ``价格**$610**`` or ``涨幅**+5%**``. The literal asterisks then
   leak onto the page. ``clean_markdown`` inserts a hair of space so the
   delimiters flank correctly, without touching already-valid markdown.
"""
from __future__ import annotations

import re

# A clean, consistent font stack: Latin glyphs come from the system UI font,
# CJK glyphs from the first installed Han sans-serif. Per-glyph fallback means
# Chinese always lands on one of these rather than an arbitrary OS default.
_FONT_STACK = (
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, '
    '"PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", '
    '"Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Micro Hei", '
    "sans-serif"
)

_FONT_CSS = f"""
<style>
html, body, [class*="css"], .stApp, .stMarkdown, .stMarkdown *,
button, input, textarea, select,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] * {{
    font-family: {_FONT_STACK} !important;
}}
/* Steady rhythm so mixed CJK/Latin lines don't look ragged. */
.stMarkdown p, .stMarkdown li, [data-testid="stMarkdownContainer"] p {{
    line-height: 1.7;
}}
</style>
"""

# Broad CJK range: ideographs, compatibility ideographs, and CJK/fullwidth
# punctuation. Used only to detect a CJK neighbour next to a ``*`` delimiter.
_CJK = r"㐀-鿿豈-﫿　-〿＀-￯"
# ASCII punctuation that, on the inner edge of an emphasis run, breaks flanking.
# Digits are excluded on purpose — they parse fine (e.g. ``**5,000**``).
_PUNCT = r"!\"#$%&'()+,\-./:;<=>?@\[\\\]^_`{|}~"

# CJK char immediately before a delimiter run that opens onto punctuation.
_OPEN_FAIL = re.compile(rf"([{_CJK}])(\*{{1,3}})(?=[{_PUNCT}])")
# Delimiter run closing off punctuation immediately before a CJK char.
_CLOSE_FAIL = re.compile(rf"(?<=[{_PUNCT}])(\*{{1,3}})([{_CJK}])")


def inject_fonts(st) -> None:
    """Apply the CJK-aware font stack to the whole app. Call once, early."""
    st.markdown(_FONT_CSS, unsafe_allow_html=True)


def clean_markdown(text: str) -> str:
    """Return ``text`` with CJK-adjacent emphasis delimiters made parseable.

    Non-destructive: only inserts a single space where a ``*``/``**`` run would
    otherwise render as literal asterisks. Valid markdown is left unchanged.
    """
    if not text:
        return text
    text = _OPEN_FAIL.sub(r"\1 \2", text)
    text = _CLOSE_FAIL.sub(r"\1 \2", text)
    return text
