"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getDecision, getProductAnalysis } from "@/lib/api";
import type { DecisionResponse, ProductAnalysisResponse } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ReviewPanel } from "@/components/dashboard/review-panel";

function stockFlagClasses(flag: string) {
  if (flag === "CRITICAL") {
    return "bg-red-100 text-red-800 border border-red-200";
  }
  if (flag === "LOW STOCK") {
    return "bg-amber-100 text-amber-800 border border-amber-200";
  }
  if (flag === "OVERSTOCK") {
    return "bg-purple-100 text-purple-800 border border-purple-200";
  }
  return "bg-emerald-100 text-emerald-800 border border-emerald-200";
}

function trendClasses(trend: string) {
  if (trend === "Trending Up") {
    return "bg-blue-100 text-blue-800 border border-blue-200";
  }
  if (trend === "Trending Down") {
    return "bg-slate-100 text-slate-800 border border-slate-200";
  }
  return "bg-zinc-100 text-zinc-800 border border-zinc-200";
}

function confidenceClasses(confidence: number) {
  if (confidence < 40) return "text-red-700";
  if (confidence < 70) return "text-amber-700";
  return "text-emerald-700";
}

function llmActionClasses(action: string) {
  if (action === "RESTOCK_NOW") {
    return "bg-red-100 text-red-800 border border-red-200";
  }
  if (action === "RESTOCK_CAUTIOUSLY") {
    return "bg-amber-100 text-amber-800 border border-amber-200";
  }
  if (action === "SLOW_REPLENISHMENT") {
    return "bg-slate-100 text-slate-800 border border-slate-200";
  }
  if (action === "CHECK_QUALITY_BEFORE_RESTOCK") {
    return "bg-purple-100 text-purple-800 border border-purple-200";
  }
  if (action === "HOLD") {
    return "bg-zinc-100 text-zinc-800 border border-zinc-200";
  }
  return "bg-blue-100 text-blue-800 border border-blue-200";
}

function trendReasonBadgeClasses(confidence: string) {
  if (confidence === "high") {
    return "bg-emerald-100 text-emerald-800 border border-emerald-200";
  }
  if (confidence === "moderate") {
    return "bg-amber-100 text-amber-800 border border-amber-200";
  }
  return "bg-zinc-100 text-zinc-800 border border-zinc-200";
}

function MetricBox({
  label,
  value,
  valueClassName = "",
}: {
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <Card className="rounded-2xl">
      <CardHeader>
        <CardTitle>{label}</CardTitle>
      </CardHeader>
      <CardContent className={`text-2xl font-semibold ${valueClassName}`}>
        {value}
      </CardContent>
    </Card>
  );
}

function BulletList({
  items,
  emptyText,
}: {
  items: string[];
  emptyText: string;
}) {
  if (!items.length) {
    return <div className="text-sm text-muted-foreground">{emptyText}</div>;
  }

  return (
    <div className="space-y-2">
      {items.map((item, idx) => (
        <div key={idx} className="text-sm text-muted-foreground">
          • {item}
        </div>
      ))}
    </div>
  );
}

