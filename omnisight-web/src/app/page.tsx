import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { fastapiGet } from "@/lib/server-api";
import { MetricCard } from "@/components/dashboard/metric-card";
import { Card, CardContent } from "@/components/ui/card";
import { ChevronRight, AlertTriangle, TrendingUp } from "lucide-react";

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
};

type AlertItem = {
  alert_id: string;
  severity: "critical" | "warning" | "info";
  alert_type: string;
  title: string;
  message: string;
  product_id?: string;
};

function stockFlagPill(flag: string) {
  if (flag === "CRITICAL")
    return "bg-destructive/10 text-destructive border-destructive/30";
  if (flag === "LOW STOCK")
    return "bg-primary/10 text-primary border-primary/30";
  if (flag === "OVERSTOCK")
    return "bg-muted text-muted-foreground border-border";
  return "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-400 dark:border-emerald-900";
}

function confidenceClasses(c: number) {
  if (c < 40) return "text-destructive";
  if (c < 70) return "text-primary";
  return "text-emerald-600 dark:text-emerald-400";
}

function alertPill(severity: string) {
  if (severity === "critical")
    return "bg-destructive/10 text-destructive border-destructive/30";
  if (severity === "warning")
    return "bg-primary/10 text-primary border-primary/30";
  return "bg-muted text-muted-foreground border-border";
}

export default async function HomePage() {
  const session = await auth();
  if (!session?.user) redirect("/login");

  const [stats, top5, alerts] = await Promise.all([
    fastapiGet("/dashboard/stats"),
    fastapiGet("/dashboard/top5"),
    fastapiGet("/alerts/list?limit=8"),
  ]);

  const topItems: Top5Item[] = top5?.items ?? [];
  const alertItems: AlertItem[] = alerts?.items ?? [];

  const criticalAlerts = alertItems.filter((a) => a.severity === "critical").length;
  const trendingUp = topItems.filter((i) => i.trend_classification === "Trending Up").length;
  const avgConfidence =
    topItems.length > 0
      ? Math.round(
          topItems.reduce((s, i) => s + Number(i.confidence_pct ?? 0), 0) /
            topItems.length
        )
      : 0;

  return (
    <div className="space-y-6">
      {/* ── Page header (slim) ── */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Urgent products and active risk in one view.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/monitoring"
            className="rounded-md border bg-card px-3.5 py-2 text-sm font-medium transition hover:bg-muted/50"
          >
            Monitoring
          </Link>
          <Link
            href="/products"
            className="rounded-md bg-foreground px-3.5 py-2 text-sm font-medium text-background transition hover:opacity-90"
          >
            Browse Products
          </Link>
        </div>
      </div>

      {/* ── 4 focus metrics (was 6) ── */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Total Products"
          value={stats?.total_products ?? 0}
          subtitle="under management"
        />
        <MetricCard
          title="Urgent Top 5"
          value={topItems.length}
          subtitle="needs decision"
          accent
        />
        <MetricCard
          title="Trending Up"
          value={trendingUp}
          subtitle="of top 5"
        />
        <MetricCard
          title="Avg Confidence"
          value={`${avgConfidence}%`}
          subtitle="top 5 average"
        />
      </div>

      {/* ── Alert strip (collapsed by default; only critical surfaced) ── */}
      <Card className="rounded-xl">
        <CardContent className="p-0">
          <details className="group">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 transition hover:bg-muted/30">
              <div className="flex items-center gap-3">
                <div
                  className={`flex h-9 w-9 items-center justify-center rounded-md border ${
                    criticalAlerts > 0
                      ? "border-destructive/30 bg-destructive/10 text-destructive"
                      : "border-border bg-muted text-muted-foreground"
                  }`}
                >
                  <AlertTriangle className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-sm font-medium">
                    {alertItems.length} active alert
                    {alertItems.length === 1 ? "" : "s"}
                    {criticalAlerts > 0 ? (
                      <span className="ml-2 inline-flex rounded-full border border-destructive/30 bg-destructive/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-destructive">
                        {criticalAlerts} critical
                      </span>
                    ) : null}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Tap to expand details
                  </div>
                </div>
              </div>
              <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform group-open:rotate-90" />
            </summary>

            <div className="border-t px-5 py-4">
              {alertItems.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  No active alerts.
                </div>
              ) : (
                <div className="space-y-2">
                  {alertItems.slice(0, 6).map((alert) => (
                    <div
                      key={alert.alert_id}
                      className="flex items-start justify-between gap-3 rounded-md border bg-background px-3 py-2.5"
                    >
                      <div className="min-w-0 flex-1 space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span
                            className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${alertPill(
                              alert.severity
                            )}`}
                          >
                            {alert.severity}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {alert.alert_type.replaceAll("_", " ")}
                          </span>
                        </div>
                        <div className="text-sm font-medium truncate">
                          {alert.title}
                        </div>
                        <div className="text-xs text-muted-foreground line-clamp-1">
                          {alert.message}
                        </div>
                      </div>
                      {alert.product_id ? (
                        <Link
                          href={`/products/${alert.product_id}`}
                          className="shrink-0 rounded-md border px-2.5 py-1.5 text-xs font-medium transition hover:bg-muted"
                        >
                          Open
                        </Link>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </details>
        </CardContent>
      </Card>

      {/* ── Top 5 — list, not card grid ── */}
      <Card className="rounded-xl">
        <CardContent className="p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold">
                Top 5 Most Urgent
              </h2>
              <p className="text-xs text-muted-foreground">
                Highest-priority products surfaced now
              </p>
            </div>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </div>

          {topItems.length === 0 ? (
            <div className="rounded-md border border-dashed py-10 text-center text-sm text-muted-foreground">
              No urgent products yet. Run the recommendation pipeline.
            </div>
          ) : (
            <div className="divide-y">
              {topItems.map((item, index) => (
                <Link
                  key={item.product_id}
                  href={`/products/${item.product_id}`}
                  className="group flex items-center gap-4 py-3.5 transition hover:bg-muted/30"
                >
                  <div className="w-8 shrink-0 text-center text-xs font-semibold text-muted-foreground tabular-nums">
                    {String(index + 1).padStart(2, "0")}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">
                      {item.title}
                    </div>
                    <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
                      <span className="truncate">
                        {item.category_label || item.category_slug || "—"}
                      </span>
                      <span>·</span>
                      <span
                        className={`rounded-full border px-1.5 py-0 text-[10px] font-medium uppercase tracking-wider ${stockFlagPill(
                          item.stock_flag
                        )}`}
                      >
                        {item.stock_flag}
                      </span>
                    </div>
                  </div>

                  <div className="hidden md:block w-24 text-right">
                    <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                      Order
                    </div>
                    <div className="text-sm font-semibold tabular-nums">
                      {Number(item.recommended_order_qty ?? 0).toFixed(0)}
                    </div>
                  </div>

                  <div className="w-20 text-right">
                    <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                      Confidence
                    </div>
                    <div
                      className={`text-sm font-semibold tabular-nums ${confidenceClasses(
                        Number(item.confidence_pct ?? 0)
                      )}`}
                    >
                      {Number(item.confidence_pct ?? 0).toFixed(0)}%
                    </div>
                  </div>

                  <ChevronRight className="hidden h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 sm:block" />
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
