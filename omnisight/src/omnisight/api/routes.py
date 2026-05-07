from __future__ import annotations

from pathlib import Path
import os
from openai import OpenAI
from datetime import datetime, timezone

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from qdrant_client import QdrantClient

from omnisight.api.schemas import (
    CategorySummaryItem,
    CategorySummaryResponse,
    ConfidenceBucketItem,
    ConfidenceBucketResponse,
    DashboardStatsResponse,
    DecisionEventItem,
    DecisionEventListResponse,
    DecisionResponse,
    DecisionVolumeItem,
    DecisionVolumeResponse,
    FreshnessItem,
    FreshnessListResponse,
    HealthResponse,
    JobRunItem,
    JobRunListResponse,
    JobTriggerResponse,
    MonitoringProductItem,
    MonitoringProductListResponse,
    MonitoringSummaryResponse,
    OverrideBreakdownItem,
    OverrideBreakdownResponse,
    ProductAnalysisResponse,
    QueueItem,
    QueueResponse,
    ReviewActionRequest,
    ReviewActionResponse,
    ReviewHistoryResponse,
    ReviewQueueItem,
    ReviewQueueResponse,
    ReviewStatsResponse,
    SchedulerJobItem,
    SchedulerStatusResponse,
    SourceHealthItem,
    SourceHealthResponse,
    SystemStatusResponse,
    Top5ProductItem,
    Top5ProductListResponse,
    AssistantChatRequest,
    AssistantChatResponse,
    AlertItem,
    AlertListResponse,
    AlertSummaryResponse,
)
from omnisight.api.security import require_internal_token
from omnisight.db.job_store import init_job_db, list_freshness, list_job_runs
from omnisight.db.monitor_store import (
    confidence_distribution,
    decisions_over_time,
    init_monitor_db,
    list_recent_decision_events,
    log_decision_event,
    monitoring_summary,
    override_breakdown,
)
from omnisight.db.review_store import (
    create_review,
    init_review_db,
    list_reviews,
    list_reviews_for_product,
    review_stats,
)
from omnisight.graph.build_graph import build_omnisight_graph
from omnisight.jobs.refresh_jobs import (
    run_all_refresh_jobs,
    run_refresh_recommendations,
    run_refresh_reviews,
    run_refresh_trends,
)
from omnisight.jobs.scheduler_runtime import (
    pause_job,
    resume_job,
    run_job_now,
    scheduler_snapshot,
)
from omnisight.settings import settings

router = APIRouter()

_graph = None
PROJECT_ROOT = Path(__file__).resolve().parents[3]

MERGED_DIR = PROJECT_ROOT / "data" / "processed" / "merged"
MONITORING_DIR = PROJECT_ROOT / "data" / "processed" / "monitoring"
APP_DIR = PROJECT_ROOT / "data" / "app"

DECISION_FEATURES_PATH = MERGED_DIR / "decision_features.parquet"

LIVE_TRENDS_DIR = PROJECT_ROOT / "data" / "raw" / "live" / "trends"
LIVE_TRENDS_PATH = LIVE_TRENDS_DIR / "live_trends_latest.parquet"
LIVE_RELATED_QUERIES_PATH = LIVE_TRENDS_DIR / "live_related_queries_latest.parquet"

RECOMMENDATIONS_PATH = MERGED_DIR / "recommendations.parquet"
DASHBOARD_TOP5_PATH = MERGED_DIR / "dashboard_top5.parquet"
MONITORING_PRODUCTS_PATH = MERGED_DIR / "monitoring_products.parquet"
SOURCE_HEALTH_PATH = MONITORING_DIR / "source_health.parquet"

APP_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_PATH = APP_DIR / "review_export.csv"

init_review_db()
init_monitor_db()
init_job_db()


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_omnisight_graph()
    return _graph


def _read_parquet(path: Path, empty_columns: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=empty_columns or [])
    return pd.read_parquet(path).copy()


def load_analysis_df() -> pd.DataFrame:
    df = _read_parquet(RECOMMENDATIONS_PATH)
    if df.empty:
        raise FileNotFoundError(f"recommendations.parquet not found at {RECOMMENDATIONS_PATH}")
    if "product_id" in df.columns:
        df["product_id"] = df["product_id"].astype(str)
    return df


def load_dashboard_df() -> pd.DataFrame:
    df = _read_parquet(DASHBOARD_TOP5_PATH)
    if "product_id" in df.columns:
        df["product_id"] = df["product_id"].astype(str)
    return df


def load_monitoring_df() -> pd.DataFrame:
    df = _read_parquet(MONITORING_PRODUCTS_PATH)
    if "product_id" in df.columns:
        df["product_id"] = df["product_id"].astype(str)
    return df


def load_source_health_df() -> pd.DataFrame:
    return _read_parquet(
        SOURCE_HEALTH_PATH,
        empty_columns=[
            "source_name",
            "captured_at",
            "row_count",
            "success_count",
            "failure_count",
            "status",
            "is_stale",
            "stale_reason",
        ],
    )


