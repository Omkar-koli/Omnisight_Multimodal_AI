import axios from "axios";
import {
  AssistantChatRequest,
  AssistantChatResponse,
  DashboardStatsResponse,
  DecisionEventListResponse,
  DecisionResponse,
  FreshnessListResponse,
  JobRunListResponse,
  JobTriggerResponse,
  MonitoringProductListResponse,
  MonitoringSummaryResponse,
  ProductAnalysisResponse,
  QueueResponse,
  ReviewActionRequest,
  ReviewActionResponse,
  ReviewHistoryResponse,
  ReviewQueueResponse,
  ReviewStatsResponse,
  SchedulerStatusResponse,
  SourceHealthResponse,
  SystemStatusResponse,
  Top5ProductListResponse,
  CategorySummaryResponse,
} from "./types";

export const api = axios.create({
  baseURL: "/api",
  timeout: 90000,
});

function extractError(error: any): never {
  const detail =
    error?.response?.data?.detail ||
    error?.response?.data ||
    error?.message ||
    "Unknown API error";

  throw new Error(
    typeof detail === "string" ? detail : JSON.stringify(detail, null, 2)
  );
}

async function apiGet<T>(url: string, params?: Record<string, any>): Promise<T> {
  try {
    const { data } = await api.get(url, { params });
    return data as T;
  } catch (error: any) {
    extractError(error);
  }
}

async function apiPost<T>(url: string, payload?: any): Promise<T> {
  try {
    const { data } = await api.post(url, payload);
    return data as T;
  } catch (error: any) {
    extractError(error);
  }
}

export async function getHealth() {
  return apiGet("/health");
}

export async function getDecision(productId: string): Promise<DecisionResponse> {
  return apiGet<DecisionResponse>(`/decision/${productId}`);
}

export async function getProductAnalysis(
  productId: string
): Promise<ProductAnalysisResponse> {
  return apiGet<ProductAnalysisResponse>(`/products/${productId}/analysis`);
}

export async function getQueue(params?: {
  action?: string;
  search?: string;
  category_slug?: string;
  limit?: number;
}): Promise<QueueResponse> {
  return apiGet<QueueResponse>("/products/queue", params);
}

export async function getDashboardStats(): Promise<DashboardStatsResponse> {
  return apiGet<DashboardStatsResponse>("/dashboard/stats");
}

export async function getDashboardTop5(): Promise<Top5ProductListResponse> {
  return apiGet<Top5ProductListResponse>("/dashboard/top5");
}

export async function getMonitoringProducts(params?: {
  category_slug?: string;
  trend_classification?: string;
  stock_flag?: string;
  manual_review_required?: boolean | string;
  limit?: number;
}): Promise<MonitoringProductListResponse> {
  return apiGet<MonitoringProductListResponse>("/monitoring/products", params);
}

export async function getCategoriesSummary(): Promise<CategorySummaryResponse> {
  return apiGet<CategorySummaryResponse>("/categories/summary");
}

export async function getSourceHealth(): Promise<SourceHealthResponse> {
  return apiGet<SourceHealthResponse>("/monitoring/source-health");
}

export async function getReviewStats(): Promise<ReviewStatsResponse> {
  return apiGet<ReviewStatsResponse>("/dashboard/review-stats");
}

export async function getReviewQueue(params?: {
  review_action?: string;
  reviewer_name?: string;
  limit?: number;
}): Promise<ReviewQueueResponse> {
  return apiGet<ReviewQueueResponse>("/reviews/queue", params);
}

export async function getSystemStatus(): Promise<SystemStatusResponse> {
  return apiGet<SystemStatusResponse>("/system/status");
}

export async function getDecisionHistory(
  productId: string
): Promise<ReviewHistoryResponse> {
  return apiGet<ReviewHistoryResponse>(`/decision/${productId}/history`);
}

export async function submitDecisionReview(
  productId: string,
  payload: ReviewActionRequest
): Promise<ReviewActionResponse> {
  return apiPost<ReviewActionResponse>(`/decision/${productId}/review`, payload);
}

export async function getMonitoringSummary(): Promise<MonitoringSummaryResponse> {
  return apiGet<MonitoringSummaryResponse>("/monitoring/summary");
}

export async function getRecentDecisions(
  limit = 100
): Promise<DecisionEventListResponse> {
  return apiGet<DecisionEventListResponse>("/monitoring/recent-decisions", { limit });
}

export async function getJobRuns(): Promise<JobRunListResponse> {
  return apiGet<JobRunListResponse>("/jobs/runs");
}

export async function getFreshnessSummary(): Promise<FreshnessListResponse> {
  return apiGet<FreshnessListResponse>("/freshness/summary");
}

export async function triggerAllJobs(): Promise<any> {
  return apiPost("/jobs/run/all");
}

export function getReviewExportUrl(): string {
  return "/api/reviews/export";
}

export async function getSchedulerStatus(): Promise<SchedulerStatusResponse> {
  return apiGet<SchedulerStatusResponse>("/jobs/scheduler/status");
}

export async function runSchedulerJobNow(
  jobName: string
): Promise<JobTriggerResponse> {
  return apiPost<JobTriggerResponse>(`/jobs/scheduler/run-now/${jobName}`);
}

export async function pauseSchedulerJob(
  jobName: string
): Promise<JobTriggerResponse> {
  return apiPost<JobTriggerResponse>(`/jobs/scheduler/pause/${jobName}`);
}

export async function resumeSchedulerJob(
  jobName: string
): Promise<JobTriggerResponse> {
  return apiPost<JobTriggerResponse>(`/jobs/scheduler/resume/${jobName}`);
}

export async function sendAssistantChat(
  payload: AssistantChatRequest
): Promise<AssistantChatResponse> {
  return apiPost<AssistantChatResponse>("/assistant/chat", payload);
}