function TrendReasonBlock({ analysis }: { analysis: ProductAnalysisResponse }) {
  const isTrendingUp = analysis.trend_classification === "Trending Up";
  const keywords = analysis.trend_keywords ?? [];
  const reasons = analysis.trend_reasons ?? [];
  const reasonConfidence = analysis.trend_reason_confidence ?? "not_applicable";

  if (!isTrendingUp) {
    return (
      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle>Trend Analysis</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="text-sm">
            <span className="font-medium">Classification: </span>
            {analysis.trend_classification}
          </div>
          {analysis.trend_conflict ? (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              Trend and review signals conflict. Treat this result with caution.
            </div>
          ) : null}
          <div className="text-sm text-muted-foreground">
            {analysis.trend_summary || "No trend summary available."}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="rounded-2xl">
      <CardHeader>
        <CardTitle>Why It’s Trending</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium">Classification:</span>
          <span
            className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${trendClasses(
              analysis.trend_classification
            )}`}
          >
            {analysis.trend_classification}
          </span>
          <span
            className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${trendReasonBadgeClasses(
              reasonConfidence
            )}`}
          >
            {reasonConfidence.replaceAll("_", " ")} confidence
          </span>
        </div>

        {analysis.trend_conflict ? (
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            Trend and review signals conflict. Treat this trend explanation with caution.
          </div>
        ) : null}

        <div>
          <div className="mb-2 text-sm font-medium">Top Search / Review Keywords</div>
          {keywords.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {keywords.slice(0, 5).map((keyword, idx) => (
                <span
                  key={`${keyword}-${idx}`}
                  className="rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground"
                >
                  {keyword}
                </span>
              ))}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              No strong keyword evidence is available.
            </div>
          )}
        </div>

        <div>
          <div className="mb-2 text-sm font-medium">Top Reasons</div>
          <BulletList
            items={reasons.slice(0, 3)}
            emptyText="Recent reviews are too few or too old to explain the trend reliably."
          />
        </div>

        {analysis.trend_summary ? (
          <div className="rounded-xl border bg-muted/20 p-3 text-sm text-muted-foreground">
            {analysis.trend_summary}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

export default function ProductDecisionPage() {
  const params = useParams<{ productId: string }>();
  const productId = params.productId;

  const [decision, setDecision] = useState<DecisionResponse | null>(null);
  const [analysis, setAnalysis] = useState<ProductAnalysisResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!productId) return;

    setLoading(true);
    Promise.all([getDecision(productId), getProductAnalysis(productId)])
      .then(([decisionRes, analysisRes]) => {
        setDecision(decisionRes);
        setAnalysis(analysisRes);
        setError("");
      })
      .catch((err) => {
        setError(String(err));
      })
      .finally(() => setLoading(false));
  }, [productId]);

  if (loading) return <div>Loading product analysis...</div>;
  if (error) return <div className="text-red-500">{error}</div>;
  if (!analysis) return <div>No product analysis returned.</div>;

  const llm = decision;
  const confidencePct = Number(analysis.confidence_pct ?? 0);
  const llmConfidencePct = Number(llm?.llm_confidence ?? 0) * 100;
  const baselineConfidencePct = Number(llm?.baseline_confidence ?? 0) * 100;

  return (
    <div className="space-y-6">
      <Card className="rounded-3xl">
        <CardContent className="p-6">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${stockFlagClasses(
                  analysis.stock_flag
                )}`}
              >
                {analysis.stock_flag}
              </span>

              <span
                className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${trendClasses(
                  analysis.trend_classification
                )}`}
              >
                {analysis.trend_classification}
              </span>

              {analysis.manual_review_required ? (
                <span className="inline-flex rounded-full border border-red-200 bg-red-50 px-2.5 py-1 text-xs font-medium text-red-700">
                  Manual Review Required
                </span>
              ) : null}

              {analysis.destination_view ? (
                <span className="inline-flex rounded-full border bg-muted px-2.5 py-1 text-xs font-medium text-foreground">
                  {analysis.destination_view === "dashboard"
                    ? "Dashboard"
                    : "Monitoring"}
                </span>
              ) : null}
            </div>

            <div>
              <h2 className="text-2xl font-semibold">{analysis.title}</h2>
              <p className="text-sm text-muted-foreground">{analysis.product_id}</p>
              <p className="text-sm text-muted-foreground">
                {analysis.category_label ||
                  analysis.category_slug ||
                  "Unknown Category"}
              </p>
            </div>

            <div className="text-sm text-muted-foreground">
              {analysis.executive_summary || "No executive summary available."}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricBox
          label="Current Quantity"
          value={Number(analysis.current_quantity ?? 0).toFixed(0)}
        />
        <MetricBox
          label="Dynamic Threshold"
          value={Number(analysis.threshold_units ?? 0).toFixed(0)}
        />
        <MetricBox
          label="Projected Weekly Demand"
          value={Number(analysis.projected_weekly_demand ?? 0).toFixed(1)}
        />
        <MetricBox
          label="Recommended Order Qty"
          value={Number(analysis.recommended_order_qty ?? 0).toFixed(0)}
        />
        <MetricBox
          label="Confidence"
          value={`${confidencePct.toFixed(0)}%`}
          valueClassName={confidenceClasses(confidencePct)}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <TrendReasonBlock analysis={analysis} />

        <Card className="rounded-2xl">
          <CardHeader>
            <CardTitle>Stock Assessment</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-sm">
              <span className="font-medium">Stock Flag: </span>
              {analysis.stock_flag}
            </div>
            <div className="text-sm">
              <span className="font-medium">Units Short: </span>
              {Number(analysis.units_short ?? 0).toFixed(0)}
            </div>
            <div className="text-sm text-muted-foreground">
              {analysis.threshold_explanation ||
                "No threshold explanation available."}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle>Order Recommendation</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="text-base font-medium">
            {Number(analysis.recommended_order_qty ?? 0) > 0
              ? `Order approximately ${Number(
                  analysis.recommended_order_qty ?? 0
                ).toFixed(0)} units`
              : "Do not restock yet"}
          </div>
          <div className="text-sm text-muted-foreground">
            {analysis.order_recommendation ||
              "No order recommendation explanation available."}
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle>Confidence Notes</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div
            className={`text-base font-medium ${confidenceClasses(confidencePct)}`}
          >
            Analysis Confidence: {confidencePct.toFixed(0)}%
          </div>
          <div className="text-sm text-muted-foreground">
            {analysis.confidence_notes || "No confidence notes available."}
          </div>
          {analysis.manual_review_required ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              Confidence is below the safety threshold. Manual review is required
              before acting.
            </div>
          ) : null}
        </CardContent>
      </Card>

      {llm ? (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>Baseline Action</CardTitle>
              </CardHeader>
              <CardContent>
                <Badge variant="outline">{llm.baseline_action}</Badge>
              </CardContent>
            </Card>

            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>Baseline Confidence</CardTitle>
              </CardHeader>
              <CardContent>{baselineConfidencePct.toFixed(0)}%</CardContent>
            </Card>

            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>LLM Action</CardTitle>
              </CardHeader>
              <CardContent>
                <Badge className={llmActionClasses(llm.llm_final_action)}>
                  {llm.llm_final_action}
                </Badge>
              </CardContent>
            </Card>

            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>LLM Confidence</CardTitle>
              </CardHeader>
              <CardContent>{llmConfidencePct.toFixed(0)}%</CardContent>
            </Card>
          </div>

          <Card className="rounded-2xl">
            <CardHeader>
              <CardTitle>LLM Reasoning Summary</CardTitle>
            </CardHeader>
            <CardContent>{llm.reasoning_summary}</CardContent>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>Key Risks</CardTitle>
              </CardHeader>
              <CardContent>
                <BulletList
                  items={llm.key_risks}
                  emptyText="No key risks returned."
                />
              </CardContent>
            </Card>

            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>Key Opportunities</CardTitle>
              </CardHeader>
              <CardContent>
                <BulletList
                  items={llm.key_opportunities}
                  emptyText="No key opportunities returned."
                />
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>Caution Flags</CardTitle>
              </CardHeader>
              <CardContent>
                <BulletList
                  items={llm.caution_flags}
                  emptyText="No caution flags returned."
                />
              </CardContent>
            </Card>

            <Card className="rounded-2xl">
              <CardHeader>
                <CardTitle>Follow-up Actions</CardTitle>
              </CardHeader>
              <CardContent>
                <BulletList
                  items={llm.follow_up_actions}
                  emptyText="No follow-up actions returned."
                />
              </CardContent>
            </Card>
          </div>

          <Card className="rounded-2xl">
            <CardHeader>
              <CardTitle>Supporting Evidence</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {llm.supporting_evidence.length > 0 ? (
                llm.supporting_evidence.map((item, idx) => (
                  <div key={idx} className="rounded-xl border p-3">
                    <div className="mb-1 text-sm font-medium uppercase text-muted-foreground">
                      {item.source}
                    </div>
                    <div>{item.summary}</div>
                  </div>
                ))
              ) : (
                <div className="text-sm text-muted-foreground">
                  No supporting evidence returned.
                </div>
              )}
            </CardContent>
          </Card>
        </>
      ) : null}

      <ReviewPanel productId={productId} />
    </div>
  );
}