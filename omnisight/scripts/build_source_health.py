from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_LIVE_DIR = PROJECT_ROOT / "data" / "raw" / "live"
MONITORING_DIR = PROJECT_ROOT / "data" / "processed" / "monitoring"

CATALOG_HEALTH_PATH = RAW_LIVE_DIR / "catalog" / "live_catalog_health.parquet"
TRENDS_HEALTH_PATH = RAW_LIVE_DIR / "trends" / "live_trends_health.parquet"

OUTPUT_PARQUET = MONITORING_DIR / "source_health.parquet"
OUTPUT_CSV = MONITORING_DIR / "source_health.csv"


def parse_dt(value) -> datetime | None:
    if value is None:
        return None
    try:
        ts = pd.to_datetime(value, errors="coerce", utc=True)
        if pd.isna(ts):
            return None
        return ts.to_pydatetime()
    except Exception:
        return None


def compute_staleness(source_name: str, captured_at: datetime | None, now_utc: datetime) -> tuple[bool, str]:
    if captured_at is None:
        return True, "missing captured_at"

    age = now_utc - captured_at

    if source_name == "live_catalog":
        if age > timedelta(days=2):
            return True, f"older than 2 days ({age})"
        return False, ""

    if source_name == "live_trends":
        if age > timedelta(days=1):
            return True, f"older than 1 day ({age})"
        return False, ""

    return False, ""


def normalize_catalog_health(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "source_name",
                "captured_at",
                "row_count",
                "success_count",
                "failure_count",
                "status",
            ]
        )

    out = pd.DataFrame()
    out["source_name"] = df.get("source_name", "live_catalog")
    out["captured_at"] = df.get("captured_at")
    out["row_count"] = df.get("row_count", 0)
    out["success_count"] = df.get("success_count", 0)
    out["failure_count"] = df.get("failure_count", 0)
    out["status"] = df.get("status", "unknown")
    return out


def normalize_trends_health(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "source_name",
                "captured_at",
                "row_count",
                "success_count",
                "failure_count",
                "status",
            ]
        )

    out = pd.DataFrame()
    out["source_name"] = df.get("source_name", "live_trends")
    out["captured_at"] = df.get("captured_at")

    trend_rows = pd.to_numeric(df.get("trend_row_count", 0), errors="coerce").fillna(0)
    related_rows = pd.to_numeric(df.get("related_row_count", 0), errors="coerce").fillna(0)
    trending_now_rows = pd.to_numeric(df.get("trending_now_row_count", 0), errors="coerce").fillna(0)
    out["row_count"] = trend_rows + related_rows + trending_now_rows

    success_cols = [
        "timeseries_success_count",
        "related_success_count",
        "trending_now_success_count",
    ]
    failure_cols = [
        "timeseries_failure_count",
        "related_failure_count",
        "trending_now_failure_count",
    ]

    success_total = 0
    failure_total = 0

    for col in success_cols:
        if col in df.columns:
            success_total += pd.to_numeric(df[col], errors="coerce").fillna(0)
    for col in failure_cols:
        if col in df.columns:
            failure_total += pd.to_numeric(df[col], errors="coerce").fillna(0)

    out["success_count"] = success_total
    out["failure_count"] = failure_total
    out["status"] = df.get("status", "unknown")
    return out


def load_health_file(path: Path, normalizer) -> pd.DataFrame:
    if not path.exists():
        print(f"[warn] Missing health file: {path}")
        return normalizer(pd.DataFrame())

    df = pd.read_parquet(path)
    return normalizer(df)


def main() -> None:
    now_utc = datetime.now(timezone.utc)

    catalog_df = load_health_file(CATALOG_HEALTH_PATH, normalize_catalog_health)
    trends_df = load_health_file(TRENDS_HEALTH_PATH, normalize_trends_health)

    combined = pd.concat([catalog_df, trends_df], ignore_index=True)

    if combined.empty:
        combined = pd.DataFrame(
            columns=[
                "source_name",
                "captured_at",
                "row_count",
                "success_count",
                "failure_count",
                "status",
                "is_stale",
                "stale_reason",
            ]
        )
    else:
        combined["captured_at"] = combined["captured_at"].astype(str)

        stale_flags = []
        stale_reasons = []

        for _, row in combined.iterrows():
            source_name = str(row.get("source_name", "")).strip()
            captured_at = parse_dt(row.get("captured_at"))
            is_stale, stale_reason = compute_staleness(source_name, captured_at, now_utc)
            stale_flags.append(is_stale)
            stale_reasons.append(stale_reason)

        combined["is_stale"] = stale_flags
        combined["stale_reason"] = stale_reasons

    MONITORING_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(OUTPUT_PARQUET, index=False)
    combined.to_csv(OUTPUT_CSV, index=False)

    print(f"[saved] {OUTPUT_PARQUET}")
    print(f"[saved] {OUTPUT_CSV}")
    print(combined.to_string(index=False))


if __name__ == "__main__":
    main()