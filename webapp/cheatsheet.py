"""Generate the beginner cheatsheet by running the Claude-Code skill prompt
against a finished report — but as a backend LLM call instead of in the CLI.

The skill's SKILL.md is the single source of truth: we read its body and use it
as the system prompt, then hand the model the actual report files (so it does
not need filesystem access) plus the language and holdings context.
"""
from __future__ import annotations

import os

from . import config, storage
from .report_store import Run

# Files the skills tell us to read, in priority order. We skip complete_report.md.
_CHEATSHEET_SOURCES = [
    "5_portfolio/decision.md",
    "3_trading/trader.md",
    "2_research/manager.md",
    "1_analysts/market.md",
    "key_levels_cheatsheet.md",
    "1_analysts/sentiment.md",
    "1_analysts/news.md",
    "2_research/bull.md",
    "2_research/bear.md",
]


def _skill_body(lang: str) -> str:
    """Read the SKILL.md body (frontmatter stripped) for the chosen language."""
    skill_name = config.SKILL_ZH if lang == "zh" else config.SKILL_EN
    skill_path = config.SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_path.exists():
        raise FileNotFoundError(
            f"找不到技能提示词：{skill_path}。请确认 WEBAPP_SKILLS_DIR 指向你的 skills 目录。"
        )
    text = skill_path.read_text(encoding="utf-8")
    # Strip the YAML frontmatter between the first pair of '---' fences.
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            text = parts[2]
    return text.strip()


def _gather_report_text(run: Run) -> str:
    files = storage.load_report_files(run.name)
    chunks = []
    for rel in _CHEATSHEET_SOURCES:
        content = files.get(rel)
        if content:
            chunks.append(f"===== {rel} =====\n{content}")
    if not chunks:
        raise FileNotFoundError(f"该报告没有可用的角色文件：{run.name}")
    return "\n\n".join(chunks)


def _resolve_provider() -> tuple[str, str]:
    """Pick (provider, model) for the cheatsheet call.

    Default to the web app's provider (DeepSeek). If that provider needs an API
    key that isn't present, fall back to the TradingAgents-configured provider so
    the app still works.
    """
    from tradingagents.llm_clients.api_key_env import get_api_key_env

    provider = config.CHEATSHEET_PROVIDER
    model = config.CHEATSHEET_MODEL
    key_env = get_api_key_env(provider)
    if key_env and not os.getenv(key_env):
        from tradingagents.default_config import DEFAULT_CONFIG

        provider = DEFAULT_CONFIG["llm_provider"]
        model = DEFAULT_CONFIG["quick_think_llm"]
    return provider, model


def _holdings_line(shares: str, cost: str, lang: str) -> str:
    shares = (shares or "").strip()
    cost = (cost or "").strip()
    if not shares:
        return ("用户未提供持仓信息——按「未提供」处理。" if lang == "zh"
                else "The user did not provide holdings — treat as 'not provided'.")
    msg = f"当前持仓：{shares} 股" if lang == "zh" else f"Current holdings: {shares} shares"
    if cost:
        msg += (f"，成本价 {cost}" if lang == "zh" else f", cost basis {cost}")
    return msg


def _build_prompts(run: Run, lang: str, shares: str, cost: str) -> tuple[str, str]:
    """Assemble the (system, user) prompt pair for a cheatsheet request."""
    system_prompt = _skill_body(lang)
    report_text = _gather_report_text(run)
    holdings = _holdings_line(shares, cost, lang)

    if lang == "zh":
        user_prompt = (
            "下面是某只股票的 TradingAgents 报告角色文件。**不要再去找文件**，"
            "直接用这些内容，严格按你（技能）规定的小节顺序、格式和硬性规则，"
            "生成一页纸的中文新手速查表。\n\n"
            f"【持仓】{holdings}\n\n"
            f"【报告内容】\n{report_text}"
        )
    else:
        user_prompt = (
            "Below are the role files of a TradingAgents report. **Do not look for "
            "files** — use this content directly and produce the one-page beginner "
            "cheatsheet, following your (the skill's) exact sections, format and hard "
            "rules.\n\n"
            f"[Holdings] {holdings}\n\n"
            f"[Report content]\n{report_text}"
        )
    return system_prompt, user_prompt


def _make_llm():
    """Build the chat model for cheatsheet generation (temperature-pinned)."""
    from tradingagents.llm_clients import create_llm_client

    provider, model = _resolve_provider()
    client = create_llm_client(provider, model, temperature=config.TEMPERATURE)
    return client.get_llm()  # the underlying LangChain chat model


def generate(run: Run, lang: str = "zh", shares: str = "", cost: str = "",
             save: bool = True) -> str:
    """Generate (and optionally save) the beginner cheatsheet markdown."""
    from tradingagents.llm_clients.base_client import normalize_content

    system_prompt, user_prompt = _build_prompts(run, lang, shares, cost)
    response = _make_llm().invoke([
        ("system", system_prompt),
        ("human", user_prompt),
    ])
    markdown = normalize_content(response).content.strip()

    if save:
        storage.save_cheatsheet(run.name, lang, markdown)

    return markdown


def stream(run: Run, lang: str = "zh", shares: str = "", cost: str = ""):
    """Yield cheatsheet markdown chunks as the model produces them.

    Built for Streamlit's ``st.write_stream`` so the user sees text appear
    immediately instead of waiting on a spinner. This does NOT persist — the
    caller saves the full string ``st.write_stream`` returns via
    ``storage.save_cheatsheet``.
    """
    from tradingagents.llm_clients.base_client import normalize_content

    system_prompt, user_prompt = _build_prompts(run, lang, shares, cost)
    for chunk in _make_llm().stream([
        ("system", system_prompt),
        ("human", user_prompt),
    ]):
        text = normalize_content(chunk).content
        if text:
            yield text
