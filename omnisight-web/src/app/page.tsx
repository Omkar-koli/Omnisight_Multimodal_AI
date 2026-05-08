import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { fastapiGet } from "@/lib/server-api";
import { MetricCard } from "@/components/dashboard/metric-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Top5Item = {
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
  trend_keywords?: string[];
  trend_reasons?: string[];
  trend_reason_confidence?: string;
};

type AlertItem = {
  alert_id: string;
  severity: "critical" | "warning" | "info";
  alert_type: string;
  title: string;
  message: string;
  product_id?: string;
  category_slug?: string;
  source_name?: string;
  created_from?: string;
  metric_value?: number;
};

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
  if (confidence < 40) {
    return "text-red-700";
  }
  if (confidence < 70) {
    return "text-amber-700";
  }
  return "text-emerald-700";
}

function alertClasses(severity: string) {
  if (severity === "critical") {
    return "bg-red-100 text-red-800 border-red-200";
  }
  if (severity === "warning") {
    return "bg-amber-100 text-amber-800 border-amber-200";
  }
  return "bg-blue-100 text-blue-800 border-blue-200";
}

function TrendingReasonBlock({ item }: { item: Top5Item }) {
  const isTrendingUp = item.trend_classification === "Trending Up";
  const keywords = item.trend_keywords ?? [];
  const reasons = item.trend_reasons ?? [];
  const confidence = item.trend_reason_confidence ?? "not_applicable";

  if (!isTrendingUp) return null;

  return (
    <div className="mt-4 rounded-2xl border bg-muted/20 p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          Why It’s Trending
        </div>
        <span
          className={`rounded-full px-2 py-1 text-[10px] font-medium ${
            confidence === "high"
              ? "bg-emerald-100 text-emerald-800"
              : confidence === "moderate"
              ? "bg-amber-100 text-amber-800"
              : "bg-zinc-100 text-zinc-800"
          }`}
        >
          {confidence.replaceAll("_", " ")}
        </span>
      </div>

      {keywords.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-2">
          {keywords.slice(0, 5).map((keyword, idx) => (
            <span
              key={`${keyword}-${idx}`}
              className="rounded-full bg-background px-2.5 py-1 text-[11px] text-muted-foreground"
            >
              {keyword}
            </span>
          ))}
        </div>
      ) : (
        <div className="mt-2 text-sm text-muted-foreground">
          No strong keyword evidence is available.
        </div>
      )}

      <div className="mt-3 space-y-1">
        {reasons.length > 0 ? (
          reasons.slice(0, 3).map((reason, idx) => (
            <p key={idx} className="text-sm text-muted-foreground">
              • {reason}
            </p>
          ))
        ) : (
          <p className="text-sm text-muted-foreground">
            Recent reviews are too few or too old to explain the trend reliably.
          </p>
        )}
      </div>
    </div>
  );
}

