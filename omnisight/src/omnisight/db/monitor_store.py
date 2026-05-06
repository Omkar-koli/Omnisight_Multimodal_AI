from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from omnisight.db.review_store import init_review_db

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_DIR = PROJECT_ROOT / "data" / "app"
DB_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_DIR / "omnisight.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_monitor_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            title TEXT DEFAULT '',
            baseline_action TEXT DEFAULT '',
            baseline_confidence REAL DEFAULT 0,
            llm_final_action TEXT DEFAULT '',
            llm_confidence REAL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def log_decision_event(
    product_id: str,
    title: str,
    baseline_action: str,
    baseline_confidence: float,
    llm_final_action: str,
    llm_confidence: float,
) -> dict[str, Any]:
    init_monitor_db()

    conn = get_conn()
    cur = conn.cursor()

    created_at = datetime.now(timezone.utc).isoformat()

    cur.execute(
        """
        INSERT INTO decision_events
        (product_id, title, baseline_action, baseline_confidence, llm_final_action, llm_confidence, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            product_id,
            title,
            baseline_action,
            baseline_confidence,
            llm_final_action,
            llm_confidence,
            created_at,
        ),
    )

    event_id = cur.lastrowid
    conn.commit()

    row = cur.execute(
        "SELECT * FROM decision_events WHERE id = ?",
        (event_id,),
    ).fetchone()

    conn.close()
    return dict(row)


def list_recent_decision_events(limit: int = 100) -> list[dict[str, Any]]:
    init_monitor_db()

    conn = get_conn()
    rows = conn.execute(
        """
        SELECT *
        FROM decision_events
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def monitoring_summary(review_stats_fn) -> dict[str, Any]:
    init_monitor_db()
    init_review_db()

    conn = get_conn()
    cur = conn.cursor()

    total_decisions = cur.execute(
        "SELECT COUNT(*) FROM decision_events"
    ).fetchone()[0]

    baseline_llm_agree_count = cur.execute(
        """
        SELECT COUNT(*)
        FROM decision_events
        WHERE baseline_action = llm_final_action
        """
    ).fetchone()[0]

    avg_llm_confidence = cur.execute(
        "SELECT AVG(llm_confidence) FROM decision_events"
    ).fetchone()[0]

    restock_now_count = cur.execute(
        "SELECT COUNT(*) FROM decision_events WHERE llm_final_action = 'RESTOCK_NOW'"
    ).fetchone()[0]

    cautious_count = cur.execute(
        "SELECT COUNT(*) FROM decision_events WHERE llm_final_action = 'RESTOCK_CAUTIOUSLY'"
    ).fetchone()[0]

    monitor_count = cur.execute(
        "SELECT COUNT(*) FROM decision_events WHERE llm_final_action = 'MONITOR'"
    ).fetchone()[0]

    hold_count = cur.execute(
        "SELECT COUNT(*) FROM decision_events WHERE llm_final_action = 'HOLD'"
    ).fetchone()[0]

    slow_count = cur.execute(
        "SELECT COUNT(*) FROM decision_events WHERE llm_final_action = 'SLOW_REPLENISHMENT'"
    ).fetchone()[0]

    quality_count = cur.execute(
        "SELECT COUNT(*) FROM decision_events WHERE llm_final_action = 'CHECK_QUALITY_BEFORE_RESTOCK'"
    ).fetchone()[0]

    conn.close()

    review_stats_data = review_stats_fn()
    total_reviews = review_stats_data["total_reviews"]
    approved_count = review_stats_data["approved_count"]
    rejected_count = review_stats_data["rejected_count"]
    deferred_count = review_stats_data["deferred_count"]

    override_rate = 0.0
    if total_reviews > 0:
        override_rate = round((rejected_count + deferred_count) / total_reviews, 4)

    agreement_rate = 0.0
    if total_decisions > 0:
        agreement_rate = round(baseline_llm_agree_count / total_decisions, 4)

    return {
        "total_decisions": int(total_decisions),
        "baseline_llm_agree_count": int(baseline_llm_agree_count),
        "baseline_llm_agreement_rate": agreement_rate,
        "avg_llm_confidence": round(float(avg_llm_confidence or 0.0), 4),
        "total_reviews": int(total_reviews),
        "override_rate": override_rate,
        "approved_count": int(approved_count),
        "rejected_count": int(rejected_count),
        "deferred_count": int(deferred_count),
        "restock_now_count": int(restock_now_count),
        "cautious_count": int(cautious_count),
        "monitor_count": int(monitor_count),
        "hold_count": int(hold_count),
        "slow_replenishment_count": int(slow_count),
        "check_quality_count": int(quality_count),
    }


def confidence_distribution() -> list[dict[str, Any]]:
    init_monitor_db()

    conn = get_conn()
    cur = conn.cursor()

    row = cur.execute(
        """
        SELECT
            SUM(CASE WHEN llm_confidence >= 0.0 AND llm_confidence < 0.4 THEN 1 ELSE 0 END) AS low_count,
            SUM(CASE WHEN llm_confidence >= 0.4 AND llm_confidence < 0.6 THEN 1 ELSE 0 END) AS medium_low_count,
            SUM(CASE WHEN llm_confidence >= 0.6 AND llm_confidence < 0.8 THEN 1 ELSE 0 END) AS medium_high_count,
            SUM(CASE WHEN llm_confidence >= 0.8 AND llm_confidence <= 1.0 THEN 1 ELSE 0 END) AS high_count
        FROM decision_events
        """
    ).fetchone()

    conn.close()

    return [
        {"bucket": "0.0-0.4", "count": int(row["low_count"] or 0)},
        {"bucket": "0.4-0.6", "count": int(row["medium_low_count"] or 0)},
        {"bucket": "0.6-0.8", "count": int(row["medium_high_count"] or 0)},
        {"bucket": "0.8-1.0", "count": int(row["high_count"] or 0)},
    ]


def decisions_over_time(days: int = 14) -> list[dict[str, Any]]:
    init_monitor_db()
    init_review_db()

    conn = get_conn()

    decision_rows = conn.execute(
        """
        SELECT substr(created_at, 1, 10) AS event_date, COUNT(*) AS decision_count
        FROM decision_events
        WHERE date(substr(created_at, 1, 10)) >= date('now', ?)
        GROUP BY substr(created_at, 1, 10)
        ORDER BY event_date ASC
        """,
        (f"-{days - 1} days",),
    ).fetchall()

    review_rows = conn.execute(
        """
        SELECT substr(created_at, 1, 10) AS event_date, COUNT(*) AS review_count
        FROM decision_reviews
        WHERE date(substr(created_at, 1, 10)) >= date('now', ?)
        GROUP BY substr(created_at, 1, 10)
        ORDER BY event_date ASC
        """,
        (f"-{days - 1} days",),
    ).fetchall()

    conn.close()

    merged: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"date": "", "decision_count": 0, "review_count": 0}
    )

    for row in decision_rows:
        d = row["event_date"]
        merged[d]["date"] = d
        merged[d]["decision_count"] = int(row["decision_count"] or 0)

    for row in review_rows:
        d = row["event_date"]
        merged[d]["date"] = d
        merged[d]["review_count"] = int(row["review_count"] or 0)

    return [merged[k] for k in sorted(merged.keys())]


