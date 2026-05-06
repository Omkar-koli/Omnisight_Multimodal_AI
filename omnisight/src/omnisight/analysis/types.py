from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


TrendClass = Literal["Trending Up", "Trending Down", "Stable"]
StockFlag = Literal["CRITICAL", "LOW STOCK", "SUFFICIENT"]
ViewName = Literal["dashboard", "monitoring"]


@dataclass
class ProductAnalysis:
    product_id: str
    title: str
    category_slug: str
    category_label: str

    trend_classification: TrendClass
    trend_conflict: bool
    trend_summary: str

    projected_weekly_demand: float
    threshold_units: float
    threshold_explanation: str

    current_quantity: float
    stock_flag: StockFlag
    units_short: float

    recommended_order_qty: float
    order_recommendation: str

    confidence_pct: float
    confidence_notes: str
    manual_review_required: bool

    executive_summary: str

    urgency_rank_score: float
    destination_view: ViewName