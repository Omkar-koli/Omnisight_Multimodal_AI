from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from omnisight.jobs.refresh_jobs import (
    run_all_refresh_jobs,
    run_refresh_recommendations,
    run_refresh_reviews,
    run_refresh_trends,
)

_scheduler: BackgroundScheduler | None = None
_scheduler_lock = Lock()


JOB_REGISTRY = {
    "refresh_recommendations": run_refresh_recommendations,
    "refresh_reviews": run_refresh_reviews,
    "refresh_trends": run_refresh_trends,
    "refresh_all": run_all_refresh_jobs,
}


def _safe_job_runner(job_name: str) -> None:
    fn = JOB_REGISTRY[job_name]
    fn()


def get_scheduler() -> BackgroundScheduler:
    global _scheduler

    with _scheduler_lock:
        if _scheduler is None:
            _scheduler = BackgroundScheduler(timezone="UTC")
        return _scheduler


def start_scheduler() -> None:
    scheduler = get_scheduler()

    if scheduler.running:
        return

    # Every 6 hours
    scheduler.add_job(
        func=_safe_job_runner,
        trigger=IntervalTrigger(hours=6),
        args=["refresh_recommendations"],
        id="refresh_recommendations",
        name="refresh_recommendations",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        func=_safe_job_runner,
        trigger=IntervalTrigger(hours=6),
        args=["refresh_reviews"],
        id="refresh_reviews",
        name="refresh_reviews",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )

    # Every 12 hours
    scheduler.add_job(
        func=_safe_job_runner,
        trigger=IntervalTrigger(hours=12),
        args=["refresh_trends"],
        id="refresh_trends",
        name="refresh_trends",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )

    # Daily at 02:00 UTC
    scheduler.add_job(
        func=_safe_job_runner,
        trigger=CronTrigger(hour=2, minute=0),
        args=["refresh_all"],
        id="refresh_all",
        name="refresh_all",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=600,
    )

    scheduler.start()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)


def scheduler_snapshot() -> dict[str, Any]:
    scheduler = get_scheduler()

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "job_id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else "",
                "trigger": str(job.trigger),
                "paused": job.next_run_time is None,
            }
        )

    return {
        "running": scheduler.running,
        "timezone": str(scheduler.timezone),
        "jobs": jobs,
    }


def run_job_now(job_name: str) -> dict[str, Any]:
    if job_name not in JOB_REGISTRY:
        return {"status": "error", "message": f"Unknown job: {job_name}"}

    JOB_REGISTRY[job_name]()
    return {"status": "success", "message": f"Ran job: {job_name}"}


def pause_job(job_name: str) -> dict[str, Any]:
    scheduler = get_scheduler()

    try:
        scheduler.pause_job(job_name)
        return {"status": "success", "message": f"Paused job: {job_name}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def resume_job(job_name: str) -> dict[str, Any]:
    scheduler = get_scheduler()

    try:
        scheduler.resume_job(job_name)
        return {"status": "success", "message": f"Resumed job: {job_name}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}