def safe_float(value, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def compute_days_to_stockout(row: pd.Series) -> float:
    qty = safe_float(row.get("current_quantity", 0.0), 0.0)
    weekly = safe_float(row.get("projected_weekly_demand", 0.0), 0.0)
    if weekly <= 0:
        return 999.0
    return round((qty / weekly) * 7.0, 2)


def infer_legacy_action(row: pd.Series) -> str:
    stock_flag = str(row.get("stock_flag", "") or "")
    trend_classification = str(row.get("trend_classification", "") or "")
    current_quantity = safe_float(row.get("current_quantity", 0.0), 0.0)
    threshold_units = safe_float(row.get("threshold_units", 0.0), 0.0)
    recommended_order_qty = safe_float(row.get("recommended_order_qty", 0.0), 0.0)
    manual_review_required = bool(row.get("manual_review_required", False))
    projected_weekly_demand = safe_float(row.get("projected_weekly_demand", 0.0), 0.0)

    ratio = current_quantity / max(threshold_units, 1.0)
    weeks_cover = current_quantity / max(projected_weekly_demand, 1.0)

    if manual_review_required and recommended_order_qty > 0:
        return "CHECK_QUALITY_BEFORE_RESTOCK"

    if stock_flag == "CRITICAL":
        return "RESTOCK_NOW"

    if stock_flag == "LOW STOCK":
        return "RESTOCK_CAUTIOUSLY"

    if stock_flag == "OVERSTOCK":
        if ratio >= 1.75 or weeks_cover >= 10.0:
            return "HOLD"
        return "SLOW_REPLENISHMENT"

    if trend_classification == "Trending Up" and weeks_cover <= 3.0:
        return "RESTOCK_CAUTIOUSLY"

    return "MONITOR"


def infer_legacy_confidence(row: pd.Series) -> float:
    return round(safe_float(row.get("confidence_pct", 0.0), 0.0) / 100.0, 2)


def infer_stockout_risk(row: pd.Series) -> float:
    stock_flag = str(row.get("stock_flag", "") or "")
    if stock_flag == "CRITICAL":
        return 0.90
    if stock_flag == "LOW STOCK":
        return 0.65
    return 0.25


def infer_overstock_risk(row: pd.Series) -> float:
    trend_classification = str(row.get("trend_classification", "") or "")
    current_quantity = safe_float(row.get("current_quantity", 0.0), 0.0)
    threshold_units = safe_float(row.get("threshold_units", 1.0), 1.0)
    ratio = current_quantity / max(threshold_units, 1.0)

    if trend_classification == "Trending Down" and ratio >= 1.5:
        return 0.85
    if trend_classification == "Trending Down" and ratio >= 1.2:
        return 0.70
    if ratio >= 1.2:
        return 0.50
    return 0.20


def infer_trend_strength(row: pd.Series) -> float:
    trend_classification = str(row.get("trend_classification", "") or "")
    if trend_classification == "Trending Up":
        return 0.80
    if trend_classification == "Trending Down":
        return 0.20
    return 0.50

def build_alert_rows() -> list[dict]:
    alerts: list[dict] = []

    try:
        analysis_df = load_analysis_df()
    except Exception:
        analysis_df = pd.DataFrame()

    try:
        source_df = load_source_health_df()
    except Exception:
        source_df = pd.DataFrame()

    if not analysis_df.empty:
        for _, row in analysis_df.iterrows():
            product_id = str(row.get("product_id", "") or "")
            title = str(row.get("title", "") or "").strip()
            category_slug = str(row.get("category_slug", "") or "")
            stock_flag = str(row.get("stock_flag", "") or "")
            trend_classification = str(row.get("trend_classification", "") or "")
            confidence_pct = safe_float(row.get("confidence_pct", 0.0), 0.0)
            manual_review_required = bool(row.get("manual_review_required", False))
            current_quantity = safe_float(row.get("current_quantity", 0.0), 0.0)
            threshold_units = safe_float(row.get("threshold_units", 0.0), 0.0)
            recommended_order_qty = safe_float(row.get("recommended_order_qty", 0.0), 0.0)

            if stock_flag == "CRITICAL":
                alerts.append(
                    {
                        "alert_id": f"critical-stock-{product_id}",
                        "severity": "critical",
                        "alert_type": "critical_stock",
                        "title": f"Critical stock: {title}",
                        "message": (
                            f"{title} is in CRITICAL stock status. "
                            f"Current quantity is {current_quantity:.0f} against a threshold of {threshold_units:.0f}."
                        ),
                        "product_id": product_id,
                        "category_slug": category_slug,
                        "source_name": "",
                        "created_from": "analysis",
                        "metric_value": current_quantity,
                    }
                )

            elif stock_flag == "LOW STOCK":
                alerts.append(
                    {
                        "alert_id": f"low-stock-{product_id}",
                        "severity": "warning",
                        "alert_type": "low_stock",
                        "title": f"Low stock: {title}",
                        "message": (
                            f"{title} is below threshold and may need replenishment soon. "
                            f"Recommended order quantity is {recommended_order_qty:.0f}."
                        ),
                        "product_id": product_id,
                        "category_slug": category_slug,
                        "source_name": "",
                        "created_from": "analysis",
                        "metric_value": recommended_order_qty,
                    }
                )

            if stock_flag == "OVERSTOCK":
                alerts.append(
                    {
                        "alert_id": f"overstock-{product_id}",
                        "severity": "warning",
                        "alert_type": "overstock",
                        "title": f"Overstock risk: {title}",
                        "message": (
                            f"{title} is overstocked relative to threshold. "
                            f"Current quantity is {current_quantity:.0f} vs threshold {threshold_units:.0f}."
                        ),
                        "product_id": product_id,
                        "category_slug": category_slug,
                        "source_name": "",
                        "created_from": "analysis",
                        "metric_value": current_quantity - threshold_units,
                    }
                )

            if trend_classification == "Trending Down" and stock_flag in {"OVERSTOCK", "SUFFICIENT"}:
                alerts.append(
                    {
                        "alert_id": f"trend-drop-{product_id}",
                        "severity": "warning",
                        "alert_type": "trend_drop",
                        "title": f"Trend drop: {title}",
                        "message": (
                            f"{title} is trending down. Inventory should be watched closely to avoid excess stock."
                        ),
                        "product_id": product_id,
                        "category_slug": category_slug,
                        "source_name": "",
                        "created_from": "analysis",
                        "metric_value": 0.0,
                    }
                )

            if manual_review_required or confidence_pct < 60:
                alerts.append(
                    {
                        "alert_id": f"low-confidence-{product_id}",
                        "severity": "info" if confidence_pct >= 50 else "warning",
                        "alert_type": "low_confidence",
                        "title": f"Low-confidence recommendation: {title}",
                        "message": (
                            f"{title} has a recommendation confidence of {confidence_pct:.0f}%. "
                            f"A human review may be useful before acting."
                        ),
                        "product_id": product_id,
                        "category_slug": category_slug,
                        "source_name": "",
                        "created_from": "analysis",
                        "metric_value": confidence_pct,
                    }
                )

    if not source_df.empty:
        for _, row in source_df.iterrows():
            source_name = str(row.get("source_name", "") or "")
            status = str(row.get("status", "") or "").lower()
            is_stale = bool(row.get("is_stale", False))
            stale_reason = str(row.get("stale_reason", "") or "").strip()
            row_count = int(safe_float(row.get("row_count", 0), 0))

            if is_stale:
                alerts.append(
                    {
                        "alert_id": f"stale-source-{source_name}",
                        "severity": "critical",
                        "alert_type": "stale_source",
                        "title": f"Stale source: {source_name}",
                        "message": stale_reason or f"{source_name} is stale and may be impacting freshness.",
                        "product_id": "",
                        "category_slug": "",
                        "source_name": source_name,
                        "created_from": "source_health",
                        "metric_value": float(row_count),
                    }
                )

            elif status == "empty":
                alerts.append(
                    {
                        "alert_id": f"empty-source-{source_name}",
                        "severity": "warning",
                        "alert_type": "empty_source",
                        "title": f"Empty source: {source_name}",
                        "message": f"{source_name} returned no usable rows in the latest refresh.",
                        "product_id": "",
                        "category_slug": "",
                        "source_name": source_name,
                        "created_from": "source_health",
                        "metric_value": float(row_count),
                    }
                )

    severity_order = {"critical": 3, "warning": 2, "info": 1}
    alerts = sorted(
        alerts,
        key=lambda x: (
            severity_order.get(str(x.get("severity", "info")), 0),
            safe_float(x.get("metric_value", 0.0), 0.0),
        ),
        reverse=True,
    )

    return alerts


def build_alert_summary(alerts: list[dict]) -> dict:
    critical_count = sum(1 for a in alerts if a.get("severity") == "critical")
    warning_count = sum(1 for a in alerts if a.get("severity") == "warning")
    info_count = sum(1 for a in alerts if a.get("severity") == "info")

    return {
        "total_alerts": len(alerts),
        "critical_count": critical_count,
        "warning_count": warning_count,
        "info_count": info_count,
    }


def make_chat_client() -> OpenAI:
    base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1").strip()
    api_key = os.getenv("LLM_API_KEY", "ollama").strip() or "ollama"
    return OpenAI(base_url=base_url, api_key=api_key)


def get_chat_model_name() -> str:
    return os.getenv("LLM_MODEL", "gemma3:12b").strip()


def summarize_grounded_context(
    df: pd.DataFrame,
    page_context: str,
    product_id: str = "",
) -> dict:
    work = df.copy()

    referenced_product_ids: list[str] = []

    if product_id:
        selected = work[work["product_id"].astype(str) == str(product_id)].copy()
        if not selected.empty:
            referenced_product_ids = selected["product_id"].astype(str).head(5).tolist()
            return {
                "scope": "product_detail",
                "rows": selected.head(1).to_dict(orient="records"),
                "referenced_product_ids": referenced_product_ids,
            }

    if page_context == "monitoring":
        work = work[work["destination_view"].astype(str) == "monitoring"].copy()

    if "urgency_rank_score" in work.columns:
        work = work.sort_values(by="urgency_rank_score", ascending=False)

    top_rows = work.head(15).copy()
    referenced_product_ids = top_rows["product_id"].astype(str).head(10).tolist()

    summary = {
        "total_products": int(len(work)),
        "stock_flag_counts": work["stock_flag"].astype(str).value_counts(dropna=False).to_dict()
        if "stock_flag" in work.columns else {},
        "trend_counts": work["trend_classification"].astype(str).value_counts(dropna=False).to_dict()
        if "trend_classification" in work.columns else {},
        "category_counts": work["category_slug"].astype(str).value_counts(dropna=False).to_dict()
        if "category_slug" in work.columns else {},
        "sample_rows": top_rows[
            [
                c for c in [
                    "product_id",
                    "title",
                    "category_slug",
                    "category_label",
                    "stock_flag",
                    "trend_classification",
                    "current_quantity",
                    "threshold_units",
                    "projected_weekly_demand",
                    "recommended_order_qty",
                    "confidence_pct",
                    "destination_view",
                    "executive_summary",
                ]
                if c in top_rows.columns
            ]
        ].to_dict(orient="records"),
    }

    return {
        "scope": page_context or "global",
        "summary": summary,
        "referenced_product_ids": referenced_product_ids,
    }


def _format_recency_line(recency_days: int | None) -> str:
    if recency_days is None:
        return "Here’s what’s trending right now (trend data recency is unavailable)."

    if recency_days > 7:
        return (
            f"Here’s what’s trending right now. Trend data is {recency_days} days old, "
            f"so it may not reflect what is happening at this exact moment."
        )

    if recency_days == 0:
        return "Here’s what’s trending right now (data is current as of today)."

    if recency_days == 1:
        return "Here’s what’s trending right now (data is current as of 1 day ago)."

    return f"Here’s what’s trending right now (data is current as of {recency_days} days ago)."


def render_trending_now_answer(context: dict) -> str:
    products = context.get("products", []) or []
    recency_days = context.get("recency_days", None)

    intro = _format_recency_line(recency_days)

    if not products:
        return (
            f"{intro}\n\n"
            "I do not see any products clearly classified as Trending Up in the latest grounded data.\n\n"
            "Would you like the full analysis for any specific product?"
        )

    lines = [intro, ""]
    for i, product in enumerate(products, start=1):
        title = str(product.get("title", "")).strip() or f"Product {i}"
        trend_classification = str(product.get("trend_classification", "Stable")).strip()
        keywords = product.get("keywords", []) or []
        keywords_text = ", ".join([str(k).strip() for k in keywords[:3] if str(k).strip()])
        if not keywords_text:
            keywords_text = "no strong keyword signal available"

        review_reason = str(product.get("review_reason", "")).strip()
        if not review_reason:
            review_reason = "Recent review behavior supports current momentum."

        lines.append(
            f"{i}. **{title}** - {trend_classification} - Keywords: {keywords_text} - {review_reason}"
        )

    lines.append("")
    lines.append("Would you like the full analysis for any of these products?")
    return "\n".join(lines)


def render_trending_next_answer(context: dict) -> str:
    candidates = context.get("candidates", []) or []

    intro = (
        "Here are the products that look most likely to trend next based on early signals in the data. "
        "These are directional predictions, not certainties."
    )

    if not candidates:
        return (
            f"{intro}\n\n"
            "I do not currently see enough aligned early signals to flag a strong next-wave candidate.\n\n"
            "Want me to monitor these closely and alert you when the signal strengthens?"
        )

    lines = [intro, ""]
    for i, product in enumerate(candidates, start=1):
        title = str(product.get("title", "")).strip() or f"Product {i}"
        confidence = str(product.get("confidence", "speculative")).strip().title()
        early_signals = product.get("early_signals", []) or []
        signals_text = "; ".join([str(s).strip() for s in early_signals if str(s).strip()])
        if not signals_text:
            signals_text = "Early signals are present but still thin."

        watch_signal = str(product.get("watch_signal", "")).strip()
        if not watch_signal:
            watch_signal = "Watch whether demand strengthens over the next few weeks."

        lines.append(
            f"{i}. **{title}** - {confidence} Confidence - Signals: {signals_text} - "
            f"Confidence: {confidence} - Watch Signal: {watch_signal}"
        )

    lines.append("")
    lines.append("Want me to monitor these closely and alert you when the signal strengthens?")
    return "\n".join(lines)


def build_general_chat_answer(
    user_message: str,
    grounded_context: dict,
) -> str:
    client = make_chat_client()
    model = get_chat_model_name()

    system_prompt = """
You are OmniSight Assistant, a grounded inventory analysis copilot.

Rules:
- Answer only from the provided grounded context.
- Do not invent products, counts, categories, or metrics.
- Keep the answer concise and easy to scan.
- Prefer short paragraphs or short bullet-like lines.
- End with exactly one follow-up suggestion.
"""

    user_prompt = f"""
User question:
{user_message}

Grounded context:
{grounded_context}

Return plain text only.
"""

    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return (response.choices[0].message.content or "").strip()

def build_chat_answer(
    user_message: str,
    intent: str,
    grounded_context: dict,
) -> str:
    if intent == "trending_now":
        return render_trending_now_answer(grounded_context)

    if intent == "trending_next":
        return render_trending_next_answer(grounded_context)

    return build_general_chat_answer(
        user_message=user_message,
        grounded_context=grounded_context,
    )

def load_decision_features_df() -> pd.DataFrame:
    df = _read_parquet(DECISION_FEATURES_PATH)
    if "product_id" in df.columns:
        df["product_id"] = df["product_id"].astype(str)
    return df


def load_live_trends_df() -> pd.DataFrame:
    df = _read_parquet(LIVE_TRENDS_PATH)
    if "product_id" in df.columns:
        df["product_id"] = df["product_id"].astype(str)
    return df


def load_related_queries_df() -> pd.DataFrame:
    return _read_parquet(LIVE_RELATED_QUERIES_PATH)

def detect_chat_intent(message: str) -> str:
    text = (message or "").strip().lower()

    trending_now_terms = [
        "trending right now",
        "what is trending right now",
        "what's trending right now",
        "most popular",
        "top trending",
        "latest trending",
        "currently trending",
        "what is trending",
        "what's trending",
    ]

    trending_next_terms = [
        "what will trend",
        "what will be trending",
        "trend next",
        "about to take off",
        "watch out for",
        "what should i watch",
        "likely to trend",
        "what do you think will trend next",
    ]

    if any(term in text for term in trending_now_terms):
        return "trending_now"

    if any(term in text for term in trending_next_terms):
        return "trending_next"

    return "general"

def parse_captured_at(value) -> datetime | None:
    if value is None:
        return None

    try:
        # epoch seconds
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except Exception:
        pass

    try:
        # string epoch
        if isinstance(value, str) and value.strip().isdigit():
            return datetime.fromtimestamp(float(value.strip()), tz=timezone.utc)
    except Exception:
        pass

    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def get_latest_trend_recency_days(live_trends_df: pd.DataFrame) -> int | None:
    if live_trends_df.empty or "captured_at" not in live_trends_df.columns:
        return None

    timestamps = [
        parse_captured_at(v)
        for v in live_trends_df["captured_at"].tolist()
    ]
    timestamps = [t for t in timestamps if t is not None]
    if not timestamps:
        return None

    latest = max(timestamps)
    now = datetime.now(timezone.utc)
    return max(0, (now - latest).days)

def get_product_trend_keywords(
    product_id: str,
    title: str,
    category_slug: str,
    live_trends_df: pd.DataFrame,
    related_df: pd.DataFrame,
) -> list[str]:
    keywords: list[str] = []

    seed_keywords = []
    if not live_trends_df.empty:
        matches = live_trends_df[live_trends_df["product_id"].astype(str) == str(product_id)]
        if "trend_keyword" in matches.columns and not matches.empty:
            seed_keywords = (
                matches["trend_keyword"]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
            )

    related_matches = pd.DataFrame()
    if not related_df.empty:
        if seed_keywords and "seed_keyword" in related_df.columns:
            related_matches = related_df[
                related_df["seed_keyword"].astype(str).isin(seed_keywords)
            ].copy()

        if related_matches.empty and "category_slug" in related_df.columns:
            related_matches = related_df[
                related_df["category_slug"].astype(str) == str(category_slug)
            ].copy()

    if not related_matches.empty and "related_query" in related_matches.columns:
        if "extracted_value" in related_matches.columns:
            related_matches["extracted_value"] = pd.to_numeric(
                related_matches["extracted_value"], errors="coerce"
            ).fillna(0)
            related_matches = related_matches.sort_values(
                by="extracted_value", ascending=False
            )

        for value in related_matches["related_query"].dropna().astype(str).tolist():
            value = value.strip()
            if value and value not in keywords:
                keywords.append(value)
            if len(keywords) >= 3:
                break

    if not keywords:
        title_words = [w.strip(",.- ") for w in str(title).split() if len(w.strip(",.- ")) > 3]
        keywords = title_words[:3]

    return keywords[:3]

def build_trending_now_context() -> dict:
    analysis_df = load_analysis_df()
    live_trends_df = load_live_trends_df()
    related_df = load_related_queries_df()

    recency_days = get_latest_trend_recency_days(live_trends_df)

    work = analysis_df.copy()
    if "trend_classification" in work.columns:
        work = work[work["trend_classification"].astype(str) == "Trending Up"].copy()

    if "confidence_pct" in work.columns:
        work = work.sort_values(by="confidence_pct", ascending=False)

    top_rows = work.head(5).copy()

    products = []
    for _, row in top_rows.iterrows():
        product_id = str(row.get("product_id", ""))
        title = str(row.get("title", ""))
        category_slug = str(row.get("category_slug", ""))

        keywords = get_product_trend_keywords(
            product_id=product_id,
            title=title,
            category_slug=category_slug,
            live_trends_df=live_trends_df,
            related_df=related_df,
        )

        review_reason = str(row.get("executive_summary", "")).strip()
        if not review_reason:
            review_reason = "Recent reviews suggest positive momentum around this product."

        products.append(
            {
                "product_id": product_id,
                "title": title,
                "trend_classification": str(row.get("trend_classification", "Stable")),
                "keywords": keywords,
                "review_reason": review_reason,
                "confidence_pct": safe_float(row.get("confidence_pct", 0.0)),
            }
        )

    return {
        "intent": "trending_now",
        "recency_days": recency_days,
        "products": products,
    }

def safe_list(value) -> list[float]:
    if value is None:
        return []
    if isinstance(value, list):
        return [safe_float(v) for v in value]
    if hasattr(value, "tolist"):
        raw = value.tolist()
        if isinstance(raw, list):
            return [safe_float(v) for v in raw]
        return [safe_float(raw)]
    return []


def build_trending_next_context() -> dict:
    analysis_df = load_analysis_df()
    features_df = load_decision_features_df()

    if features_df.empty:
        return {
            "intent": "trending_next",
            "candidates": [],
        }

    merged = features_df.merge(
        analysis_df[
            [
                c for c in [
                    "product_id",
                    "title",
                    "category_slug",
                    "trend_classification",
                    "confidence_pct",
                    "executive_summary",
                ]
                if c in analysis_df.columns
            ]
        ],
        on="product_id",
        how="left",
    )

    # count how many products per category are already trending up
    category_trending_up = {}
    if "category_slug" in merged.columns and "trend_classification" in merged.columns:
        tmp = merged[merged["trend_classification"].astype(str) == "Trending Up"]
        category_trending_up = (
            tmp["category_slug"].astype(str).value_counts(dropna=False).to_dict()
        )

    candidates = []

    for _, row in merged.iterrows():
        if str(row.get("trend_classification", "")) == "Trending Up":
            continue

        weekly_history = safe_list(row.get("weekly_sales_history"))
        trend_values = safe_list(row.get("trend_values"))

        recent_review_avg = safe_float(row.get("recent_review_avg", 0.0))
        older_review_avg = safe_float(row.get("older_review_avg", 0.0))
        review_delta = recent_review_avg - older_review_avg

        trend_recent = sum(trend_values[-4:]) / max(len(trend_values[-4:]), 1) if trend_values else 0.0
        trend_long = sum(trend_values[-12:]) / max(len(trend_values[-12:]), 1) if trend_values else 0.0
        trend_rising = trend_long > 0 and ((trend_recent - trend_long) / trend_long) >= 0.05

        sales_accel = False
        if len(weekly_history) >= 3:
            sales_accel = weekly_history[-1] > weekly_history[-2] > weekly_history[-3]

        review_improving = review_delta >= 0.15

        category_slug = str(row.get("category_slug", ""))
        spillover = category_trending_up.get(category_slug, 0) > 0

        signal_count = sum(
            [
                1 if trend_rising else 0,
                1 if review_improving else 0,
                1 if sales_accel else 0,
                1 if spillover else 0,
            ]
        )

        if signal_count < 2:
            continue

        if signal_count >= 4:
            confidence = "high"
        elif signal_count == 3:
            confidence = "moderate"
        else:
            confidence = "speculative"

        early_signals = []
        if trend_rising:
            early_signals.append("Google Trends searches are rising over the last few weeks")
        if review_improving:
            early_signals.append("review sentiment improved over the last 30 days")
        if sales_accel:
            early_signals.append("weekly sales velocity accelerated for at least two consecutive weeks")
        if spillover:
            early_signals.append("related products in the same category are already trending")

        if trend_rising:
            watch_signal = "Watch whether search interest keeps rising over the next 1–2 weeks."
        elif sales_accel:
            watch_signal = "Watch whether weekly sales continue accelerating next week."
        else:
            watch_signal = "Watch whether review volume starts to increase along with sentiment."

        candidates.append(
            {
                "product_id": str(row.get("product_id", "")),
                "title": str(row.get("title", "")),
                "confidence": confidence,
                "early_signals": early_signals,
                "watch_signal": watch_signal,
            }
        )

    # prioritize higher-signal items
    confidence_order = {"high": 3, "moderate": 2, "speculative": 1}
    candidates = sorted(
        candidates,
        key=lambda x: confidence_order.get(x["confidence"], 0),
        reverse=True,
    )[:5]

    return {
        "intent": "trending_next",
        "candidates": candidates,
    }


@router.get("/", tags=["system"])
async def root():
    return {"message": "OmniSight API is running"}


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="omnisight-api")


