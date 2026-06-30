# Trading Agent Analyzer

A self-contained bundle of the **TradingAgents** multi-agent analysis engine plus
a **Streamlit web UI** on top of it — so you can generate analyses, browse the
full report tree, and produce a beginner-friendly cheatsheet from the browser,
without touching the terminal. Runs on the **DeepSeek** API by default.

This repo contains both pieces, so it clones and runs on its own:

- `tradingagents/`, `cli/`, `main.py`, `pyproject.toml`, … — the analysis engine
  (a locally-modified copy of the open-source TradingAgents project; see
  **Attribution** below).
- `webapp/` — the Streamlit frontend.
- `prompts/` — the cheatsheet skill prompts the web app uses.

## Quickstart

```bash
# 1. Create/activate a Python 3.10+ env, then install everything (engine + web dep):
pip install -r requirements.txt          # or: uv pip install -r requirements.txt
#   (requirements.txt installs this repo's `tradingagents` package via pyproject,
#    plus streamlit)

# 2. Configure secrets:
cp .env.example .env
#   then edit .env and set at least:  DEEPSEEK_API_KEY=...

# 3. Launch the web app:
streamlit run webapp/app.py
```

Open http://localhost:8501.

> Prefer the terminal? The original CLI still works: `tradingagents` (or
> `python main.py`). See **[README.tradingagents.md](README.tradingagents.md)**
> for the engine's own documentation.

## The web app

| Page | What you do |
|---|---|
| 🚀 新建分析 | Enter a ticker + date, pick analysts, run. The analysis runs in the background (minutes). |
| 📋 运行记录 | Live status of every run (queued / running / done / failed), auto-refreshing. |
| 📄 报告 & 速查表 | Read the full report tree section-by-section, and generate the **beginner cheatsheet** (中文/English, optional holdings). |

### How it works

- **Runs** call `TradingAgentsGraph.propagate()` in a background thread pool
  (`webapp/job_manager.py`); status is persisted atomically to
  `reports/.jobs/*.json` so progress survives Streamlit reruns.
- **Reports** are the standard markdown tree written by `save_reports()`.
- **Cheatsheet** (`webapp/cheatsheet.py`) uses a skill's `SKILL.md` (in
  `prompts/`) as the system prompt and feeds the report files to the model via
  the engine's own `create_llm_client()` — so it shares TradingAgents' key
  handling. DeepSeek `deepseek-v4-flash` by default; falls back to the
  engine's configured provider if the chosen provider's key is missing.

### Configuration

Everything is env-driven via `.env` (see `.env.example`). The web-app knobs all
start with `WEBAPP_` (provider, models, reports dir, prompts dir, password gate).
By default the app forces DeepSeek for both analysis and the cheatsheet,
independent of whatever provider the CLI uses.

## Attribution & license

The analysis engine is **TradingAgents** by Tauric Research
(https://github.com/TauricResearch/TradingAgents), used and modified under the
**Apache License 2.0**. The upstream `LICENSE` is retained at the repo root and
the upstream README is preserved as `README.tradingagents.md`. This combined
repository is likewise distributed under Apache-2.0.

## Notes & next steps

- Run progress is coarse (queued/running/done). Node-level streaming (per-agent
  progress) is a natural follow-up via the graph's `callbacks` hook.
- For a real multi-user product you'd add accounts, per-user report isolation,
  and per-run cost caps — out of scope for this internal tool.
