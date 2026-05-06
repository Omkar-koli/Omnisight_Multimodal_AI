from __future__ import annotations

from pathlib import Path

import pandas as pd

from omnisight.db.job_store import (
    start_job,
    finish_job,
    upsert_freshness,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def run_refresh_recommendations() -> dict:
    job_id = start_job("refresh_recommendations")

    try:
        rec_path = PROCESSED_DIR / "recommendations.parquet"

        if not rec_path.exists():
            upsert_freshness(
                dataset_name="recommendations",
                freshness_status="missing",
                notes="recommendations.parquet not found",
            )
            finish_job(job_id, "failed", "recommendations.parquet not found")
            return {"status": "failed", "message": "recommendations.parquet not found"}

        df = pd.read_parquet(rec_path)
        row_count = len(df)

        upsert_freshness(
            dataset_name="recommendations",
            freshness_status="fresh",
            notes=f"Loaded {row_count} recommendation rows",
        )

        finish_job(job_id, "success", f"Loaded {row_count} recommendation rows")
        return {"status": "success", "message": f"Loaded {row_count} recommendation rows"}

    except Exception as e:
        finish_job(job_id, "failed", str(e))
        return {"status": "failed", "message": str(e)}


def run_refresh_reviews() -> dict:
    job_id = start_job("refresh_reviews")

    try:
        reviews_path = PROCESSED_DIR / "reviews.parquet"

        if not reviews_path.exists():
            upsert_freshness(
                dataset_name="reviews",
                freshness_status="missing",
                notes="reviews.parquet not found",
            )
            finish_job(job_id, "failed", "reviews.parquet not found")
            return {"status": "failed", "message": "reviews.parquet not found"}

        df = pd.read_parquet(reviews_path)
        row_count = len(df)

        upsert_freshness(
            dataset_name="reviews",
            freshness_status="fresh",
            notes=f"Loaded {row_count} review rows",
        )

        finish_job(job_id, "success", f"Loaded {row_count} review rows")
        return {"status": "success", "message": f"Loaded {row_count} review rows"}

    except Exception as e:
        finish_job(job_id, "failed", str(e))
        return {"status": "failed", "message": str(e)}


def run_refresh_trends() -> dict:
    job_id = start_job("refresh_trends")

    try:
        trends_path = PROCESSED_DIR / "trends.parquet"

        if not trends_path.exists():
            upsert_freshness(
                dataset_name="trends",
                freshness_status="missing",
                notes="trends.parquet not found",
            )
            finish_job(job_id, "failed", "trends.parquet not found")
            return {"status": "failed", "message": "trends.parquet not found"}

        df = pd.read_parquet(trends_path)
        row_count = len(df)

        upsert_freshness(
            dataset_name="trends",
            freshness_status="fresh",
            notes=f"Loaded {row_count} trend rows",
        )

        finish_job(job_id, "success", f"Loaded {row_count} trend rows")
        return {"status": "success", "message": f"Loaded {row_count} trend rows"}

    except Exception as e:
        finish_job(job_id, "failed", str(e))
        return {"status": "failed", "message": str(e)}


def run_all_refresh_jobs() -> dict:
    return {
        "recommendations": run_refresh_recommendations(),
        "reviews": run_refresh_reviews(),
        "trends": run_refresh_trends(),
    }