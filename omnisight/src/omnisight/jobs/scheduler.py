from __future__ import annotations

from omnisight.db.job_store import init_job_db
from omnisight.jobs.refresh_jobs import run_all_refresh_jobs


def initialize_scheduler() -> None:
    init_job_db()

    # Lightweight startup refresh
    try:
        run_all_refresh_jobs()
    except Exception:
        pass