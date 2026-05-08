import Link from "next/link";
import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { fastapiGet } from "@/lib/server-api";
import { MetricCard } from "@/components/dashboard/metric-card";
import { Card, CardContent } from "@/components/ui/card";
import { BarMetricChart } from "@/components/dashboard/bar-metric-chart";
import { DistributionDonutChart } from "@/components/monitoring/distribution-donut-chart";
import { CategoryHealthChart } from "@/components/monitoring/category-health-chart";
import { StockThresholdLineChart } from "@/components/monitoring/stock-threshold-line-chart";
import { ChevronRight, AlertTriangle, Activity } from "lucide-react";

type SourceHealthItem = {
  source_name?: string;
  captured_at?: string;
  row_count?: number;
  success_count?: number;
  failure_count?: number;
  status?: string;
  is_stale?: boolean;
  stale_reason?: string;
};

type MonitoringProductItem = {
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

type CategorySummaryItem = {
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

type AlertItem = {
  alert_id: string;
  severity: "critical" | "warning" | "info";
  alert_type: string;
  title: string;
  message: string;
  product_id?: string;
};

function getSingleParam(value: string | string[] | undefined, fallback = ""): string {
  if (Array.isArray(value)) return value[0] ?? fallback;
  return value ?? fallback;
}

function stockFlagPill(flag: string) {
  if (flag === "CRITICAL")
    return "bg-destructive/10 text-destructive border-destructive/30";
  if (flag === "LOW STOCK")
    return "bg-primary/10 text-primary border-primary/30";
  if (flag === "OVERSTOCK")
    return "bg-muted text-muted-foreground border-border";
  return "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-400 dark:border-emerald-900";
}

function trendPill(trend: string) {
  if (trend === "Trending Up") return "bg-primary/10 text-primary border-primary/30";
  if (trend === "Trending Down") return "bg-muted text-muted-foreground border-border";
  return "bg-muted/60 text-muted-foreground border-border";
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

function buildMonitoringQuery(p: {
  categorySlug?: string;
  trendClassification?: string;
  stockFlag?: string;
  manualReviewRequired?: string;
  limit?: number;
}) {
  const sp = new URLSearchParams();
  if (p.categorySlug) sp.set("category_slug", p.categorySlug);
  if (p.trendClassification) sp.set("trend_classification", p.trendClassification);
  if (p.stockFlag) sp.set("stock_flag", p.stockFlag);
  if (p.manualReviewRequired) sp.set("manual_review_required", p.manualReviewRequired);
  sp.set("limit", String(p.limit ?? 500));
  return `/monitoring/products?${sp.toString()}`;
}

function buildFilterHref(
  current: { categorySlug: string; trendClassification: string; stockFlag: string; manualReviewRequired: string },
  next: Partial<{ categorySlug: string; trendClassification: string; stockFlag: string; manualReviewRequired: string }>
) {
  const merged = {
    categorySlug: next.categorySlug ?? current.categorySlug,
    trendClassification: next.trendClassification ?? current.trendClassification,
    stockFlag: next.stockFlag ?? current.stockFlag,
    manualReviewRequired: next.manualReviewRequired ?? current.manualReviewRequired,
  };
  const params = new URLSearchParams();
  if (merged.categorySlug) params.set("category_slug", merged.categorySlug);
  if (merged.trendClassification) params.set("trend_classification", merged.trendClassification);
  if (merged.stockFlag) params.set("stock_flag", merged.stockFlag);
  if (merged.manualReviewRequired) params.set("manual_review_required", merged.manualReviewRequired);
  const qs = params.toString();
  return qs ? `/monitoring?${qs}` : "/monitoring";
}

function FilterChip({
  href,
  label,
  active,
}: {
  href: string;
  label: string;
  active: boolean;
}) {
  return (
    <Link
      href={href}
      className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
        active
          ? "border-foreground bg-foreground text-background"
          : "border-border bg-card text-muted-foreground hover:border-foreground/30 hover:text-foreground"
      }`}
    >
      {label}
    </Link>
  );
}

export default async function MonitoringPage({
  searchParams,
}: {
  searchParams?: Promise<{
    category_slug?: string | string[];
    trend_classification?: string | string[];
    stock_flag?: string | string[];
    manual_review_required?: string | string[];
  }>;
}) {
  const session = await auth();
  if (!session?.user) redirect("/login");

  const resolvedSearchParams = await searchParams;
  const categorySlug = getSingleParam(resolvedSearchParams?.category_slug);
  const trendClassification = getSingleParam(resolvedSearchParams?.trend_classification);
  const stockFlag = getSingleParam(resolvedSearchParams?.stock_flag);
  const manualReviewRequired = getSingleParam(resolvedSearchParams?.manual_review_required);

  const [monitoring, sourceHealth, categories, alerts] = await Promise.all([
    fastapiGet(
      buildMonitoringQuery({
        categorySlug,
        trendClassification,
        stockFlag,
        manualReviewRequired,
        limit: 500,
      })
    ),
    fastapiGet("/monitoring/source-health"),
    fastapiGet("/categories/summary"),
    fastapiGet("/alerts/list?limit=20"),
  ]);

  const items: MonitoringProductItem[] = monitoring?.items ?? [];
  const sourceItems: SourceHealthItem[] = sourceHealth?.items ?? [];
  const categoryItems: CategorySummaryItem[] = categories?.items ?? [];
  const alertItems: AlertItem[] = alerts?.items ?? [];

  // Aggregations
  const criticalCount = items.filter((i) => i.stock_flag === "CRITICAL").length;
  const lowStockCount = items.filter((i) => i.stock_flag === "LOW STOCK").length;
  const trendingUpCount = items.filter((i) => i.trend_classification === "Trending Up").length;
  const manualReviewCount = items.filter((i) => Boolean(i.manual_review_required)).length;

  const criticalAlerts = alertItems.filter((a) => a.severity === "critical").length;
  const staleSources = sourceItems.filter((s) => Boolean(s.is_stale)).length;

  const stockFlagData = [
    { name: "Critical", value: criticalCount },
    { name: "Low Stock", value: lowStockCount },
    {
      name: "Sufficient",
      value: items.filter((i) => i.stock_flag === "SUFFICIENT").length,
    },
    {
      name: "Overstock",
      value: items.filter((i) => i.stock_flag === "OVERSTOCK").length,
    },
  ];

  const trendDistributionData = [
    { name: "Trending Up", value: trendingUpCount },
    {
      name: "Stable",
      value: items.filter((i) => i.trend_classification === "Stable").length,
    },
    {
      name: "Trending Down",
      value: items.filter((i) => i.trend_classification === "Trending Down").length,
    },
  ];

  const categoryHealthData = categoryItems.map((c) => ({
    name: c.category_label || c.category_slug,
    critical: c.critical_count,
    low_stock: c.low_stock_count,
    trending_up: c.trending_up_count,
  }));

  const stockThresholdChartData = [...items]
    .map((i) => ({
      name: i.title.length > 18 ? `${i.title.slice(0, 18)}…` : i.title,
      current_quantity: Number(i.current_quantity ?? 0),
      threshold_units: Number(i.threshold_units ?? 0),
      pressure_gap: Number(i.threshold_units ?? 0) - Number(i.current_quantity ?? 0),
    }))
    .sort((a, b) => b.pressure_gap - a.pressure_gap)
    .slice(0, 10)
    .map(({ name, current_quantity, threshold_units }) => ({
      name,
      current_quantity,
      threshold_units,
    }));

  const currentFilters = { categorySlug, trendClassification, stockFlag, manualReviewRequired };

  return (
    <div className="space-y-6">
      {/* ── Slim header ── */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Monitoring</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Detailed product health and operational signals.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/"
            className="rounded-md border bg-card px-3.5 py-2 text-sm font-medium transition hover:bg-muted/50"
          >
            Dashboard
          </Link>
          <Link
            href="/products"
            className="rounded-md border bg-card px-3.5 py-2 text-sm font-medium transition hover:bg-muted/50"
          >
            Products
          </Link>
        </div>
      </div>

      {/* ── 4 focus metrics ── */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard title="In View" value={items.length} subtitle="filtered products" accent />
        <MetricCard title="Critical" value={criticalCount} subtitle="immediate action" />
        <MetricCard title="Trending Up" value={trendingUpCount} subtitle="rising demand" />
        <MetricCard title="Manual Review" value={manualReviewCount} subtitle="needs analyst" />
      </div>

      {/* ── Filters: compact chip row, no card chrome ── */}
      <Card className="rounded-xl">
        <CardContent className="space-y-3.5 px-5 py-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Category
            </span>
            <FilterChip
              href={buildFilterHref(currentFilters, { categorySlug: "" })}
              label="All"
              active={!categorySlug}
            />
            {categoryItems.map((c) => (
              <FilterChip
                key={c.category_slug}
                href={buildFilterHref(currentFilters, { categorySlug: c.category_slug })}
                label={c.category_label || c.category_slug}
                active={categorySlug === c.category_slug}
              />
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Stock
            </span>
            {["", "CRITICAL", "LOW STOCK", "SUFFICIENT", "OVERSTOCK"].map((v) => (
              <FilterChip
                key={v || "all-stock"}
                href={buildFilterHref(currentFilters, { stockFlag: v })}
                label={v || "All"}
                active={stockFlag === v}
              />
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Trend
            </span>
            {["", "Trending Up", "Stable", "Trending Down"].map((v) => (
              <FilterChip
                key={v || "all-trend"}
                href={buildFilterHref(currentFilters, { trendClassification: v })}
                label={v || "All"}
                active={trendClassification === v}
              />
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Review
            </span>
            {[
              { l: "All", v: "" },
              { l: "Required", v: "true" },
              { l: "Not required", v: "false" },
            ].map((opt) => (
              <FilterChip
                key={opt.l}
                href={buildFilterHref(currentFilters, { manualReviewRequired: opt.v })}
                label={opt.l}
                active={manualReviewRequired === opt.v}
              />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* ── Operational health row: alerts + sources, both collapsed ── */}
      <div className="grid gap-3 md:grid-cols-2">
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
                      {alertItems.length} active alert{alertItems.length === 1 ? "" : "s"}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {criticalAlerts} critical · expand for details
                    </div>
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform group-open:rotate-90" />
              </summary>

              <div className="border-t px-5 py-4 space-y-2">
                {alertItems.length === 0 ? (
                  <div className="text-sm text-muted-foreground">No active alerts.</div>
                ) : (
                  alertItems.slice(0, 6).map((a) => (
                    <div
                      key={a.alert_id}
                      className="flex items-start justify-between gap-3 rounded-md border bg-background px-3 py-2.5"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span
                            className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${alertPill(
                              a.severity
                            )}`}
                          >
                            {a.severity}
                          </span>
                        </div>
                        <div className="mt-0.5 truncate text-sm font-medium">
                          {a.title}
                        </div>
                      </div>
                      {a.product_id ? (
                        <Link
                          href={`/products/${a.product_id}`}
                          className="shrink-0 rounded-md border px-2.5 py-1.5 text-xs font-medium transition hover:bg-muted"
                        >
                          Open
                        </Link>
                      ) : null}
                    </div>
                  ))
                )}
              </div>
            </details>
          </CardContent>
        </Card>

        <Card className="rounded-xl">
          <CardContent className="p-0">
            <details className="group">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 transition hover:bg-muted/30">
                <div className="flex items-center gap-3">
                  <div
                    className={`flex h-9 w-9 items-center justify-center rounded-md border ${
                      staleSources > 0
                        ? "border-destructive/30 bg-destructive/10 text-destructive"
                        : "border-border bg-muted text-muted-foreground"
                    }`}
                  >
                    <Activity className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="text-sm font-medium">
                      {sourceItems.length} data source
                      {sourceItems.length === 1 ? "" : "s"}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {staleSources} stale · expand for details
                    </div>
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform group-open:rotate-90" />
              </summary>

              <div className="border-t px-5 py-4 space-y-2">
                {sourceItems.length === 0 ? (
                  <div className="text-sm text-muted-foreground">No source data.</div>
                ) : (
                  sourceItems.map((s, idx) => (
                    <div
                      key={`${s.source_name}-${idx}`}
                      className="flex items-center justify-between gap-3 rounded-md border bg-background px-3 py-2.5 text-sm"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="truncate font-medium capitalize">
                          {(s.source_name ?? "").replaceAll("_", " ")}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {s.row_count ?? 0} rows · {s.captured_at || "—"}
                        </div>
                      </div>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${
                          s.is_stale
                            ? "border-destructive/30 bg-destructive/10 text-destructive"
                            : "border-border bg-muted text-muted-foreground"
                        }`}
                      >
                        {s.is_stale ? "stale" : s.status ?? "ok"}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </details>
          </CardContent>
        </Card>
      </div>

      {/* ── Two key charts (was 4) ── */}
      <div className="grid gap-3 lg:grid-cols-2">
        <Card className="rounded-xl">
          <CardContent className="p-5">
            <div className="mb-3">
              <h3 className="text-sm font-semibold">Stock Flag Distribution</h3>
              <p className="text-xs text-muted-foreground">
                Where pressure sits across the filtered set
              </p>
            </div>
            <DistributionDonutChart
              data={stockFlagData}
              emptyTitle="No stock flag data available."
            />
          </CardContent>
        </Card>

        <Card className="rounded-xl">
          <CardContent className="p-5">
            <div className="mb-3">
              <h3 className="text-sm font-semibold">Category Health</h3>
              <p className="text-xs text-muted-foreground">
                Critical, low-stock and trending-up products by category
              </p>
            </div>
            <CategoryHealthChart data={categoryHealthData} />
          </CardContent>
        </Card>
      </div>

      {/* ── Trend distribution + stock-vs-threshold ── */}
      <div className="grid gap-3 lg:grid-cols-2">
        <Card className="rounded-xl">
          <CardContent className="p-5">
            <div className="mb-3">
              <h3 className="text-sm font-semibold">Trend Distribution</h3>
              <p className="text-xs text-muted-foreground">
                How filtered products are moving
              </p>
            </div>
            <BarMetricChart
              data={trendDistributionData}
              xKey="name"
              barKey="value"
              emptyTitle="No trend distribution available"
              emptyDescription="Trend categories appear after analysis runs."
            />
          </CardContent>
        </Card>

        <Card className="rounded-xl">
          <CardContent className="p-5">
            <div className="mb-3">
              <h3 className="text-sm font-semibold">
                Top Pressure: Stock vs Threshold
              </h3>
              <p className="text-xs text-muted-foreground">
                Largest gaps between current stock and threshold
              </p>
            </div>
            <StockThresholdLineChart data={stockThresholdChartData} />
          </CardContent>
        </Card>
      </div>

      {/* ── Compact products list ── */}
      <Card className="rounded-xl">
        <CardContent className="p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold">Products</h2>
              <p className="text-xs text-muted-foreground">
                {items.length} matching the current filters
              </p>
            </div>
          </div>

          {items.length === 0 ? (
            <div className="rounded-md border border-dashed py-10 text-center text-sm text-muted-foreground">
              No monitoring products match the selected filters.
            </div>
          ) : (
            <div className="divide-y">
              {items.map((item) => (
                <Link
                  key={item.product_id}
                  href={`/products/${item.product_id}`}
                  className="group flex items-start gap-4 py-3.5 transition hover:bg-muted/30"
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium">
                      {item.title}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
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
                      <span
                        className={`rounded-full border px-1.5 py-0 text-[10px] font-medium ${trendPill(
                          item.trend_classification
                        )}`}
                      >
                        {item.trend_classification}
                      </span>
                      {item.manual_review_required ? (
                        <span className="rounded-full border border-destructive/30 bg-destructive/10 px-1.5 py-0 text-[10px] font-medium uppercase tracking-wider text-destructive">
                          Review
                        </span>
                      ) : null}
                    </div>
                  </div>

                  <div className="hidden md:block w-20 text-right">
                    <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                      Stock
                    </div>
                    <div className="text-sm font-semibold tabular-nums">
                      {Number(item.current_quantity ?? 0).toFixed(0)}
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
