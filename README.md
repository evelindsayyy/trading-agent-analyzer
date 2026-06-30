# TradingAgents Web

A Streamlit front-end for [TradingAgents](https://github.com/) — generate
analyses, browse the report tree, and produce a beginner-friendly cheatsheet,
all from the browser instead of the terminal. Runs on the **DeepSeek** API.

> This repo is **just the web app**. It depends on the separate `tradingagents`
> Python package (an open-source project you install yourself — see below). That
> keeps this repo small and independently committable.

## Features

| Page | What you do |
|---|---|
| 🚀 新建分析 | Enter a ticker + date, pick analysts, run. The analysis runs in the background (minutes). |
| 📋 运行记录 | Live status of every run (queued / running / done / failed), auto-refreshing. |
| 📄 报告 & 速查表 | Read the full report tree section-by-section, and generate the **beginner cheatsheet** (中文/English, optional holdings). |

## Setup

```bash
# 1. Install the TradingAgents package (separate project) into your env.
#    Clone it if you haven't, then editable-install it:
uv pip install -e /path/to/TradingAgents      # or: pip install -e /path/to/TradingAgents

# 2. Install this app's deps.
uv pip install -r requirements.txt

# 3. Configure secrets.
cp .env.example .env
#    then edit .env and set DEEPSEEK_API_KEY=...
```

## Run

```bash
streamlit run webapp/app.py
```

Open http://localhost:8501.

## Layout

```
tradingagents-web/
├── webapp/            # the Streamlit app
│   ├── app.py         # UI + pages
│   ├── job_manager.py # background runner (thread pool, atomic JSON status)
│   ├── cheatsheet.py  # beginner cheatsheet via the vendored skill prompt
│   ├── report_store.py# read report trees from disk
│   └── config.py      # all config via env (.env)
├── prompts/           # vendored cheatsheet skill prompts (self-contained)
│   ├── report-cheatsheet/SKILL.md      # English
│   └── report-cheatsheet-zh/SKILL.md   # 中文
├── reports/           # generated output (gitignored)
├── .env.example
└── requirements.txt
```

## How it works

- **Runs** call `TradingAgentsGraph.propagate()` in a background thread pool
  (`job_manager.py`); status is persisted atomically to `reports/.jobs/*.json`
  so progress survives Streamlit reruns.
- **Reports** are the standard markdown tree written by `save_reports()`.
- **Cheatsheet** (`cheatsheet.py`) uses a skill's `SKILL.md` (in `prompts/`) as
  the system prompt and feeds the report files to the model via the project's
  own `create_llm_client()` — so it shares TradingAgents' key handling.

The cheatsheet prompts in `prompts/` are copies of the Claude-Code skills
`report-cheatsheet` / `report-cheatsheet-zh`. If you edit the originals in
`~/.claude/skills/`, copy them back here (or set `WEBAPP_SKILLS_DIR` to point at
`~/.claude/skills`).

## Notes & next steps

- Run progress is coarse (queued/running/done). Node-level streaming (per-agent
  progress) is a natural follow-up via the graph's `callbacks` hook.
- For a real multi-user product you'd add accounts, per-user report isolation,
  and per-run cost caps — out of scope for this internal tool.