@router.get("/ready", tags=["system"])
async def ready():
    return {"status": "ready"}


# -----------------------------
# New analysis-driven endpoints
# -----------------------------

@router.get(
    "/dashboard/top5",
    response_model=Top5ProductListResponse,
    tags=["dashboard"],
    dependencies=[Depends(require_internal_token)],
)
async def get_dashboard_top5() -> Top5ProductListResponse:
    df = load_dashboard_df()

    items = [
        Top5ProductItem(
            product_id=str(row.get("product_id", "")),
            title=str(row.get("title", "")),
            category_slug=str(row.get("category_slug", "")),
            category_label=str(row.get("category_label", "")),
            stock_flag=str(row.get("stock_flag", "SUFFICIENT")),
            current_quantity=safe_float(row.get("current_quantity", 0.0)),
            trend_classification=str(row.get("trend_classification", "Stable")),
            recommended_order_qty=safe_float(row.get("recommended_order_qty", 0.0)),
            confidence_pct=safe_float(row.get("confidence_pct", 0.0)),
            executive_summary=str(row.get("executive_summary", "")),
        )
        for _, row in df.iterrows()
    ]
    return Top5ProductListResponse(items=items)


@router.get(
    "/monitoring/products",
    response_model=MonitoringProductListResponse,
    tags=["monitoring"],
    dependencies=[Depends(require_internal_token)],
)
async def get_monitoring_products(
    category_slug: str | None = Query(default=None),
    trend_classification: str | None = Query(default=None),
    stock_flag: str | None = Query(default=None),
    manual_review_required: bool | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
) -> MonitoringProductListResponse:
    df = load_monitoring_df()

    if category_slug:
        df = df[df["category_slug"].astype(str) == category_slug]

    if trend_classification:
        df = df[df["trend_classification"].astype(str) == trend_classification]

    if stock_flag:
        df = df[df["stock_flag"].astype(str) == stock_flag]

    if manual_review_required is not None:
        df = df[df["manual_review_required"].astype(bool) == manual_review_required]

    df = df.head(limit).copy()

    items = [
        MonitoringProductItem(
            product_id=str(row.get("product_id", "")),
            title=str(row.get("title", "")),
            category_slug=str(row.get("category_slug", "")),
            category_label=str(row.get("category_label", "")),
            stock_flag=str(row.get("stock_flag", "SUFFICIENT")),
            trend_classification=str(row.get("trend_classification", "Stable")),
            current_quantity=safe_float(row.get("current_quantity", 0.0)),
            threshold_units=safe_float(row.get("threshold_units", 0.0)),
            projected_weekly_demand=safe_float(row.get("projected_weekly_demand", 0.0)),
            recommended_order_qty=safe_float(row.get("recommended_order_qty", 0.0)),
            confidence_pct=safe_float(row.get("confidence_pct", 0.0)),
            manual_review_required=bool(row.get("manual_review_required", False)),
            destination_view=str(row.get("destination_view", "monitoring")),
            executive_summary=str(row.get("executive_summary", "")),
        )
        for _, row in df.iterrows()
    ]
    return MonitoringProductListResponse(items=items)


