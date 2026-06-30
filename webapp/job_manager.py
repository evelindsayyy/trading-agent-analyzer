"""Background runner for long TradingAgents analyses.

A full run takes minutes and makes many LLM calls, so it must not block the
Streamlit script. We run it in a thread pool and persist status + results via
the storage layer (a DB when DATABASE_URL is set, else local files). Worker
threads never touch Streamlit APIs.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from . import config, storage


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class JobManager:
    """Process-wide singleton: survives Streamlit reruns (module-level instance)."""

    def __init__(self, max_workers: int = 2):
        self._pool = ThreadPoolExecutor(max_workers=max_workers)

    def start_run(self, ticker: str, date: str, analysts: list[str],
                  debate_rounds: int = 1, risk_rounds: int = 1,
                  output_language: str | None = None) -> str:
        ticker = ticker.strip().upper()
        job_id = f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        status = {
            "id": job_id,
            "ticker": ticker,
            "date": date,
            "analysts": analysts,
            "debate_rounds": debate_rounds,
            "risk_rounds": risk_rounds,
            "output_language": output_language or config.OUTPUT_LANGUAGE,
            "status": "queued",
            "created_at": _now(),
            "started_at": None,
            "finished_at": None,
            "report_dir": job_id,
            "signal": None,
            "error": None,
        }
        storage.save_status(status)
        self._pool.submit(self._run, status)
        return job_id

    def _run(self, status: dict) -> None:
        # Heavy imports happen inside the worker so importing this module is cheap.
        try:
            status["status"] = "running"
            status["started_at"] = _now()
            storage.save_status(status)

            from tradingagents.default_config import DEFAULT_CONFIG
            from tradingagents.graph.trading_graph import TradingAgentsGraph

            cfg = DEFAULT_CONFIG.copy()
            # Force the web app's provider (DeepSeek by default) regardless of the
            # CLI's global .env. base_url=None → the client uses DeepSeek's endpoint.
            cfg["llm_provider"] = config.LLM_PROVIDER
            cfg["deep_think_llm"] = config.DEEP_MODEL
            cfg["quick_think_llm"] = config.QUICK_MODEL
            cfg["backend_url"] = None
            cfg["output_language"] = status.get("output_language") or config.OUTPUT_LANGUAGE
            cfg["max_debate_rounds"] = status["debate_rounds"]
            cfg["max_risk_discuss_rounds"] = status["risk_rounds"]

            analysts = tuple(status["analysts"]) or (
                "market", "social", "news", "fundamentals")
            ta = TradingAgentsGraph(
                selected_analysts=analysts, debug=False, config=cfg)

            final_state, signal = ta.propagate(status["ticker"], status["date"])

            # Write the report tree to local disk (this is the file backend's
            # store, and a temp source we read into the DB backend).
            report_dir = config.REPORTS_ROOT / status["id"]
            ta.save_reports(final_state, status["ticker"], report_dir)
            files = {
                p.relative_to(report_dir).as_posix(): p.read_text(encoding="utf-8")
                for p in report_dir.rglob("*.md")
            }
            storage.save_report_files(status["id"], files)

            status["status"] = "done"
            status["signal"] = str(signal)
            status["finished_at"] = _now()
            storage.save_status(status)
        except Exception as exc:  # noqa: BLE001 — surface any failure to the UI
            import traceback
            status["status"] = "failed"
            status["error"] = f"{exc}\n\n{traceback.format_exc()}"
            status["finished_at"] = _now()
            storage.save_status(status)


def list_jobs() -> list[dict]:
    """Newest-first list of all jobs."""
    return storage.list_status()


def get_job(job_id: str) -> dict | None:
    return storage.load_status(job_id)


def has_active_jobs() -> bool:
    return storage.has_active()


# Module-level singleton — one pool per Streamlit server process.
manager = JobManager()
