from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


class SupportingEvidence(BaseModel):
    source: Literal["product", "review", "trend", "image", "rules"]
    summary: str


class DecisionResponse(BaseModel):
    status: Literal["ok", "error"]
    product_id: str
    title: str = ""
    baseline_action: str = ""
    baseline_confidence: float = 0.0
    llm_final_action: str = ""
    llm_confidence: float = 0.0
    reasoning_summary: str = ""
    key_risks: List[str] = []
    key_opportunities: List[str] = []
    caution_flags: List[str] = []
    follow_up_actions: List[str] = []
    supporting_evidence: List[SupportingEvidence] = []
    error: str = ""


class HealthResponse(BaseModel):
    status: str
    service: str


class QueueItem(BaseModel):
    product_id: str
    title: str
    category: str = ""
    current_inventory: float = 0.0
    weekly_units_sold: float = 0.0
    days_to_stockout: float = 0.0
    stockout_risk_score: float = 0.0
    overstock_risk_score: float = 0.0
    review_risk_score: float = 0.0
    trend_strength_score: float = 0.0
    action: str = ""
    confidence: float = 0.0
    evidence_summary: str = ""


class QueueResponse(BaseModel):
    items: List[QueueItem]


class DashboardStatsResponse(BaseModel):
    total_products: int
    restock_now_count: int
    cautious_count: int
    monitor_count: int
    slow_replenishment_count: int
    hold_count: int
    avg_confidence: float


class ReviewActionRequest(BaseModel):
    reviewer_name: str = Field(..., min_length=1)
    review_action: Literal["APPROVE", "REJECT", "DEFER"]
    notes: str = ""


class ReviewActionResponse(BaseModel):
    id: int
    product_id: str
    baseline_action: str = ""
    llm_action: str = ""
    reviewer_name: str
    review_action: Literal["APPROVE", "REJECT", "DEFER"]
    notes: str = ""
    created_at: str


class ReviewHistoryResponse(BaseModel):
    items: List[ReviewActionResponse]


class ReviewStatsResponse(BaseModel):
    total_reviews: int
    approved_count: int
    rejected_count: int
    deferred_count: int


class ReviewQueueItem(BaseModel):
    id: int
    product_id: str
    baseline_action: str = ""
    llm_action: str = ""
    reviewer_name: str
    review_action: Literal["APPROVE", "REJECT", "DEFER"]
    notes: str = ""
    created_at: str


class ReviewQueueResponse(BaseModel):
    items: List[ReviewQueueItem]


class SystemStatusResponse(BaseModel):
    api_status: str
    qdrant_status: str
    recommendations_loaded: bool
    review_db_ready: bool
    total_recommendations: int
    total_reviews: int


class MonitoringSummaryResponse(BaseModel):
    total_decisions: int
    baseline_llm_agree_count: int
    baseline_llm_agreement_rate: float
    avg_llm_confidence: float
    total_reviews: int
    override_rate: float
    approved_count: int
    rejected_count: int
    deferred_count: int
    restock_now_count: int
    cautious_count: int
    monitor_count: int
    hold_count: int
    slow_replenishment_count: int
    check_quality_count: int


class DecisionEventItem(BaseModel):
    id: int
    product_id: str
    title: str = ""
    baseline_action: str = ""
    baseline_confidence: float = 0.0
    llm_final_action: str = ""
    llm_confidence: float = 0.0
    created_at: str


class DecisionEventListResponse(BaseModel):
    items: List[DecisionEventItem]


class ConfidenceBucketItem(BaseModel):
    bucket: str
    count: int


class ConfidenceBucketResponse(BaseModel):
    items: List[ConfidenceBucketItem]


class DecisionVolumeItem(BaseModel):
    date: str
    decision_count: int
    review_count: int


class DecisionVolumeResponse(BaseModel):
    items: List[DecisionVolumeItem]


class OverrideBreakdownItem(BaseModel):
    baseline_action: str
    total_reviews: int
    approve_count: int
    reject_count: int
    defer_count: int
    override_rate: float


class OverrideBreakdownResponse(BaseModel):
    items: List[OverrideBreakdownItem]


class JobRunItem(BaseModel):
    id: int
    job_name: str
    status: str
    started_at: str
    finished_at: str = ""
    duration_seconds: float = 0.0
    message: str = ""


class JobRunListResponse(BaseModel):
    items: List[JobRunItem]


