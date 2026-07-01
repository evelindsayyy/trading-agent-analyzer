"""Repair unreliable ``**bold**`` markers in Chinese (CJK) markdown reports.

LLM-written reports lean on ``**bold**`` around prices/percentages, but the
markers are unreliable next to Chinese: CommonMark emphasis fails to parse when
``**`` hugs a CJK character with ASCII punctuation on the inside (``**$610**``),
when a closer has a stray leading space (``低點 **``), or when a paragraph has
an odd, orphaned ``**`` that cascades and breaks every bold after it. The
literal asterisks then leak onto the page. ``clean_markdown`` re-pairs the
markers per line, drops orphans, and re-emits each bold span with proper spacing
so it always renders cleanly.

App-wide fonts (including the CJK stack) are handled by ``webapp.ui.CSS``.
"""
from __future__ import annotations

import re

# Fullwidth + ASCII punctuation that should never have a space inserted before
# it, so a closing bold next to e.g. a fullwidth comma stays tight: ``...**，``.
_NO_SPACE_BEFORE = set("，。、；：！？）】」』’”%,.;:!?)]}…")


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
