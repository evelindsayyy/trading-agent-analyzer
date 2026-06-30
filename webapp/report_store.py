"""Read finished runs for the UI to display, via the storage layer."""
from __future__ import annotations

from dataclasses import dataclass

from . import storage

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
    name: str            # the run id, e.g. WDC_20260630_120612
    ticker: str
    timestamp: str       # raw YYYYMMDD_HHMMSS part
    signal: str | None = None


def _to_run(rec: dict) -> Run:
    name = rec["id"]
    _, _, stamp = name.partition("_")
    return Run(name=name, ticker=rec.get("ticker", ""), timestamp=stamp,
               signal=rec.get("signal"))


def list_runs() -> list[Run]:
    """Newest-first list of finished runs (those with a report)."""
    return [_to_run(r) for r in storage.list_status() if r.get("status") == "done"]


def get_run(name: str) -> Run | None:
    rec = storage.load_status(name)
    if rec is None:
        return None
    return _to_run(rec)


def available_sections(run: Run) -> list[tuple[str, str, str]]:
    """Return (rel_path, label, content) for sections present in this run."""
    files = storage.load_report_files(run.name)
    out = []
    for rel, label in SECTION_FILES:
        content = files.get(rel)
        if content:
            out.append((rel, label, content))
    return out


def report_files(run: Run) -> dict:
    """All report-tree files for a run, keyed by relative path."""
    return storage.load_report_files(run.name)


def existing_cheatsheet(run: Run, lang: str) -> str | None:
    return storage.load_cheatsheet(run.name, lang)
