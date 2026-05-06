from __future__ import annotations

from typing import List, Literal
from pydantic import BaseModel, Field


DecisionAction = Literal[
    "RESTOCK_NOW",
    "RESTOCK_CAUTIOUSLY",
    "MONITOR",
    "SLOW_REPLENISHMENT",
    "CHECK_QUALITY_BEFORE_RESTOCK",
    "HOLD",
]


class EvidenceItem(BaseModel):
    source: Literal["product", "review", "trend", "image", "rules"]
    summary: str = Field(..., min_length=1)


class ReasoningOutput(BaseModel):
    product_id: str
    title: str
    final_action: DecisionAction
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning_summary: str = Field(..., min_length=1)
    key_risks: List[str] = Field(default_factory=list)
    key_opportunities: List[str] = Field(default_factory=list)
    supporting_evidence: List[EvidenceItem] = Field(default_factory=list)
    caution_flags: List[str] = Field(default_factory=list)
    follow_up_actions: List[str] = Field(default_factory=list)