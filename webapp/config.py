"""Web-app configuration. All values come from env (.env is loaded), with
sensible defaults so the app runs out of the box for a single user."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load the repo-root .env so the web app shares the same keys/config the CLI uses.
_REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_REPO_ROOT / ".env")


def _bridge_streamlit_secrets() -> None:
    """On Streamlit Community Cloud there is no .env — keys come from st.secrets.
    Copy any top-level string secrets into os.environ so the rest of the app
    (which reads env vars) works unchanged. Guarded so non-Streamlit contexts
    and the no-secrets case are no-ops."""
    try:
        import streamlit as st

        for key, value in st.secrets.items():
            if isinstance(value, str):
                os.environ.setdefault(key, value)
    except Exception:
        pass


_bridge_streamlit_secrets()

# Where finished report trees are written and read from. We default to the repo
# `reports/` dir — the same place existing runs and the cheatsheet skills look.
REPORTS_ROOT = Path(os.getenv("WEBAPP_REPORTS_ROOT", _REPO_ROOT / "reports"))

# Job status files live here (one JSON per run) so progress survives reruns.
JOBS_DIR = REPORTS_ROOT / ".jobs"

# LLM provider for the whole web app. Defaults to DeepSeek so the site runs on
# the DeepSeek API regardless of the CLI's global .env. Override per-deployment
# with WEBAPP_* env vars. Requires DEEPSEEK_API_KEY.
LLM_PROVIDER = os.getenv("WEBAPP_LLM_PROVIDER", "deepseek")
DEEP_MODEL = os.getenv("WEBAPP_DEEP_MODEL", "deepseek-v4-pro")    # flagship, for analysis
QUICK_MODEL = os.getenv("WEBAPP_QUICK_MODEL", "deepseek-v4-flash")  # fast, for quick steps

# Cheatsheet generation. Defaults to DeepSeek's fast model (cheap + same API as
# the rest of the site). Falls back to the TradingAgents-configured provider
# automatically if the chosen provider's key is missing (see cheatsheet.py).
CHEATSHEET_PROVIDER = os.getenv("WEBAPP_CHEATSHEET_PROVIDER", LLM_PROVIDER)
CHEATSHEET_MODEL = os.getenv("WEBAPP_CHEATSHEET_MODEL", QUICK_MODEL)

# Where the cheatsheet skill prompts live. Vendored into this repo's prompts/
# so it's self-contained; override to point at ~/.claude/skills if you'd rather
# keep the Claude-Code skills as the single source of truth.
SKILLS_DIR = Path(
    os.getenv("WEBAPP_SKILLS_DIR", _REPO_ROOT / "prompts")
)
SKILL_EN = "report-cheatsheet"
SKILL_ZH = "report-cheatsheet-zh"

# Simple shared-password gate for an internal (you + friends) deployment.
# If unset, the app runs open (fine for localhost-only use).
APP_PASSWORD = os.getenv("WEBAPP_PASSWORD", "")

# Analyst keys understood by TradingAgentsGraph(selected_analysts=...).
ANALYST_CHOICES = {
    "market": "技术面（行情与指标）",
    "social": "情绪面（社交舆情）",
    "news": "消息面（新闻与宏观）",
    "fundamentals": "基本面（财务数据）",
}

# Short Chinese names for compact display (e.g. the run cards).
ANALYST_SHORT_ZH = {
    "market": "技术面", "social": "情绪面",
    "news": "消息面", "fundamentals": "基本面",
}

# Plain-Chinese gloss for the report's final rating signal.
RATING_ZH = {
    "Buy": "买入", "Overweight": "加仓（看好）", "Hold": "持有",
    "Underweight": "减仓（看淡）", "Sell": "卖出",
}


def ensure_dirs() -> None:
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
