from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_DIR = PROJECT_ROOT / "data" / "app"
DB_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_DIR / "omnisight.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_job_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS job_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT DEFAULT '',
            duration_seconds REAL DEFAULT 0,
            message TEXT DEFAULT ''
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS data_freshness (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset_name TEXT NOT NULL UNIQUE,
            last_refreshed_at TEXT NOT NULL,
            freshness_status TEXT NOT NULL,
            notes TEXT DEFAULT ''
        )
        """
    )

    conn.commit()
    conn.close()


def start_job(job_name: str) -> int:
    init_job_db()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO job_runs (job_name, status, started_at)
        VALUES (?, ?, ?)
        """,
        (job_name, "running", utc_now()),
    )

    job_id = cur.lastrowid
    conn.commit()
    conn.close()
    return int(job_id)


def finish_job(job_id: int, status: str, message: str = "") -> None:
    init_job_db()
    conn = get_conn()
    cur = conn.cursor()

    row = cur.execute(
        "SELECT started_at FROM job_runs WHERE id = ?",
        (job_id,),
    ).fetchone()

    finished_at = utc_now()
    duration_seconds = 0.0

    if row and row["started_at"]:
        started = datetime.fromisoformat(row["started_at"])
        finished = datetime.fromisoformat(finished_at)
        duration_seconds = round((finished - started).total_seconds(), 2)

    cur.execute(
        """
        UPDATE job_runs
        SET status = ?, finished_at = ?, duration_seconds = ?, message = ?
        WHERE id = ?
        """,
        (status, finished_at, duration_seconds, message, job_id),
    )

    conn.commit()
    conn.close()


def upsert_freshness(
    dataset_name: str,
    freshness_status: str,
    notes: str = "",
) -> None:
    init_job_db()
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO data_freshness (dataset_name, last_refreshed_at, freshness_status, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(dataset_name)
        DO UPDATE SET
            last_refreshed_at = excluded.last_refreshed_at,
            freshness_status = excluded.freshness_status,
            notes = excluded.notes
        """,
        (dataset_name, utc_now(), freshness_status, notes),
    )

    conn.commit()
    conn.close()


def list_job_runs(limit: int = 50) -> list[dict[str, Any]]:
    init_job_db()
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT *
        FROM job_runs
        ORDER BY started_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_freshness() -> list[dict[str, Any]]:
    init_job_db()
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT *
        FROM data_freshness
        ORDER BY dataset_name ASC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]