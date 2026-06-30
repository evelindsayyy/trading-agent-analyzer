"""Background runner for long TradingAgents analyses.

A full run takes minutes and makes many LLM calls, so it must not block the
Streamlit script. We run it in a thread pool and persist each job's status to a
JSON file under REPORTS_ROOT/.jobs so progress survives Streamlit reruns and is
visible across browser sessions. Worker threads never touch Streamlit APIs.
"""
from __future__ import annotations

import json
import os
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from threading import Lock

from . import config

_STATUSES = ("queued", "running", "done", "failed")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _job_file(job_id: str) -> Path:
    return config.JOBS_DIR / f"{job_id}.json"


def _write_status(data: dict) -> None:
    """Atomically persist a job's status.

    A worker thread rewrites this file while the Streamlit poller reads it, so we
    write to a temp file and os.replace() it in — readers never see a partial
    file (os.replace is atomic on the same filesystem).
    """
    config.ensure_dirs()
    target = _job_file(data["id"])
    tmp = target.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, target)


def _read_status(f: Path) -> dict | None:
    """Read one job file, tolerating a transient mid-write empty read."""
    for _ in range(3):
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
    return None


class JobManager:
    """Process-wide singleton: survives Streamlit reruns (module-level instance)."""

    def __init__(self, max_workers: int = 2):
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = Lock()

    def start_run(self, ticker: str, date: str, analysts: list[str],
                  debate_rounds: int = 1, risk_rounds: int = 1) -> str:
        ticker = ticker.strip().upper()
        job_id = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        status = {
            "id": job_id,
            "ticker": ticker,
            "date": date,
            "analysts": analysts,
            "debate_rounds": debate_rounds,
            "risk_rounds": risk_rounds,
            "status": "queued",
            "created_at": _now(),
            "started_at": None,
            "finished_at": None,
            "report_dir": None,
            "signal": None,
            "error": None,
        }
        _write_status(status)
        self._pool.submit(self._run, status)
        return job_id

    def _run(self, status: dict) -> None:
        # Heavy imports happen inside the worker so importing this module is cheap
        # and does not require API keys.
        try:
            status["status"] = "running"
            status["started_at"] = _now()
            _write_status(status)

            from tradingagents.default_config import DEFAULT_CONFIG
            from tradingagents.graph.trading_graph import TradingAgentsGraph

            cfg = DEFAULT_CONFIG.copy()
            # Force the web app's provider (DeepSeek by default) so runs use it
            # regardless of the CLI's global .env. base_url=None lets the
            # OpenAI-compatible client use DeepSeek's own endpoint.
            cfg["llm_provider"] = config.LLM_PROVIDER
            cfg["deep_think_llm"] = config.DEEP_MODEL
            cfg["quick_think_llm"] = config.QUICK_MODEL
            cfg["backend_url"] = None
            cfg["max_debate_rounds"] = status["debate_rounds"]
            cfg["max_risk_discuss_rounds"] = status["risk_rounds"]

            analysts = tuple(status["analysts"]) or (
                "market", "social", "news", "fundamentals")
            ta = TradingAgentsGraph(
                selected_analysts=analysts, debug=False, config=cfg)

            final_state, signal = ta.propagate(status["ticker"], status["date"])

            report_dir = config.REPORTS_ROOT / status["id"]
            ta.save_reports(final_state, status["ticker"], report_dir)

            status["status"] = "done"
            status["signal"] = str(signal)
            status["report_dir"] = report_dir.name
            status["finished_at"] = _now()
            _write_status(status)
        except Exception as exc:  # noqa: BLE001 — surface any failure to the UI
            status["status"] = "failed"
            status["error"] = f"{exc}\n\n{traceback.format_exc()}"
            status["finished_at"] = _now()
            _write_status(status)


def list_jobs() -> list[dict]:
    """Newest-first list of all jobs from disk."""
    config.ensure_dirs()
    jobs = []
    for f in config.JOBS_DIR.glob("*.json"):
        job = _read_status(f)
        if job is not None:
            jobs.append(job)
    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    return jobs


def get_job(job_id: str) -> dict | None:
    f = _job_file(job_id)
    if f.exists():
        return _read_status(f)
    return None


def has_active_jobs() -> bool:
    return any(j["status"] in ("queued", "running") for j in list_jobs())


# Module-level singleton — one pool per Streamlit server process.
manager = JobManager()
