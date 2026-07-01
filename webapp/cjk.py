"""Helpers that make Chinese (CJK) text render correctly in the Streamlit UI.

Two unrelated problems both surface as "the Chinese report looks broken":

1. Streamlit ships no CJK font, so the browser falls back per-character to
   whatever the OS happens to pick — uneven weights/sizes and the odd serif
   glyph. ``inject_fonts`` pins one clean CJK sans-serif stack.

2. LLM-written reports lean on ``**bold**`` around prices/percentages, but the
   markers are unreliable next to Chinese: CommonMark emphasis fails to parse
   when ``**`` hugs a CJK character with ASCII punctuation on the inside
   (``**$610**``), when a closer has a stray leading space (``低點 **``), or
   when a paragraph has an odd, orphaned ``**`` that cascades and breaks every
   bold after it. The literal asterisks then leak onto the page.
   ``clean_markdown`` re-pairs the markers per line, drops orphans, and re-emits
   each bold span with proper spacing so it always renders cleanly.
"""
from __future__ import annotations

import re

# A clean, consistent font stack: Latin glyphs come from the system UI font,
# CJK glyphs from the first installed Han sans-serif. Per-glyph fallback means
# Chinese always lands on one of these rather than an arbitrary OS default.
_FONT_STACK = (
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, '
    '"PingFang SC", "PingFang TC", "Microsoft YaHei", "Hiragino Sans GB", '
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
/* Keep the "reopen sidebar" control reachable after the sidebar is collapsed. */
[data-testid="stSidebarCollapsedControl"] {{
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
}}
</style>
"""

# Fullwidth + ASCII punctuation that should never have a space inserted before
# it, so a closing bold next to e.g. a fullwidth comma stays tight: ``...**，``.
_NO_SPACE_BEFORE = set("，。、；：！？）】」』’”%,.;:!?)]}…")


def inject_fonts(st) -> None:
    """Apply the CJK-aware font stack (and sidebar fix) to the app. Call once."""
    st.markdown(_FONT_CSS, unsafe_allow_html=True)


def _emit_bold(result: str, inner: str, tail: str) -> str:
    """Append a re-spaced ``**inner**`` span plus the text that follows it."""
    inner = inner.strip()
    if not inner:  # empty span — drop the now-useless delimiters
        return result + tail
    if result and not result[-1].isspace():
        result += " "
    result += f"**{inner}**"
    if tail and not tail[0].isspace() and tail[0] not in _NO_SPACE_BEFORE:
        result += " "
    return result + tail


def _process_line(line: str) -> str:
    line = re.sub(r"\*[ \t]\*", "**", line)  # mend a split "* *" back into "**"
    if "**" not in line:
        return line
    parts = line.split("**")
    pairs = (len(parts) - 1) // 2  # complete open/close pairs; the rest is orphan
    result, done, i = parts[0], 0, 1
    while i < len(parts):
        if done < pairs:
            tail = parts[i + 1] if i + 1 < len(parts) else ""
            result = _emit_bold(result, parts[i], tail)
            done += 1
            i += 2
        else:  # leftover orphan delimiter: drop it, keep the text
            result += parts[i]
            i += 1
    return result


def clean_markdown(text: str) -> str:
    """Return ``text`` with CJK-adjacent bold markers repaired.

    Re-pairs ``**`` per line so emphasis always parses, drops orphaned markers
    that would otherwise leak literal asterisks, and leaves fenced code blocks
    untouched. Plain text and already-valid markdown survive intact.
    """
    if not text:
        return text
    out, in_fence = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append(line)
            continue
        out.append(line if in_fence else _process_line(line))
    return "\n".join(out)