export default async function HomePage() {
  const session = await auth();
  if (!session?.user) {
    redirect("/login");
  }

  const [stats, top5, alerts] = await Promise.all([
    fastapiGet("/dashboard/stats"),
    fastapiGet("/dashboard/top5"),
    fastapiGet("/alerts/list?limit=8"),
  ]);

  const topItems: Top5Item[] = top5?.items ?? [];
  const alertItems: AlertItem[] = alerts?.items ?? [];

  const criticalCount = topItems.filter((item) => item.stock_flag === "CRITICAL").length;
  const lowStockCount = topItems.filter((item) => item.stock_flag === "LOW STOCK").length;
  const overstockCount = topItems.filter((item) => item.stock_flag === "OVERSTOCK").length;
  const trendingUpCount = topItems.filter((item) => item.trend_classification === "Trending Up").length;

  const avgTopConfidence =
    topItems.length > 0
      ? Math.round(
          topItems.reduce(
            (sum, item) => sum + Number(item.confidence_pct ?? 0),
            0
          ) / topItems.length
        )
      : 0;

  const criticalAlertCount = alertItems.filter((item) => item.severity === "critical").length;
  const warningAlertCount = alertItems.filter((item) => item.severity === "warning").length;
  const infoAlertCount = alertItems.filter((item) => item.severity === "info").length;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 xl:grid-cols-[1.35fr_0.65fr]">
        <Card className="rounded-3xl">
          <CardContent className="p-6">
            <div className="space-y-3">
              <div className="text-sm font-medium text-muted-foreground">
                OmniSight decision workspace
              </div>
              <div>
                <h1 className="text-3xl font-semibold tracking-tight">Dashboard</h1>
                <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
                  A minimal control center focused on urgent products, recommendation confidence,
                  and active alert pressure.
                </p>
              </div>

              <div className="flex flex-wrap gap-3 pt-2">
                <Link
                  href="/monitoring"
                  className="inline-flex rounded-2xl border px-4 py-2.5 text-sm font-medium transition hover:bg-muted/40"
                >
                  Open Monitoring
                </Link>
                <Link
                  href="/products"
                  className="inline-flex rounded-2xl border px-4 py-2.5 text-sm font-medium transition hover:bg-muted/40"
                >
                  Browse Products
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
          <Card className="rounded-3xl">
            <CardContent className="p-5">
              <div className="text-sm text-muted-foreground">Urgent Top 5</div>
              <div className="mt-2 text-3xl font-semibold">{topItems.length}</div>
              <div className="mt-2 text-xs text-muted-foreground">
                Highest-priority products surfaced to the dashboard.
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-3xl">
            <CardContent className="p-5">
              <div className="text-sm text-muted-foreground">Active Alerts</div>
              <div className="mt-2 text-3xl font-semibold">{alertItems.length}</div>
              <div className="mt-2 text-xs text-muted-foreground">
                Compact summary shown below. Full alert page can come next.
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard title="Total Products" value={stats?.total_products ?? 0} />
        <MetricCard title="Critical in Top 5" value={criticalCount} />
        <MetricCard title="Low Stock in Top 5" value={lowStockCount} />
        <MetricCard title="Overstock in Top 5" value={overstockCount} />
        <MetricCard title="Trending Up in Top 5" value={trendingUpCount} />
        <MetricCard title="Avg Top-5 Confidence" value={avgTopConfidence} />
      </div>

      <Card className="rounded-3xl">
        <CardHeader>
          <CardTitle>Alert Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <MetricCard title="Critical Alerts" value={criticalAlertCount} />
            <MetricCard title="Warning Alerts" value={warningAlertCount} />
            <MetricCard title="Info Alerts" value={infoAlertCount} />
          </div>

          <details className="group rounded-2xl border bg-background p-4">
            <summary className="cursor-pointer list-none text-sm font-medium">
              <span className="flex items-center justify-between">
                <span>View active alerts</span>
                <span className="text-xs text-muted-foreground group-open:hidden">
                  Expand
                </span>
                <span className="hidden text-xs text-muted-foreground group-open:inline">
                  Collapse
                </span>
              </span>
            </summary>

            <div className="mt-4 space-y-3">
              {alertItems.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  No active alerts are available right now.
                </div>
              ) : (
                alertItems.map((alert) => (
                  <div
                    key={alert.alert_id}
                    className="rounded-2xl border bg-muted/20 p-4"
                  >
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span
                            className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${alertClasses(
                              alert.severity
                            )}`}
                          >
                            {alert.severity.toUpperCase()}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {alert.alert_type.replaceAll("_", " ")}
                          </span>
                        </div>
                        <div className="text-sm font-semibold">{alert.title}</div>
                        <div className="text-sm text-muted-foreground">
                          {alert.message}
                        </div>
                      </div>

                      {alert.product_id ? (
                        <Link
                          href={`/products/${alert.product_id}`}
                          className="inline-flex rounded-xl border px-3 py-2 text-sm font-medium transition hover:bg-muted/40"
                        >
                          Open Product
                        </Link>
                      ) : null}
                    </div>
                  </div>
                ))
              )}
            </div>
          </details>
        </CardContent>
      </Card>

      <Card className="rounded-3xl">
        <CardHeader>
          <CardTitle>Top 5 Most Urgent Products</CardTitle>
        </CardHeader>
        <CardContent>
          {topItems.length === 0 ? (
            <div className="text-sm text-muted-foreground">
              No urgent products are available yet. Run the recommendation pipeline first.
            </div>
          ) : (
            <div className="grid gap-4 xl:grid-cols-2">
              {topItems.map((item, index) => (
                <Link
                  key={item.product_id}
                  href={`/products/${item.product_id}`}
                  className="block rounded-3xl border bg-background p-5 transition hover:bg-muted/30"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        Rank #{index + 1}
                      </div>
                      <h3 className="line-clamp-2 text-base font-semibold">
                        {item.title}
                      </h3>
                      <div className="text-sm text-muted-foreground">
                        {item.category_label || item.category_slug || "Unknown Category"}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {item.product_id}
                      </div>
                    </div>

                    <div
                      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${stockFlagClasses(
                        item.stock_flag
                      )}`}
                    >
                      {item.stock_flag}
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <span
                      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${trendClasses(
                        item.trend_classification
                      )}`}
                    >
                      {item.trend_classification}
                    </span>
                  </div>

                  <TrendingReasonBlock item={item} />

                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <div className="rounded-xl bg-muted/40 p-3">
                      <div className="text-xs text-muted-foreground">Current Qty</div>
                      <div className="mt-1 text-lg font-semibold">
                        {Number(item.current_quantity ?? 0).toFixed(0)}
                      </div>
                    </div>

                    <div className="rounded-xl bg-muted/40 p-3">
                      <div className="text-xs text-muted-foreground">
                        Recommended Order
                      </div>
                      <div className="mt-1 text-lg font-semibold">
                        {Number(item.recommended_order_qty ?? 0).toFixed(0)}
                      </div>
                    </div>

                    <div className="rounded-xl bg-muted/40 p-3">
                      <div className="text-xs text-muted-foreground">Confidence</div>
                      <div
                        className={`mt-1 text-lg font-semibold ${confidenceClasses(
                          Number(item.confidence_pct ?? 0)
                        )}`}
                      >
                        {Number(item.confidence_pct ?? 0).toFixed(0)}%
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 text-sm text-muted-foreground">
                    {item.executive_summary || "No summary available."}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}