@router.get(
    "/products/{product_id}/analysis",
    response_model=ProductAnalysisResponse,
    tags=["products"],
    dependencies=[Depends(require_internal_token)],
)
async def get_product_analysis(product_id: str) -> ProductAnalysisResponse:
    df = load_analysis_df()
    match_df = df[df["product_id"].astype(str) == str(product_id)]

    if match_df.empty:
        raise HTTPException(status_code=404, detail=f"Product not found for product_id={product_id}")

    row = match_df.iloc[0]
    return ProductAnalysisResponse(
        product_id=str(row.get("product_id", "")),
        title=str(row.get("title", "")),
        category_slug=str(row.get("category_slug", "")),
        category_label=str(row.get("category_label", "")),
        trend_classification=str(row.get("trend_classification", "Stable")),
        trend_conflict=bool(row.get("trend_conflict", False)),
        trend_summary=str(row.get("trend_summary", "")),
        projected_weekly_demand=safe_float(row.get("projected_weekly_demand", 0.0)),
        threshold_units=safe_float(row.get("threshold_units", 0.0)),
        threshold_explanation=str(row.get("threshold_explanation", "")),
        current_quantity=safe_float(row.get("current_quantity", 0.0)),
        stock_flag=str(row.get("stock_flag", "SUFFICIENT")),
        units_short=safe_float(row.get("units_short", 0.0)),
        recommended_order_qty=safe_float(row.get("recommended_order_qty", 0.0)),
        order_recommendation=str(row.get("order_recommendation", "")),
        confidence_pct=safe_float(row.get("confidence_pct", 0.0)),
        confidence_notes=str(row.get("confidence_notes", "")),
        manual_review_required=bool(row.get("manual_review_required", False)),
        executive_summary=str(row.get("executive_summary", "")),
        urgency_rank_score=safe_float(row.get("urgency_rank_score", 0.0)),
        destination_view=str(row.get("destination_view", "monitoring")),
    )


