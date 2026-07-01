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

## Deploy a live site (Streamlit Community Cloud)

GitHub Pages can't host this — it only serves static files, and this is a live
Python/Streamlit server. The easiest real host is **Streamlit Community Cloud**:

1. Push this repo to GitHub (done).
2. Go to **https://share.streamlit.io** → sign in with GitHub → **New app**.
3. Pick repo **`evelindsayyy/trading-agent-analyzer`**, branch **`main`**, and set
   **Main file path** to **`webapp/app.py`**.
4. **Advanced settings**:
   - Python version: **3.12** (3.11/3.13 also fine).
   - **Secrets**: paste (see `.streamlit/secrets.toml.example`):
     ```toml
     DEEPSEEK_API_KEY = "sk-..."
     WEBAPP_PASSWORD   = "choose-a-passphrase"   # recommended: the app is public
     ```
5. **Deploy**. First build takes a few minutes (it installs the engine + deps).

The app reads those secrets as environment variables (bridged in
`webapp/config.py`), so no code changes are needed.

**Honest caveats for the free tier** — fine for a demo, not durable multi-user:
- The app **sleeps when idle**; an in-flight analysis can be killed when it
  spins down. Background runs are best kicked off while you're watching.
- Disk is **ephemeral** — generated reports under `reports/` are lost on
  restart/redeploy. (Add object storage / a DB for persistence.)
- TradingAgents runs are **multi-minute and use paid DeepSeek calls**; the
  free tier's ~1 GB RAM can be tight. Set `WEBAPP_PASSWORD` so it isn't open to
  the world running up your DeepSeek bill.

For always-on hosting with real disk, use Render / Railway / Fly.io or a VPS
(`streamlit run webapp/app.py` behind a reverse proxy) — same secrets.

## Persistence — keep runs forever (recommended for hosting)

By default the app stores runs as **local files** under `reports/`. That's perfect
on your own computer, but on a host like Streamlit Cloud the disk is **wiped on
every restart**, so generated runs would disappear. To keep every run forever in
one shared library, point the app at a free **Postgres** database by setting
`DATABASE_URL`. When it's set, the app stores all run metadata, reports, and
cheatsheets in the database instead of local files (no code changes — it just
switches backends).

### Set it up with a free database (one-time, ~3 minutes)

Using **Neon** (simplest) — or Supabase works the same way:

1. Go to **https://neon.tech** → sign up (free) → **Create project**.
2. On the project dashboard, copy the **connection string** — it looks like
   `postgresql://user:password@ep-xxxx.region.aws.neon.tech/dbname`.
3. In your **Streamlit Cloud** app → **Settings → Secrets**, add:
   ```toml
   DATABASE_URL = "postgresql://...the string you copied..."
   ```
4. Save → the app reboots → done. The app creates its table automatically on
   first start, and from now on **every run is saved permanently** and visible to
   everyone who logs in.

No database administration needed — the app manages its own schema. If
`DATABASE_URL` is wrong, the app shows a clear "database connection failed"
message instead of crashing.

> One shared library: everyone who logs in sees the same runs (matches the
> single-password setup). Per-user private histories would need real accounts —
> a larger change, not included here.

### Storage stays under the cap automatically

So a small free-tier database (e.g. Neon's 0.5 GB) never fills up:

- **Compact storage** — the redundant `complete_report.md` (a full concatenation
  of every section, never shown in the UI) is not stored, roughly halving the
  bytes per run.
- **Auto-eviction** — after each analysis, if stored data is past the soft limit,
  the oldest finished runs are deleted to make room. The sidebar shows current
  usage. Tune with:
  - `WEBAPP_DB_SOFT_LIMIT_MB` (default `350`) — start evicting past this size.
  - `WEBAPP_DB_KEEP_MIN_RUNS` (default `5`) — always keep at least this many.

  At ~35 KB per run that's ~10,000 analyses before anything is evicted.

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
