"""CJK markdown rendering helpers (webapp.cjk).

Bold markdown around prices/percentages (``**$610**``, ``**+5%**``) fails
CommonMark emphasis flanking when hugged by Chinese characters, leaking literal
asterisks onto the page. ``clean_markdown`` must fix those without disturbing
markdown that already parses.
"""
from __future__ import annotations

import pytest

from webapp import cjk

# Patterns that leak literal ``**`` before the fix: CJK char + ``**`` + ASCII
# punctuation on the inner edge (currency, sign, bracket, percent...).
_LEAKY = [
    "价格**$610**，目标**$700**",
    "涨幅**+5.2%**很强",
    "回撤**-8%**需止损",
    "占比**(15%)**的仓位",
    "区间**[600, 700]**内",
]

# Markdown that already parses correctly and must be returned byte-for-byte.
_VALID = [
    "这是**很重要**的内容",
    "为**5,000**元",
    "纯英文 **$100** bold",
    "没有任何强调的纯文本。",
    "",
]


@pytest.fixture(scope="module")
def render():
    md = pytest.importorskip("markdown_it").MarkdownIt("commonmark")
    return lambda text: md.render(text)


@pytest.mark.parametrize("raw", _LEAKY)
def test_leaky_emphasis_no_longer_leaks(raw, render):
    cleaned = cjk.clean_markdown(raw)
    assert "**" not in render(cleaned), f"literal asterisks still leak: {cleaned!r}"
    assert "<strong>" in render(cleaned)


@pytest.mark.parametrize("raw", _VALID)
def test_valid_markdown_is_untouched(raw):
    assert cjk.clean_markdown(raw) == raw


def test_clean_markdown_handles_none_like_empty():
    assert cjk.clean_markdown("") == ""


def test_font_css_injected_once():
    calls: list[tuple[str, dict]] = []

    class _FakeSt:
        def markdown(self, body, **kwargs):
            calls.append((body, kwargs))

    cjk.inject_fonts(_FakeSt())
    assert len(calls) == 1
    body, kwargs = calls[0]
    assert kwargs.get("unsafe_allow_html") is True
    assert "font-family" in body and "PingFang SC" in body