@router.get(
    "/categories/summary",
    response_model=CategorySummaryResponse,
    tags=["products"],
    dependencies=[Depends(require_internal_token)],
)
async def get_categories_summary() -> CategorySummaryResponse:
    df = load_analysis_df()

    if df.empty:
        return CategorySummaryResponse(items=[])

    df = df.copy()
    df["category_slug"] = df["category_slug"].fillna("").astype(str).str.strip()
    df["category_label"] = df["category_label"].fillna("").astype(str).str.strip()

    rows = []
    for category_slug, group in df.groupby("category_slug", dropna=False):
        category_label = ""
        non_empty_labels = [x for x in group["category_label"].tolist() if str(x).strip()]
        if non_empty_labels:
            category_label = str(non_empty_labels[0]).strip()

        rows.append(
            CategorySummaryItem(
                category_slug=str(category_slug or ""),
                category_label=category_label,
                total_products=int(len(group)),
                dashboard_count=int((group["destination_view"] == "dashboard").sum()),
                monitoring_count=int((group["destination_view"] == "monitoring").sum()),
                critical_count=int((group["stock_flag"] == "CRITICAL").sum()),
                low_stock_count=int((group["stock_flag"] == "LOW STOCK").sum()),
                sufficient_count=int((group["stock_flag"] == "SUFFICIENT").sum()),
                trending_up_count=int((group["trend_classification"] == "Trending Up").sum()),
                trending_down_count=int((group["trend_classification"] == "Trending Down").sum()),
                stable_count=int((group["trend_classification"] == "Stable").sum()),
            )
        )

    rows = sorted(rows, key=lambda x: x.category_slug)
    return CategorySummaryResponse(items=rows)