def override_breakdown() -> list[dict[str, Any]]:
    init_review_db()

    conn = get_conn()
    rows = conn.execute(
        """
        SELECT
            baseline_action,
            COUNT(*) AS total_reviews,
            SUM(CASE WHEN review_action = 'APPROVE' THEN 1 ELSE 0 END) AS approve_count,
            SUM(CASE WHEN review_action = 'REJECT' THEN 1 ELSE 0 END) AS reject_count,
            SUM(CASE WHEN review_action = 'DEFER' THEN 1 ELSE 0 END) AS defer_count
        FROM decision_reviews
        GROUP BY baseline_action
        ORDER BY total_reviews DESC
        """
    ).fetchall()
    conn.close()

    out = []
    for row in rows:
        total_reviews = int(row["total_reviews"] or 0)
        reject_count = int(row["reject_count"] or 0)
        defer_count = int(row["defer_count"] or 0)

        override_rate = 0.0
        if total_reviews > 0:
            override_rate = round((reject_count + defer_count) / total_reviews, 4)

        out.append(
            {
                "baseline_action": str(row["baseline_action"] or ""),
                "total_reviews": total_reviews,
                "approve_count": int(row["approve_count"] or 0),
                "reject_count": reject_count,
                "defer_count": defer_count,
                "override_rate": override_rate,
            }
        )

    return out