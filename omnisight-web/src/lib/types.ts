export type SupportingEvidence = {
  source: "product" | "review" | "trend" | "image" | "rules";
  summary: string;
};

export type DecisionResponse = {
  status: "ok" | "error";
  product_id: string;
  title: string;
  baseline_action: string;
  baseline_confidence: number;
  llm_final_action: string;
  llm_confidence: number;
  reasoning_summary: string;
  key_risks: string[];
  key_opportunities: string[];
  caution_flags: string[];
  follow_up_actions: string[];
  supporting_evidence: SupportingEvidence[];
  error?: string;
};

export type PreviewRow = {
  product_id: string;
  title: string;
  action?: string;
  confidence?: number;
};

export type QueueItem = {
  product_id: string;
  title: string;
  category: string;
  current_inventory: number;
  weekly_units_sold: number;
  days_to_stockout: number;
  stockout_risk_score: number;
  overstock_risk_score: number;
  review_risk_score: number;
  trend_strength_score: number;
  action: string;
  confidence: number;
  evidence_summary: string;
};

export type QueueResponse = {
  items: QueueItem[];
};

export type DashboardStatsResponse = {
  total_products: number;
  restock_now_count: number;
  cautious_count: number;
  monitor_count: number;
  slow_replenishment_count: number;
  hold_count: number;
  avg_confidence: number;
};

export type ReviewAction = "APPROVE" | "REJECT" | "DEFER";

export type ReviewActionRequest = {
  reviewer_name: string;
  review_action: ReviewAction;
  notes: string;
};

export type ReviewActionResponse = {
  id: number;
  product_id: string;
  baseline_action: string;
  llm_action: string;
  reviewer_name: string;
  review_action: ReviewAction;
  notes: string;
  created_at: string;
};

export type ReviewHistoryResponse = {
  items: ReviewActionResponse[];
};

export type ReviewStatsResponse = {
  total_reviews: number;
  approved_count: number;
  rejected_count: number;
  deferred_count: number;
};

export type ReviewQueueItem = {
  id: number;
  product_id: string;
  baseline_action: string;
  llm_action: string;
  reviewer_name: string;
  review_action: "APPROVE" | "REJECT" | "DEFER";
  notes: string;
  created_at: string;
};

export type ReviewQueueResponse = {
  items: ReviewQueueItem[];
};

export type SystemStatusResponse = {
  api_status: string;
  qdrant_status: string;
  recommendations_loaded: boolean;
  review_db_ready: boolean;
  total_recommendations: number;
  total_reviews: number;
};

export type MonitoringSummaryResponse = {
  total_decisions: number;
  baseline_llm_agree_count: number;
  baseline_llm_agreement_rate: number;
  avg_llm_confidence: number;
  override_rate: number;
  approved_count: number;
  rejected_count: number;
  deferred_count: number;
  restock_now_count: number;
  cautious_count: number;
  monitor_count: number;
  hold_count: number;
  slow_replenishment_count: number;
  check_quality_count: number;
};

export type DecisionEventItem = {
  id: number;
  product_id: string;
  title: string;
  baseline_action: string;
  baseline_confidence: number;
  llm_final_action: string;
  llm_confidence: number;
  created_at: string;
};

export type DecisionEventListResponse = {
  items: DecisionEventItem[];
};

export type JobRunItem = {
  id: number;
  job_name: string;
  status: string;
  started_at: string;
  finished_at: string;
  duration_seconds: number;
  message: string;
};

export type JobRunListResponse = {
  items: JobRunItem[];
};

export type FreshnessItem = {
  id: number;
  dataset_name: string;
  last_refreshed_at: string;
  freshness_status: string;
  notes: string;
};

export type FreshnessListResponse = {
  items: FreshnessItem[];
};

export type JobTriggerResponse = {
  status: string;
  message: string;
};

export type SchedulerJobItem = {
  job_id: string;
  name: string;
  next_run_time: string;
  trigger: string;
  paused: boolean;
};

export type SchedulerStatusResponse = {
  running: boolean;
  timezone: string;
  jobs: SchedulerJobItem[];
};

export type Top5ProductItem = {
  product_id: string;
  title: string;
  category_slug?: string;
  category_label?: string;
  stock_flag: "CRITICAL" | "LOW STOCK" | "SUFFICIENT" | "OVERSTOCK";
  current_quantity?: number;
  trend_classification: "Trending Up" | "Trending Down" | "Stable";
  recommended_order_qty?: number;
  confidence_pct?: number;
  executive_summary?: string;
};

export type Top5ProductListResponse = {
  items: Top5ProductItem[];
};

export type MonitoringProductItem = {
  product_id: string;
  title: string;
  category_slug?: string;
  category_label?: string;
  stock_flag: "CRITICAL" | "LOW STOCK" | "SUFFICIENT" | "OVERSTOCK";
  trend_classification: "Trending Up" | "Trending Down" | "Stable";
  current_quantity?: number;
  threshold_units?: number;
  projected_weekly_demand?: number;
  recommended_order_qty?: number;
  confidence_pct?: number;
  manual_review_required?: boolean;
  destination_view?: "dashboard" | "monitoring";
  executive_summary?: string;
};

export type MonitoringProductListResponse = {
  items: MonitoringProductItem[];
};

export type ProductAnalysisResponse = {
  product_id: string;
  title: string;
  category_slug?: string;
  category_label?: string;

  trend_classification: "Trending Up" | "Trending Down" | "Stable";
  trend_conflict?: boolean;
  trend_summary?: string;

  projected_weekly_demand?: number;
  threshold_units?: number;
  threshold_explanation?: string;

  current_quantity?: number;
  stock_flag: "CRITICAL" | "LOW STOCK" | "SUFFICIENT" | "OVERSTOCK";
  units_short?: number;

  recommended_order_qty?: number;
  order_recommendation?: string;

  confidence_pct?: number;
  confidence_notes?: string;
  manual_review_required?: boolean;

  executive_summary?: string;

  urgency_rank_score?: number;
  destination_view?: "dashboard" | "monitoring";
};

export type CategorySummaryItem = {
  category_slug: string;
  category_label?: string;
  total_products: number;
  dashboard_count: number;
  monitoring_count: number;
  critical_count: number;
  low_stock_count: number;
  sufficient_count: number;
  trending_up_count: number;
  trending_down_count: number;
  stable_count: number;
};

export type CategorySummaryResponse = {
  items: CategorySummaryItem[];
};

export type SourceHealthItem = {
  source_name: string;
  captured_at?: string;
  row_count?: number;
  success_count?: number;
  failure_count?: number;
  status?: string;
  is_stale?: boolean;
  stale_reason?: string;
};

export type SourceHealthResponse = {
  items: SourceHealthItem[];
};

export type AssistantChatRole = "user" | "assistant";

export type AssistantChatMessage = {
  role: AssistantChatRole;
  content: string;
};

export type AssistantChatRequest = {
  message: string;
  page_context?: "products" | "monitoring" | "product_detail" | "global";
  product_id?: string;
};

export type AssistantChatResponse = {
  answer: string;
  suggestions?: string[];
  referenced_product_ids?: string[];
};