class FreshnessItem(BaseModel):
    id: int
    dataset_name: str
    last_refreshed_at: str
    freshness_status: str
    notes: str = ""


class FreshnessListResponse(BaseModel):
    items: List[FreshnessItem]


class JobTriggerResponse(BaseModel):
    status: str
    message: str


class SchedulerJobItem(BaseModel):
    job_id: str
    name: str
    next_run_time: str = ""
    trigger: str
    paused: bool


class SchedulerStatusResponse(BaseModel):
    running: bool
    timezone: str
    jobs: List[SchedulerJobItem]


# -----------------------------
# New analysis / dashboard APIs
# -----------------------------

class Top5ProductItem(BaseModel):
    product_id: str
    title: str
    category_slug: str = ""
    category_label: str = ""
    stock_flag: Literal["CRITICAL", "LOW STOCK", "SUFFICIENT", "OVERSTOCK"]
    current_quantity: float = 0.0
    trend_classification: Literal["Trending Up", "Trending Down", "Stable"]
    recommended_order_qty: float = 0.0
    confidence_pct: float = 0.0
    executive_summary: str = ""
    trend_keywords: List[str] = []
    trend_reasons: List[str] = []
    trend_reason_confidence: str = "not_applicable"


class Top5ProductListResponse(BaseModel):
    items: List[Top5ProductItem]


class MonitoringProductItem(BaseModel):
    product_id: str
    title: str
    category_slug: str = ""
    category_label: str = ""
    stock_flag: Literal["CRITICAL", "LOW STOCK", "SUFFICIENT", "OVERSTOCK"]
    trend_classification: Literal["Trending Up", "Trending Down", "Stable"]
    current_quantity: float = 0.0
    threshold_units: float = 0.0
    projected_weekly_demand: float = 0.0
    recommended_order_qty: float = 0.0
    confidence_pct: float = 0.0
    manual_review_required: bool = False
    destination_view: Literal["dashboard", "monitoring"] = "monitoring"
    executive_summary: str = ""


class MonitoringProductListResponse(BaseModel):
    items: List[MonitoringProductItem]


class ProductAnalysisResponse(BaseModel):
    product_id: str
    title: str
    category_slug: str = ""
    category_label: str = ""

    trend_classification: Literal["Trending Up", "Trending Down", "Stable"]
    trend_conflict: bool = False
    trend_summary: str = ""
    trend_keywords: List[str] = []
    trend_reasons: List[str] = []
    trend_reason_confidence: str = "not_applicable"

    projected_weekly_demand: float = 0.0
    threshold_units: float = 0.0
    threshold_explanation: str = ""

    current_quantity: float = 0.0
    stock_flag: Literal["CRITICAL", "LOW STOCK", "SUFFICIENT", "OVERSTOCK"]
    units_short: float = 0.0

    recommended_order_qty: float = 0.0
    order_recommendation: str = ""

    confidence_pct: float = 0.0
    confidence_notes: str = ""
    manual_review_required: bool = False

    executive_summary: str = ""

    urgency_rank_score: float = 0.0
    destination_view: Literal["dashboard", "monitoring"]


class CategorySummaryItem(BaseModel):
    category_slug: str
    category_label: str = ""
    total_products: int
    dashboard_count: int
    monitoring_count: int
    critical_count: int
    low_stock_count: int
    sufficient_count: int
    trending_up_count: int
    trending_down_count: int
    stable_count: int


class CategorySummaryResponse(BaseModel):
    items: List[CategorySummaryItem]


class SourceHealthItem(BaseModel):
    source_name: str
    captured_at: str = ""
    row_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    status: str = ""
    is_stale: bool = False
    stale_reason: str = ""


class SourceHealthResponse(BaseModel):
    items: List[SourceHealthItem]

class AssistantChatRequest(BaseModel):
    message: str
    page_context: str = "global"
    product_id: str = ""


class AssistantChatResponse(BaseModel):
    answer: str
    suggestions: List[str] = []
    referenced_product_ids: List[str] = []

class AlertItem(BaseModel):
    alert_id: str
    severity: Literal["critical", "warning", "info"]
    alert_type: str
    title: str
    message: str
    product_id: str = ""
    category_slug: str = ""
    source_name: str = ""
    created_from: str = ""
    metric_value: float = 0.0


class AlertListResponse(BaseModel):
    items: List[AlertItem]


class AlertSummaryResponse(BaseModel):
    total_alerts: int
    critical_count: int
    warning_count: int
    info_count: int