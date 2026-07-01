"""CJK markdown rendering helpers (webapp.cjk).

LLM reports lean on ``**bold**`` around prices/percentages, but the markers are
unreliable next to Chinese: emphasis fails to parse when ``**`` hugs CJK with
ASCII punctuation inside, when a closer has a stray leading space, or when an
orphaned ``**`` cascades through a line. ``clean_markdown`` must repair those so
no literal asterisks leak, while leaving valid markdown intact.
"""
from __future__ import annotations

import re

import pytest

from webapp import cjk


def _visible_text(html: str) -> str:
    """Rendered text with tags stripped — what the reader actually sees."""
    return re.sub(r"<[^>]+>", "", html)


@pytest.fixture(scope="module")
def render():
    md = pytest.importorskip("markdown_it").MarkdownIt("commonmark")
    return md.render


# Lines reconstructed from real broken reports (orphans, space-before-close,
# inner punctuation, split "* *"). None may leak a literal asterisk.
_LEAKY = [
    "當前 10 EMA 為 **200.34**，股價**199.36** 已連續多日低於**10 EMA",
    "從 5 月 14 日歷史高點 235.47 **至6月26日低點 **192.53，回調幅度達 ~**18.2%",
    "占比**(15%)**的仓位，止損**-8%**風險",
    "價格**$610**，目標**$700**",
    "涨幅**+5.2%**很强",
    "區間 235.47 * *至 192.53",
]

# Markdown that already parses correctly; meaning/content must be preserved.
_VALID = [
    "這是**很重要**的內容",
    "- **技術面**：偏多",
    "為**5,000**元",
    "純文字沒有強調。",
    "",
]


@pytest.mark.parametrize("raw", _LEAKY)
def test_no_literal_asterisks_leak(raw, render):
    cleaned = cjk.clean_markdown(raw)
    visible = _visible_text(render(cleaned))
    assert "*" not in visible, f"asterisk still visible: {visible!r}"


# The split "* *至 192.53" is a single orphaned marker (no pair), so it is
# correctly dropped and yields no bold — excluded from the bold assertion below.
_LEAKY_WITH_PAIRS = [c for c in _LEAKY if c.count("*") >= 4]


@pytest.mark.parametrize("raw", _LEAKY_WITH_PAIRS)
def test_repaired_lines_still_produce_bold(raw, render):
    assert "<strong>" in render(cjk.clean_markdown(raw))


@pytest.mark.parametrize("raw", _VALID)
def test_valid_markdown_text_is_preserved(raw, render):
    # Spacing may be normalised, but the visible characters must not change.
    before = _visible_text(render(raw)).replace(" ", "")
    after = _visible_text(render(cjk.clean_markdown(raw))).replace(" ", "")
    assert before == after


def test_bold_numbers_are_emphasised():
    out = cjk.clean_markdown("股價 **199.36** 偏弱")
    assert "**199.36**" in out


def test_orphan_marker_is_dropped():
    assert "**" not in cjk.clean_markdown("已連續多日低於**10 EMA")


def test_fenced_code_is_untouched():
    src = "```\nprice = a**b\n```"
    assert cjk.clean_markdown(src) == src


def test_empty_input():
    assert cjk.clean_markdown("") == ""


def test_ui_css_keeps_sidebar_reopenable():
    # The reopen control must stay visible after the sidebar is collapsed.
    from webapp import ui

    assert "stSidebarCollapsedControl" in ui.CSS