# ------------------------------------
# Compatibility endpoints for old pages
# ------------------------------------

@router.get(
    "/dashboard/stats",
    response_model=DashboardStatsResponse,
    tags=["dashboard"],
    dependencies=[Depends(require_internal_token)],
)
async def dashboard_stats() -> DashboardStatsResponse:
    df = load_analysis_df()

    actions = df.apply(infer_legacy_action, axis=1)
    avg_conf = round(float(df["confidence_pct"].mean()) / 100.0, 2) if "confidence_pct" in df.columns else 0.0

    return DashboardStatsResponse(
        total_products=len(df),
        restock_now_count=int((actions == "RESTOCK_NOW").sum()),
        cautious_count=int((actions == "RESTOCK_CAUTIOUSLY").sum()),
        monitor_count=int((actions == "MONITOR").sum()),
        slow_replenishment_count=int((actions == "SLOW_REPLENISHMENT").sum()),
        hold_count=int((actions == "HOLD").sum()),
        avg_confidence=avg_conf,
    )


@router.get(
    "/products/queue",
    response_model=QueueResponse,
    tags=["products"],
    dependencies=[Depends(require_internal_token)],
)
async def get_queue(
    action: str | None = Query(default=None),
    search: str | None = Query(default=None),
    category_slug: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> QueueResponse:
    df = load_analysis_df()

    df["legacy_action"] = df.apply(infer_legacy_action, axis=1)
    df["legacy_confidence"] = df.apply(infer_legacy_confidence, axis=1)
    df["legacy_days_to_stockout"] = df.apply(compute_days_to_stockout, axis=1)
    df["legacy_stockout_risk_score"] = df.apply(infer_stockout_risk, axis=1)
    df["legacy_overstock_risk_score"] = df.apply(infer_overstock_risk, axis=1)
    df["legacy_trend_strength_score"] = df.apply(infer_trend_strength, axis=1)

    if action:
        df = df[df["legacy_action"] == action]

    if category_slug:
        df = df[df["category_slug"].astype(str) == category_slug]

    if search:
        s = search.strip().lower()
        df = df[
            df["product_id"].astype(str).str.lower().str.contains(s, na=False)
            | df["title"].astype(str).str.lower().str.contains(s, na=False)
        ]

    sort_cols = [c for c in ["dashboard_priority", "urgency_rank_score", "confidence_pct"] if c in df.columns]
    ascending = [False, False, False][: len(sort_cols)]
    if sort_cols:
        df = df.sort_values(by=sort_cols, ascending=ascending)

    df = df.head(limit).copy()

    items = []
    for _, row in df.iterrows():
        items.append(
            QueueItem(
                product_id=str(row.get("product_id", "")),
                title=str(row.get("title", "")),
                category=str(row.get("category_label", row.get("category_slug", ""))),
                current_inventory=safe_float(row.get("current_quantity", 0.0)),
                weekly_units_sold=safe_float(row.get("projected_weekly_demand", 0.0)),
                days_to_stockout=safe_float(row.get("legacy_days_to_stockout", 999.0)),
                stockout_risk_score=safe_float(row.get("legacy_stockout_risk_score", 0.0)),
                overstock_risk_score=safe_float(row.get("legacy_overstock_risk_score", 0.0)),
                review_risk_score=0.0,
                trend_strength_score=safe_float(row.get("legacy_trend_strength_score", 0.0)),
                action=str(row.get("legacy_action", "")),
                confidence=safe_float(row.get("legacy_confidence", 0.0)),
                evidence_summary=str(row.get("executive_summary", "")),
            )
        )

    return QueueResponse(items=items)


# -----------------------------
# Existing graph / LLM decision
# -----------------------------

@router.get(
    "/decision/{product_id}",
    response_model=DecisionResponse,
    tags=["decision"],
    dependencies=[Depends(require_internal_token)],
)
async def get_decision(product_id: str) -> DecisionResponse:
    graph = get_graph()

    config = {"configurable": {"thread_id": f"api-{product_id}"}}
    result = graph.invoke({"product_id": product_id}, config=config)

    final_response = result.get("final_response", {})

    if not final_response:
        raise HTTPException(status_code=500, detail="Graph returned no final_response.")

    if final_response.get("status") == "error":
        error_message = final_response.get("error", "Unknown error")
        if "Product not found" in error_message:
            raise HTTPException(status_code=404, detail=error_message)
        raise HTTPException(status_code=500, detail=error_message)

    try:
        log_decision_event(
            product_id=str(final_response.get("product_id", "")),
            title=str(final_response.get("title", "")),
            baseline_action=str(final_response.get("baseline_action", "")),
            baseline_confidence=float(final_response.get("baseline_confidence", 0) or 0),
            llm_final_action=str(final_response.get("llm_final_action", "")),
            llm_confidence=float(final_response.get("llm_confidence", 0) or 0),
        )
    except Exception:
        pass

    return DecisionResponse(**final_response)


# -----------------------------
# Review endpoints
# -----------------------------

@router.get(
    "/dashboard/review-stats",
    response_model=ReviewStatsResponse,
    tags=["dashboard"],
    dependencies=[Depends(require_internal_token)],
)
async def get_review_stats() -> ReviewStatsResponse:
    stats = review_stats()
    return ReviewStatsResponse(**stats)


@router.get(
    "/decision/{product_id}/history",
    response_model=ReviewHistoryResponse,
    tags=["decision"],
    dependencies=[Depends(require_internal_token)],
)
async def get_decision_history(product_id: str) -> ReviewHistoryResponse:
    rows = list_reviews_for_product(product_id)
    return ReviewHistoryResponse(items=[ReviewActionResponse(**row) for row in rows])


@router.post(
    "/decision/{product_id}/review",
    response_model=ReviewActionResponse,
    tags=["decision"],
    dependencies=[Depends(require_internal_token)],
)
async def review_decision(product_id: str, body: ReviewActionRequest) -> ReviewActionResponse:
    df = load_analysis_df()
    match_df = df[df["product_id"].astype(str) == str(product_id)]

    if match_df.empty:
        raise HTTPException(status_code=404, detail=f"Product not found for product_id={product_id}")

    row = match_df.iloc[0]
    baseline_action = infer_legacy_action(row)

    saved = create_review(
        product_id=str(product_id),
        baseline_action=baseline_action,
        llm_action="",
        reviewer_name=body.reviewer_name,
        review_action=body.review_action,
        notes=body.notes,
    )

    return ReviewActionResponse(**saved)


@router.get(
    "/reviews/queue",
    response_model=ReviewQueueResponse,
    tags=["reviews"],
    dependencies=[Depends(require_internal_token)],
)
async def get_reviews_queue(
    review_action: str | None = Query(default=None),
    reviewer_name: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
) -> ReviewQueueResponse:
    rows = list_reviews(
        review_action=review_action,
        reviewer_name=reviewer_name,
        limit=limit,
    )
    return ReviewQueueResponse(items=[ReviewQueueItem(**row) for row in rows])


@router.get(
    "/reviews/export",
    tags=["reviews"],
    dependencies=[Depends(require_internal_token)],
)
async def export_reviews_csv():
    rows = list_reviews(limit=5000)
    df = pd.DataFrame(rows)

    if df.empty:
        df = pd.DataFrame(
            columns=[
                "id",
                "product_id",
                "baseline_action",
                "llm_action",
                "reviewer_name",
                "review_action",
                "notes",
                "created_at",
            ]
        )

    df.to_csv(EXPORT_PATH, index=False)
    return FileResponse(
        path=EXPORT_PATH,
        filename="review_export.csv",
        media_type="text/csv",
    )


# -----------------------------
# System / monitoring / health
# -----------------------------

@router.get(
    "/system/status",
    response_model=SystemStatusResponse,
    tags=["system"],
    dependencies=[Depends(require_internal_token)],
)
async def system_status() -> SystemStatusResponse:
    api_status = "ok"

    try:
        qdrant = QdrantClient(url=settings.QDRANT_URL)
        qdrant.get_collections()
        qdrant_status = "ok"
    except Exception:
        qdrant_status = "error"

    recommendations_loaded = RECOMMENDATIONS_PATH.exists()
    total_recommendations = 0
    if recommendations_loaded:
        try:
            total_recommendations = len(pd.read_parquet(RECOMMENDATIONS_PATH))
        except Exception:
            recommendations_loaded = False
            total_recommendations = 0

    try:
        stats = review_stats()
        review_db_ready = True
        total_reviews = stats["total_reviews"]
    except Exception:
        review_db_ready = False
        total_reviews = 0

    return SystemStatusResponse(
        api_status=api_status,
        qdrant_status=qdrant_status,
        recommendations_loaded=recommendations_loaded,
        review_db_ready=review_db_ready,
        total_recommendations=total_recommendations,
        total_reviews=total_reviews,
    )


@router.get(
    "/monitoring/summary",
    response_model=MonitoringSummaryResponse,
    tags=["monitoring"],
    dependencies=[Depends(require_internal_token)],
)
async def get_monitoring_summary() -> MonitoringSummaryResponse:
    summary_data = monitoring_summary(review_stats)
    return MonitoringSummaryResponse(**summary_data)


@router.get(
    "/monitoring/source-health",
    response_model=SourceHealthResponse,
    tags=["monitoring"],
    dependencies=[Depends(require_internal_token)],
)
async def get_source_health() -> SourceHealthResponse:
    df = load_source_health_df()
    items = [
        SourceHealthItem(
            source_name=str(row.get("source_name", "")),
            captured_at=str(row.get("captured_at", "")),
            row_count=int(safe_float(row.get("row_count", 0), 0)),
            success_count=int(safe_float(row.get("success_count", 0), 0)),
            failure_count=int(safe_float(row.get("failure_count", 0), 0)),
            status=str(row.get("status", "")),
            is_stale=bool(row.get("is_stale", False)),
            stale_reason=str(row.get("stale_reason", "")),
        )
        for _, row in df.iterrows()
    ]
    return SourceHealthResponse(items=items)


@router.get(
    "/monitoring/recent-decisions",
    response_model=DecisionEventListResponse,
    tags=["monitoring"],
    dependencies=[Depends(require_internal_token)],
)
async def get_recent_decisions(limit: int = Query(default=100, ge=1, le=500)) -> DecisionEventListResponse:
    rows = list_recent_decision_events(limit=limit)
    return DecisionEventListResponse(items=[DecisionEventItem(**row) for row in rows])


@router.get(
    "/monitoring/confidence-distribution",
    response_model=ConfidenceBucketResponse,
    tags=["monitoring"],
    dependencies=[Depends(require_internal_token)],
)
async def get_confidence_distribution() -> ConfidenceBucketResponse:
    rows = confidence_distribution()
    return ConfidenceBucketResponse(items=[ConfidenceBucketItem(**row) for row in rows])


@router.get(
    "/monitoring/decisions-over-time",
    response_model=DecisionVolumeResponse,
    tags=["monitoring"],
    dependencies=[Depends(require_internal_token)],
)
async def get_decisions_over_time(days: int = Query(default=14, ge=1, le=90)) -> DecisionVolumeResponse:
    rows = decisions_over_time(days=days)
    return DecisionVolumeResponse(items=[DecisionVolumeItem(**row) for row in rows])


@router.get(
    "/monitoring/override-breakdown",
    response_model=OverrideBreakdownResponse,
    tags=["monitoring"],
    dependencies=[Depends(require_internal_token)],
)
async def get_override_breakdown() -> OverrideBreakdownResponse:
    rows = override_breakdown()
    return OverrideBreakdownResponse(items=[OverrideBreakdownItem(**row) for row in rows])

@router.get(
    "/alerts/list",
    response_model=AlertListResponse,
    tags=["alerts"],
    dependencies=[Depends(require_internal_token)],
)
async def get_alert_list(
    severity: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> AlertListResponse:
    alerts = build_alert_rows()

    if severity:
        alerts = [a for a in alerts if str(a.get("severity", "")) == severity]

    alerts = alerts[:limit]
    return AlertListResponse(items=[AlertItem(**a) for a in alerts])


@router.get(
    "/alerts/summary",
    response_model=AlertSummaryResponse,
    tags=["alerts"],
    dependencies=[Depends(require_internal_token)],
)
async def get_alert_summary() -> AlertSummaryResponse:
    alerts = build_alert_rows()
    return AlertSummaryResponse(**build_alert_summary(alerts))



# -----------------------------
# Jobs / scheduler
# -----------------------------

@router.get(
    "/jobs/runs",
    response_model=JobRunListResponse,
    tags=["jobs"],
    dependencies=[Depends(require_internal_token)],
)
async def get_job_runs(limit: int = Query(default=50, ge=1, le=500)) -> JobRunListResponse:
    rows = list_job_runs(limit=limit)
    return JobRunListResponse(items=[JobRunItem(**row) for row in rows])


@router.get(
    "/freshness/summary",
    response_model=FreshnessListResponse,
    tags=["jobs"],
    dependencies=[Depends(require_internal_token)],
)
async def get_freshness_summary() -> FreshnessListResponse:
    rows = list_freshness()
    return FreshnessListResponse(items=[FreshnessItem(**row) for row in rows])


@router.post(
    "/jobs/run/all",
    response_model=dict,
    tags=["jobs"],
    dependencies=[Depends(require_internal_token)],
)
async def trigger_all_jobs():
    return run_all_refresh_jobs()


@router.post(
    "/jobs/run/recommendations",
    response_model=JobTriggerResponse,
    tags=["jobs"],
    dependencies=[Depends(require_internal_token)],
)
async def trigger_recommendations_job() -> JobTriggerResponse:
    result = run_refresh_recommendations()
    return JobTriggerResponse(**result)


@router.post(
    "/jobs/run/reviews",
    response_model=JobTriggerResponse,
    tags=["jobs"],
    dependencies=[Depends(require_internal_token)],
)
async def trigger_reviews_job() -> JobTriggerResponse:
    result = run_refresh_reviews()
    return JobTriggerResponse(**result)


@router.post(
    "/jobs/run/trends",
    response_model=JobTriggerResponse,
    tags=["jobs"],
    dependencies=[Depends(require_internal_token)],
)
async def trigger_trends_job() -> JobTriggerResponse:
    result = run_refresh_trends()
    return JobTriggerResponse(**result)


@router.get(
    "/jobs/scheduler/status",
    response_model=SchedulerStatusResponse,
    tags=["jobs"],
    dependencies=[Depends(require_internal_token)],
)
async def get_scheduler_status() -> SchedulerStatusResponse:
    snapshot = scheduler_snapshot()
    return SchedulerStatusResponse(
        running=bool(snapshot["running"]),
        timezone=str(snapshot["timezone"]),
        jobs=[SchedulerJobItem(**job) for job in snapshot["jobs"]],
    )


@router.post(
    "/jobs/scheduler/run-now/{job_name}",
    response_model=JobTriggerResponse,
    tags=["jobs"],
    dependencies=[Depends(require_internal_token)],
)
async def trigger_scheduler_job_now(job_name: str) -> JobTriggerResponse:
    result = run_job_now(job_name)
    return JobTriggerResponse(**result)


@router.post(
    "/jobs/scheduler/pause/{job_name}",
    response_model=JobTriggerResponse,
    tags=["jobs"],
    dependencies=[Depends(require_internal_token)],
)
async def pause_scheduler_job(job_name: str) -> JobTriggerResponse:
    result = pause_job(job_name)
    return JobTriggerResponse(**result)


@router.post(
    "/jobs/scheduler/resume/{job_name}",
    response_model=JobTriggerResponse,
    tags=["jobs"],
    dependencies=[Depends(require_internal_token)],
)
async def resume_scheduler_job(job_name: str) -> JobTriggerResponse:
    result = resume_job(job_name)
    return JobTriggerResponse(**result)


# -----------------------------
# Chatbot
# ==============================

@router.post(
    "/assistant/chat",
    response_model=AssistantChatResponse,
    tags=["assistant"],
    dependencies=[Depends(require_internal_token)],
)
async def assistant_chat(body: AssistantChatRequest) -> AssistantChatResponse:
    intent = detect_chat_intent(body.message)

    if intent == "trending_now":
        grounded_context = build_trending_now_context()
        referenced_product_ids = [
            item.get("product_id", "") for item in grounded_context.get("products", [])
        ]
    elif intent == "trending_next":
        grounded_context = build_trending_next_context()
        referenced_product_ids = [
            item.get("product_id", "") for item in grounded_context.get("candidates", [])
        ]
    else:
        df = load_analysis_df()
        grounded_context = summarize_grounded_context(
            df=df,
            page_context=body.page_context,
            product_id=body.product_id,
        )
        referenced_product_ids = grounded_context.get("referenced_product_ids", [])

    try:
        answer = build_chat_answer(
            user_message=body.message,
            intent=intent,
            grounded_context=grounded_context,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assistant chat failed: {e}")

    if intent == "trending_now":
        suggestions = ["Would you like the full analysis for any of these products?"]
    elif intent == "trending_next":
        suggestions = ["Want me to monitor these closely and alert you when the signal strengthens?"]
    else:
        suggestions = ["Would you like me to break this down by category or product?"]

    return AssistantChatResponse(
        answer=answer,
        suggestions=suggestions,
        referenced_product_ids=referenced_product_ids[:10],
    )