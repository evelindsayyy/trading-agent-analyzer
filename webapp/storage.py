"""Persistence layer with two interchangeable backends, chosen at runtime:

- **Database** (durable) when ``DATABASE_URL`` is set — used on hosted
  deployments (Streamlit Cloud's disk is ephemeral, so runs must live in a real
  DB). Works on Postgres (prod) and SQLite (local testing) via SQLAlchemy.
- **Local files** under ``reports/`` otherwise — the zero-setup laptop default.

Both backends expose the same functions, so the rest of the app never branches
on which one is active. One shared library (no per-user separation).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import config

# Files that make up a run's report tree are everything under the run dir except
# the generated cheatsheets (those are stored separately).
_CHEATSHEET_FILES = {"beginner_cheatsheet.md", "beginner_cheatsheet_zh.md"}

# Metadata keys we persist/return for a run (the report bodies live separately).
_META_KEYS = ("id", "ticker", "date", "analysts", "status",
              "created_at", "started_at", "finished_at", "signal", "error")


def database_url() -> str:
    """Normalized DATABASE_URL, or '' when unset (→ file backend)."""
    url = os.getenv("DATABASE_URL", "").strip()
    # SQLAlchemy rejects the legacy 'postgres://' scheme some hosts hand out.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def db_enabled() -> bool:
    return bool(database_url())


# --------------------------------------------------------------------------- #
# Database backend (SQLAlchemy; Postgres in prod, SQLite for local tests)
# --------------------------------------------------------------------------- #
_engine = None
_runs = None


def _db():
    """Lazily build the engine + table; return (engine, runs_table)."""
    global _engine, _runs
    if _engine is not None:
        return _engine, _runs

    from sqlalchemy import JSON, Column, MetaData, String, Table, Text, create_engine

    url = database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    meta = MetaData()
    _runs = Table(
        "runs", meta,
        Column("id", String, primary_key=True),
        Column("ticker", String),
        Column("date", String),
        Column("analysts", JSON),
        Column("status", String),
        Column("created_at", String),
        Column("started_at", String),
        Column("finished_at", String),
        Column("signal", String),
        Column("error", Text),
        Column("report", JSON),        # {rel_path: markdown}
        Column("cheatsheets", JSON),   # {lang: markdown}
    )
    meta.create_all(_engine)
    return _engine, _runs


def _meta_only(rec: dict) -> dict:
    return {k: rec.get(k) for k in _META_KEYS}


def _db_save_status(rec: dict) -> None:
    from sqlalchemy import insert, select, update
    engine, runs = _db()
    values = _meta_only(rec)
    with engine.begin() as conn:
        exists = conn.execute(select(runs.c.id).where(runs.c.id == rec["id"])).first()
        if exists:
            conn.execute(update(runs).where(runs.c.id == rec["id"]).values(**values))
        else:
            conn.execute(insert(runs).values(report={}, cheatsheets={}, **values))


def _db_load_status(run_id: str) -> dict | None:
    from sqlalchemy import select
    engine, runs = _db()
    with engine.connect() as conn:
        row = conn.execute(
            select(*[runs.c[k] for k in _META_KEYS]).where(runs.c.id == run_id)
        ).mappings().first()
    if row is None:
        return None
    rec = dict(row)
    rec["report_dir"] = rec["id"]
    return rec


def _db_list_status() -> list[dict]:
    from sqlalchemy import desc, select
    engine, runs = _db()
    with engine.connect() as conn:
        rows = conn.execute(
            select(*[runs.c[k] for k in _META_KEYS]).order_by(desc(runs.c.created_at))
        ).mappings().all()
    out = []
    for r in rows:
        rec = dict(r)
        rec["report_dir"] = rec["id"]
        out.append(rec)
    return out


def _db_save_report_files(run_id: str, files: dict) -> None:
    from sqlalchemy import update
    engine, runs = _db()
    with engine.begin() as conn:
        conn.execute(update(runs).where(runs.c.id == run_id).values(report=files))


def _db_load_report_files(run_id: str) -> dict:
    from sqlalchemy import select
    engine, runs = _db()
    with engine.connect() as conn:
        row = conn.execute(select(runs.c.report).where(runs.c.id == run_id)).first()
    return dict(row[0]) if row and row[0] else {}


def _db_save_cheatsheet(run_id: str, lang: str, content: str) -> None:
    from sqlalchemy import select, update
    engine, runs = _db()
    with engine.begin() as conn:
        row = conn.execute(select(runs.c.cheatsheets).where(runs.c.id == run_id)).first()
        sheets = dict(row[0]) if row and row[0] else {}
        sheets[lang] = content
        conn.execute(update(runs).where(runs.c.id == run_id).values(cheatsheets=sheets))


def _db_load_cheatsheet(run_id: str, lang: str) -> str | None:
    from sqlalchemy import select
    engine, runs = _db()
    with engine.connect() as conn:
        row = conn.execute(select(runs.c.cheatsheets).where(runs.c.id == run_id)).first()
    if row and row[0]:
        return row[0].get(lang)
    return None


def _size_expr(dialect: str) -> str:
    """SQL for a row's stored report+cheatsheet size. Postgres uses on-disk
    (compressed) bytes; SQLite falls back to JSON text length for tests."""
    if dialect == "postgresql":
        return "pg_column_size(report) + pg_column_size(cheatsheets)"
    return "length(CAST(report AS TEXT)) + length(CAST(cheatsheets AS TEXT))"


def _db_data_bytes() -> int:
    from sqlalchemy import text
    engine, _ = _db()
    expr = _size_expr(engine.dialect.name)
    with engine.connect() as conn:
        return int(conn.execute(text(f"SELECT COALESCE(SUM({expr}), 0) FROM runs")).scalar() or 0)


def _db_prune(limit_bytes: int, keep_min: int) -> list[str]:
    """Delete oldest finished runs until stored data is under limit_bytes,
    always keeping at least keep_min rows and never touching active runs."""
    from sqlalchemy import text
    engine, _ = _db()
    expr = _size_expr(engine.dialect.name)
    pruned: list[str] = []
    with engine.begin() as conn:
        total = int(conn.execute(text(f"SELECT COALESCE(SUM({expr}),0) FROM runs")).scalar() or 0)
        cnt = int(conn.execute(text("SELECT COUNT(*) FROM runs")).scalar() or 0)
        if total <= limit_bytes:
            return []
        rows = conn.execute(text(
            f"SELECT id, ({expr}) AS s FROM runs WHERE status='done' ORDER BY created_at ASC"
        )).all()
        for rid, s in rows:
            if total <= limit_bytes or cnt <= keep_min:
                break
            conn.execute(text("DELETE FROM runs WHERE id = :i"), {"i": rid})
            total -= int(s or 0)
            cnt -= 1
            pruned.append(rid)
    return pruned


# --------------------------------------------------------------------------- #
# File backend (laptop default — the original on-disk layout)
# --------------------------------------------------------------------------- #
def _job_file(run_id: str) -> Path:
    return config.JOBS_DIR / f"{run_id}.json"


def _file_save_status(rec: dict) -> None:
    config.ensure_dirs()
    target = _job_file(rec["id"])
    tmp = target.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, target)  # atomic: readers never see a partial file


def _file_read(f: Path) -> dict | None:
    for _ in range(3):  # tolerate a transient mid-write empty read
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _file_load_status(run_id: str) -> dict | None:
    f = _job_file(run_id)
    return _file_read(f) if f.exists() else None


def _file_list_status() -> list[dict]:
    config.ensure_dirs()
    jobs = [j for f in config.JOBS_DIR.glob("*.json") if (j := _file_read(f))]
    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
    return jobs


def _run_dir(run_id: str) -> Path:
    return config.REPORTS_ROOT / run_id


def _file_save_report_files(run_id: str, files: dict) -> None:
    # No-op: the report tree is already on disk (written by save_reports).
    pass


def _file_load_report_files(run_id: str) -> dict:
    root = _run_dir(run_id)
    if not root.is_dir():
        return {}
    out = {}
    for p in root.rglob("*.md"):
        if p.name in _CHEATSHEET_FILES:
            continue
        out[p.relative_to(root).as_posix()] = p.read_text(encoding="utf-8")
    return out


def _cheatsheet_path(run_id: str, lang: str) -> Path:
    fname = "beginner_cheatsheet_zh.md" if lang == "zh" else "beginner_cheatsheet.md"
    return _run_dir(run_id) / fname


def _file_save_cheatsheet(run_id: str, lang: str, content: str) -> None:
    p = _cheatsheet_path(run_id, lang)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _file_load_cheatsheet(run_id: str, lang: str) -> str | None:
    p = _cheatsheet_path(run_id, lang)
    return p.read_text(encoding="utf-8") if p.exists() else None


# --------------------------------------------------------------------------- #
# Public API — dispatches to whichever backend is active
# --------------------------------------------------------------------------- #
def init() -> None:
    config.ensure_dirs()  # always needed (ephemeral working copy of report files)
    if db_enabled():
        _db()  # build engine + create table


def save_status(rec: dict) -> None:
    (_db_save_status if db_enabled() else _file_save_status)(rec)


def load_status(run_id: str) -> dict | None:
    return (_db_load_status if db_enabled() else _file_load_status)(run_id)


def list_status() -> list[dict]:
    return (_db_list_status if db_enabled() else _file_list_status)()


def has_active() -> bool:
    return any(s.get("status") in ("queued", "running") for s in list_status())


def save_report_files(run_id: str, files: dict) -> None:
    (_db_save_report_files if db_enabled() else _file_save_report_files)(run_id, files)


def load_report_files(run_id: str) -> dict:
    return (_db_load_report_files if db_enabled() else _file_load_report_files)(run_id)


def data_bytes() -> int:
    """Bytes of stored report+cheatsheet data (DB backend); 0 for files."""
    return _db_data_bytes() if db_enabled() else 0


def prune(limit_mb: int | None = None, keep_min: int | None = None) -> list[str]:
    """Auto-evict oldest finished runs to keep the DB under its soft limit.

    No-op for the file backend (local disk isn't the constrained resource).
    Returns the ids that were deleted.
    """
    if not db_enabled():
        return []
    lim = (config.DB_SOFT_LIMIT_MB if limit_mb is None else limit_mb) * 1024 * 1024
    km = config.DB_KEEP_MIN_RUNS if keep_min is None else keep_min
    return _db_prune(lim, km)


def save_cheatsheet(run_id: str, lang: str, content: str) -> None:
    (_db_save_cheatsheet if db_enabled() else _file_save_cheatsheet)(run_id, lang, content)


def load_cheatsheet(run_id: str, lang: str) -> str | None:
    return (_db_load_cheatsheet if db_enabled() else _file_load_cheatsheet)(run_id, lang)
