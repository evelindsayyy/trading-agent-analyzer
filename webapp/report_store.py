"""Read finished report trees from disk for the UI to display."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import config

# Ordered map of the report tree → human labels, mirroring write_report_tree().
SECTION_FILES: list[tuple[str, str]] = [
    ("1_analysts/market.md", "📈 技术面 Market"),
    ("1_analysts/sentiment.md", "💬 情绪面 Sentiment"),
    ("1_analysts/news.md", "📰 新闻/宏观 News"),
    ("1_analysts/fundamentals.md", "📊 基本面 Fundamentals"),
    ("2_research/bull.md", "🐂 多头 Bull"),
    ("2_research/bear.md", "🐻 空头 Bear"),
    ("2_research/manager.md", "⚖️ 研究主管 Manager"),
    ("3_trading/trader.md", "🧮 交易员 Trader"),
    ("4_risk/aggressive.md", "🔥 激进 Aggressive"),
    ("4_risk/conservative.md", "🛡️ 保守 Conservative"),
    ("4_risk/neutral.md", "😐 中性 Neutral"),
    ("5_portfolio/decision.md", "🏁 最终决策 Decision"),
]


@dataclass
class Run:
    name: str           # folder name, e.g. WDC_20260630_120612
    path: Path
    ticker: str
    timestamp: str      # raw YYYYMMDD_HHMMSS part


def list_runs() -> list[Run]:
    """Newest-first list of report folders under REPORTS_ROOT."""
    runs: list[Run] = []
    if not config.REPORTS_ROOT.exists():
        return runs
    for p in config.REPORTS_ROOT.iterdir():
        if not p.is_dir() or p.name.startswith("."):
            continue
        if not (p / "complete_report.md").exists():
            continue
        ticker, _, stamp = p.name.partition("_")
        runs.append(Run(name=p.name, path=p, ticker=ticker, timestamp=stamp))
    runs.sort(key=lambda r: r.timestamp, reverse=True)
    return runs


def get_run(name: str) -> Run | None:
    p = config.REPORTS_ROOT / name
    if not p.is_dir():
        return None
    ticker, _, stamp = name.partition("_")
    return Run(name=name, path=p, ticker=ticker, timestamp=stamp)


def read_section(run: Run, rel_path: str) -> str | None:
    f = run.path / rel_path
    if f.exists():
        return f.read_text(encoding="utf-8")
    return None


def available_sections(run: Run) -> list[tuple[str, str, str]]:
    """Return (rel_path, label, content) for sections that exist in this run."""
    out = []
    for rel, label in SECTION_FILES:
        content = read_section(run, rel)
        if content:
            out.append((rel, label, content))
    return out


def existing_cheatsheet(run: Run, lang: str) -> str | None:
    fname = "beginner_cheatsheet_zh.md" if lang == "zh" else "beginner_cheatsheet.md"
    return read_section(run, fname)
