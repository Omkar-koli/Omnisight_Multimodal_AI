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


def init_review_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            baseline_action TEXT,
            llm_action TEXT,
            reviewer_name TEXT NOT NULL,
            review_action TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def create_review(
    product_id: str,
    baseline_action: str,
    llm_action: str,
    reviewer_name: str,
    review_action: str,
    notes: str = "",
) -> dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()

    created_at = datetime.now(timezone.utc).isoformat()

    cur.execute(
        """
        INSERT INTO decision_reviews
        (product_id, baseline_action, llm_action, reviewer_name, review_action, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            product_id,
            baseline_action,
            llm_action,
            reviewer_name,
            review_action,
            notes,
            created_at,
        ),
    )

    review_id = cur.lastrowid
    conn.commit()

    row = cur.execute(
        "SELECT * FROM decision_reviews WHERE id = ?",
        (review_id,),
    ).fetchone()

    conn.close()
    return dict(row)


def list_reviews_for_product(product_id: str) -> list[dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT *
        FROM decision_reviews
        WHERE product_id = ?
        ORDER BY created_at DESC
        """,
        (product_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def review_stats() -> dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()

    total = cur.execute("SELECT COUNT(*) FROM decision_reviews").fetchone()[0]
    approved = cur.execute(
        "SELECT COUNT(*) FROM decision_reviews WHERE review_action = 'APPROVE'"
    ).fetchone()[0]
    rejected = cur.execute(
        "SELECT COUNT(*) FROM decision_reviews WHERE review_action = 'REJECT'"
    ).fetchone()[0]
    deferred = cur.execute(
        "SELECT COUNT(*) FROM decision_reviews WHERE review_action = 'DEFER'"
    ).fetchone()[0]

    conn.close()

    
    

    return {
        "total_reviews": int(total),
        "approved_count": int(approved),
        "rejected_count": int(rejected),
        "deferred_count": int(deferred),
    }

def list_reviews(
    review_action: str | None = None,
    reviewer_name: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    conn = get_conn()

    sql = """
        SELECT *
        FROM decision_reviews
        WHERE 1=1
    """
    params: list[Any] = []

    if review_action:
        sql += " AND review_action = ?"
        params.append(review_action)

    if reviewer_name:
        sql += " AND LOWER(reviewer_name) LIKE ?"
        params.append(f"%{reviewer_name.lower()}%")

    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]