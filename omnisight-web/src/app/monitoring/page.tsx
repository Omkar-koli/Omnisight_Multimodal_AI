import Link from "next/link";
import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { fastapiGet } from "@/lib/server-api";
import { MetricCard } from "@/components/dashboard/metric-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { BarMetricChart } from "@/components/dashboard/bar-metric-chart";
import { DistributionDonutChart } from "@/components/monitoring/distribution-donut-chart";
import { CategoryHealthChart } from "@/components/monitoring/category-health-chart";
import { StockThresholdLineChart } from "@/components/monitoring/stock-threshold-line-chart";

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
  category_slug?: string;
  source_name?: string;
  created_from?: string;
  metric_value?: number;
};

function getSingleParam(
  value: string | string[] | undefined,
  fallback = ""
): string {
  if (Array.isArray(value)) return value[0] ?? fallback;
  return value ?? fallback;
}

function getHealthTone(item: SourceHealthItem) {
  if (item.is_stale) return "destructive";
  if ((item.status ?? "").toLowerCase() === "empty") return "secondary";
  if ((item.status ?? "").toLowerCase() === "success") return "default";
  return "outline";
}

function formatSourceName(name?: string) {
  return (name ?? "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (m) => m.toUpperCase());
}

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

function alertClasses(severity: string) {
  if (severity === "critical") {
    return "bg-red-100 text-red-800 border-red-200";
  }
  if (severity === "warning") {
    return "bg-amber-100 text-amber-800 border-amber-200";
  }
  return "bg-blue-100 text-blue-800 border-blue-200";
}

function buildMonitoringQuery(params: {
  categorySlug?: string;
  trendClassification?: string;
  stockFlag?: string;
  manualReviewRequired?: string;
  limit?: number;
}) {
  const sp = new URLSearchParams();

  if (params.categorySlug) sp.set("category_slug", params.categorySlug);
  if (params.trendClassification) {
    sp.set("trend_classification", params.trendClassification);
  }
  if (params.stockFlag) sp.set("stock_flag", params.stockFlag);
  if (params.manualReviewRequired) {
    sp.set("manual_review_required", params.manualReviewRequired);
  }
  sp.set("limit", String(params.limit ?? 500));

  return `/monitoring/products?${sp.toString()}`;
}

function buildFilterHref(
  current: {
    categorySlug: string;
    trendClassification: string;
    stockFlag: string;
    manualReviewRequired: string;
  },
  next: Partial<{
    categorySlug: string;
    trendClassification: string;
    stockFlag: string;
    manualReviewRequired: string;
  }>
) {
  const params = new URLSearchParams();

  const merged = {
    categorySlug: next.categorySlug ?? current.categorySlug,
    trendClassification:
      next.trendClassification ?? current.trendClassification,
    stockFlag: next.stockFlag ?? current.stockFlag,
    manualReviewRequired:
      next.manualReviewRequired ?? current.manualReviewRequired,
  };

  if (merged.categorySlug) params.set("category_slug", merged.categorySlug);
  if (merged.trendClassification) {
    params.set("trend_classification", merged.trendClassification);
  }
  if (merged.stockFlag) params.set("stock_flag", merged.stockFlag);
  if (merged.manualReviewRequired) {
    params.set("manual_review_required", merged.manualReviewRequired);
  }

  const qs = params.toString();
  return qs ? `/monitoring?${qs}` : "/monitoring";
}

function SourceHealthCard({ item }: { item: SourceHealthItem }) {
  return (
    <div className="rounded-3xl border bg-background p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm font-semibold">
          {formatSourceName(item.source_name)}
        </div>
        <Badge variant={getHealthTone(item)}>
          {item.is_stale ? "Stale" : (item.status ?? "unknown").toString()}
        </Badge>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
        <div className="rounded-xl bg-muted/50 p-3">
          <div className="text-xs text-muted-foreground">Rows</div>
          <div className="mt-1 font-semibold">{item.row_count ?? 0}</div>
        </div>
        <div className="rounded-xl bg-muted/50 p-3">
          <div className="text-xs text-muted-foreground">Success</div>
          <div className="mt-1 font-semibold">{item.success_count ?? 0}</div>
        </div>
        <div className="rounded-xl bg-muted/50 p-3">
          <div className="text-xs text-muted-foreground">Failure</div>
          <div className="mt-1 font-semibold">{item.failure_count ?? 0}</div>
        </div>
      </div>

      <div className="mt-4 space-y-1 text-sm text-muted-foreground">
        <div>Captured: {item.captured_at || "-"}</div>
        <div>{item.stale_reason || "No stale reason reported."}</div>
      </div>
    </div>
  );
}

function ProductMetric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl bg-muted/40 p-3">
      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 text-base font-semibold">{value}</div>
    </div>
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

  if (!session?.user) {
    redirect("/login");
  }

  const resolvedSearchParams = await searchParams;

  const categorySlug = getSingleParam(resolvedSearchParams?.category_slug);
  const trendClassification = getSingleParam(
    resolvedSearchParams?.trend_classification
  );
  const stockFlag = getSingleParam(resolvedSearchParams?.stock_flag);
  const manualReviewRequired = getSingleParam(
    resolvedSearchParams?.manual_review_required
  );

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

  const criticalAlertCount = alertItems.filter(
    (item) => item.severity === "critical"
  ).length;
  const warningAlertCount = alertItems.filter(
    (item) => item.severity === "warning"
  ).length;
  const infoAlertCount = alertItems.filter(
    (item) => item.severity === "info"
  ).length;

  const healthyCount = sourceItems.filter(
    (item) =>
      !item.is_stale && (item.status ?? "").toLowerCase() === "success"
  ).length;
  const warningCount = sourceItems.filter(
    (item) => !item.is_stale && (item.status ?? "").toLowerCase() === "empty"
  ).length;
  const staleCount = sourceItems.filter((item) => Boolean(item.is_stale)).length;

  const criticalCount = items.filter(
    (item) => item.stock_flag === "CRITICAL"
  ).length;
  const lowStockCount = items.filter(
    (item) => item.stock_flag === "LOW STOCK"
  ).length;
  const overstockCount = items.filter(
    (item) => item.stock_flag === "OVERSTOCK"
  ).length;
  const trendingUpCount = items.filter(
    (item) => item.trend_classification === "Trending Up"
  ).length;
  const manualReviewCount = items.filter((item) =>
    Boolean(item.manual_review_required)
  ).length;

  const stockFlagData = [
    { name: "Critical", value: criticalCount },
    { name: "Low Stock", value: lowStockCount },
    {
      name: "Sufficient",
      value: items.filter((item) => item.stock_flag === "SUFFICIENT").length,
    },
    { name: "Overstock", value: overstockCount },
  ];

  const trendDistributionData = [
    {
      name: "Trending Up",
      value: items.filter((item) => item.trend_classification === "Trending Up")
        .length,
    },
    {
      name: "Stable",
      value: items.filter((item) => item.trend_classification === "Stable")
        .length,
    },
    {
      name: "Trending Down",
      value: items.filter((item) => item.trend_classification === "Trending Down")
        .length,
    },
  ];

  const categoryHealthData = categoryItems.map((item) => ({
    name: item.category_label || item.category_slug,
    critical: item.critical_count,
    low_stock: item.low_stock_count,
    trending_up: item.trending_up_count,
  }));

  const stockThresholdChartData = [...items]
    .map((item) => ({
      name: item.title.length > 18 ? `${item.title.slice(0, 18)}...` : item.title,
      current_quantity: Number(item.current_quantity ?? 0),
      threshold_units: Number(item.threshold_units ?? 0),
      pressure_gap:
        Number(item.threshold_units ?? 0) - Number(item.current_quantity ?? 0),
    }))
    .sort((a, b) => b.pressure_gap - a.pressure_gap)
    .slice(0, 12)
    .map(({ name, current_quantity, threshold_units }) => ({
      name,
      current_quantity,
      threshold_units,
    }));

  const confidenceBandData = [
    {
      name: "0-40",
      value: items.filter((item) => Number(item.confidence_pct ?? 0) < 40).length,
    },
    {
      name: "40-60",
      value: items.filter((item) => {
        const c = Number(item.confidence_pct ?? 0);
        return c >= 40 && c < 60;
      }).length,
    },
    {
      name: "60-80",
      value: items.filter((item) => {
        const c = Number(item.confidence_pct ?? 0);
        return c >= 60 && c < 80;
      }).length,
    },
    {
      name: "80-100",
      value: items.filter((item) => Number(item.confidence_pct ?? 0) >= 80)
        .length,
    },
  ];

  const currentFilters = {
    categorySlug,
    trendClassification,
    stockFlag,
    manualReviewRequired,
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 xl:grid-cols-[1.3fr_0.7fr]">
        <Card className="rounded-3xl">
          <CardContent className="p-6">
            <div className="space-y-3">
              <div className="text-sm font-medium text-muted-foreground">
                Analyst monitoring workspace
              </div>
              <div>
                <h1 className="text-3xl font-semibold tracking-tight">
                  Monitoring
                </h1>
                <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
                  Explore products outside the urgent top-5 view, inspect stock
                  and demand signals, and monitor operational health without a cluttered layout.
                </p>
              </div>

              <div className="flex flex-wrap gap-3 pt-2">
                <Link
                  href="/"
                  className="inline-flex rounded-2xl border px-4 py-2.5 text-sm font-medium transition hover:bg-muted/40"
                >
                  Open Dashboard
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
              <div className="text-sm text-muted-foreground">
                Monitoring Products
              </div>
              <div className="mt-2 text-3xl font-semibold">{items.length}</div>
              <div className="mt-2 text-xs text-muted-foreground">
                Products currently visible in this filtered monitoring view.
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-3xl">
            <CardContent className="p-5">
              <div className="text-sm text-muted-foreground">Active Alerts</div>
              <div className="mt-2 text-3xl font-semibold">
                {alertItems.length}
              </div>
              <div className="mt-2 text-xs text-muted-foreground">
                Full alert details are tucked into a dropdown below.
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-7">
        <MetricCard title="Critical" value={criticalCount} />
        <MetricCard title="Low Stock" value={lowStockCount} />
        <MetricCard title="Overstock" value={overstockCount} />
        <MetricCard title="Trending Up" value={trendingUpCount} />
        <MetricCard title="Manual Review" value={manualReviewCount} />
        <MetricCard title="Healthy Sources" value={healthyCount} />
        <MetricCard title="Stale Sources" value={staleCount} />
      </div>

      <Card className="rounded-3xl">
        <CardHeader>
          <CardTitle>Filters</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="space-y-2">
            <div className="text-sm font-medium">Category</div>
            <div className="flex flex-wrap gap-2">
              <Link
                href={buildFilterHref(currentFilters, { categorySlug: "" })}
                className={`rounded-full border px-3 py-1.5 text-sm ${
                  !categorySlug ? "bg-muted" : "hover:bg-muted/40"
                }`}
              >
                All
              </Link>
              {categoryItems.map((item) => (
                <Link
                  key={item.category_slug}
                  href={buildFilterHref(currentFilters, {
                    categorySlug: item.category_slug,
                  })}
                  className={`rounded-full border px-3 py-1.5 text-sm ${
                    categorySlug === item.category_slug
                      ? "bg-muted"
                      : "hover:bg-muted/40"
                  }`}
                >
                  {item.category_label || item.category_slug}
                </Link>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">Stock Flag</div>
            <div className="flex flex-wrap gap-2">
              {["", "CRITICAL", "LOW STOCK", "SUFFICIENT", "OVERSTOCK"].map(
                (value) => (
                  <Link
                    key={value || "all-stock"}
                    href={buildFilterHref(currentFilters, { stockFlag: value })}
                    className={`rounded-full border px-3 py-1.5 text-sm ${
                      stockFlag === value ? "bg-muted" : "hover:bg-muted/40"
                    }`}
                  >
                    {value || "All"}
                  </Link>
                )
              )}
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">Trend</div>
            <div className="flex flex-wrap gap-2">
              {["", "Trending Up", "Stable", "Trending Down"].map((value) => (
                <Link
                  key={value || "all-trend"}
                  href={buildFilterHref(currentFilters, {
                    trendClassification: value,
                  })}
                  className={`rounded-full border px-3 py-1.5 text-sm ${
                    trendClassification === value
                      ? "bg-muted"
                      : "hover:bg-muted/40"
                  }`}
                >
                  {value || "All"}
                </Link>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">Manual Review</div>
            <div className="flex flex-wrap gap-2">
              {[
                { label: "All", value: "" },
                { label: "Required", value: "true" },
                { label: "Not Required", value: "false" },
              ].map((option) => (
                <Link
                  key={option.label}
                  href={buildFilterHref(currentFilters, {
                    manualReviewRequired: option.value,
                  })}
                  className={`rounded-full border px-3 py-1.5 text-sm ${
                    manualReviewRequired === option.value
                      ? "bg-muted"
                      : "hover:bg-muted/40"
                  }`}
                >
                  {option.label}
                </Link>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

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
                  No alerts are active right now.
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

      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="rounded-3xl">
          <CardHeader>
            <CardTitle>Stock Flag Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <DistributionDonutChart
              data={stockFlagData}
              emptyTitle="No stock flag data available."
            />
          </CardContent>
        </Card>

        <Card className="rounded-3xl">
          <CardHeader>
            <CardTitle>Trend Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <BarMetricChart
              data={trendDistributionData}
              xKey="name"
              barKey="value"
              emptyTitle="No trend distribution available"
              emptyDescription="Trend categories will appear after analysis is generated."
            />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="rounded-3xl">
          <CardHeader>
            <CardTitle>Category Health Overview</CardTitle>
          </CardHeader>
          <CardContent>
            <CategoryHealthChart data={categoryHealthData} />
          </CardContent>
        </Card>

        <Card className="rounded-3xl">
          <CardHeader>
            <CardTitle>Confidence Band Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <BarMetricChart
              data={confidenceBandData}
              xKey="name"
              barKey="value"
              emptyTitle="No confidence distribution available"
              emptyDescription="Confidence bands will appear after product analysis is available."
            />
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-3xl">
        <CardHeader>
          <CardTitle>Current Stock vs Threshold</CardTitle>
        </CardHeader>
        <CardContent>
          <StockThresholdLineChart data={stockThresholdChartData} />
        </CardContent>
      </Card>

      <Card className="rounded-3xl">
        <CardHeader>
          <CardTitle>Source Health Overview</CardTitle>
        </CardHeader>
        <CardContent>
          {sourceItems.length === 0 ? (
            <div className="text-sm text-muted-foreground">
              No source health data is available yet.
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-4">
                <MetricCard title="Tracked Sources" value={sourceItems.length} />
                <MetricCard title="Healthy" value={healthyCount} />
                <MetricCard title="Warnings" value={warningCount} />
                <MetricCard title="Stale" value={staleCount} />
              </div>

              <details className="group rounded-2xl border bg-background p-4">
                <summary className="cursor-pointer list-none text-sm font-medium">
                  <span className="flex items-center justify-between">
                    <span>View source details</span>
                    <span className="text-xs text-muted-foreground group-open:hidden">
                      Expand
                    </span>
                    <span className="hidden text-xs text-muted-foreground group-open:inline">
                      Collapse
                    </span>
                  </span>
                </summary>

                <div className="mt-4 grid gap-4 xl:grid-cols-2">
                  {sourceItems.map((item, idx) => (
                    <SourceHealthCard
                      key={`${item.source_name}-${idx}`}
                      item={item}
                    />
                  ))}
                </div>
              </details>
            </div>
          )}
        </CardContent>
      </Card>

      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold">Monitoring Products</h2>
          <p className="text-sm text-muted-foreground">
            Detailed products outside the urgent dashboard view.
          </p>
        </div>

        {items.length === 0 ? (
          <Card className="rounded-3xl">
            <CardContent className="py-10 text-sm text-muted-foreground">
              No monitoring products match the selected filters.
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
            {items.map((item) => (
              <Card key={item.product_id} className="rounded-3xl">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <h3 className="line-clamp-2 text-base font-semibold">
                        {item.title}
                      </h3>
                      <div className="text-sm text-muted-foreground">
                        {item.category_label ||
                          item.category_slug ||
                          "Unknown Category"}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {item.product_id}
                      </div>
                    </div>

                    <div
                      className={`text-sm font-semibold ${confidenceClasses(
                        Number(item.confidence_pct ?? 0)
                      )}`}
                    >
                      {Number(item.confidence_pct ?? 0).toFixed(0)}%
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <span
                      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${stockFlagClasses(
                        item.stock_flag
                      )}`}
                    >
                      {item.stock_flag}
                    </span>
                    <span
                      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${trendClasses(
                        item.trend_classification
                      )}`}
                    >
                      {item.trend_classification}
                    </span>
                    {item.manual_review_required ? (
                      <span className="inline-flex rounded-full border border-red-200 bg-red-50 px-2.5 py-1 text-xs font-medium text-red-700">
                        Manual Review
                      </span>
                    ) : null}
                  </div>

                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <ProductMetric
                      label="Current Stock"
                      value={Number(item.current_quantity ?? 0).toFixed(0)}
                    />
                    <ProductMetric
                      label="Threshold"
                      value={Number(item.threshold_units ?? 0).toFixed(0)}
                    />
                    <ProductMetric
                      label="Weekly Demand"
                      value={Number(item.projected_weekly_demand ?? 0).toFixed(1)}
                    />
                    <ProductMetric
                      label="Recommended Order"
                      value={Number(item.recommended_order_qty ?? 0).toFixed(0)}
                    />
                  </div>

                  <div className="mt-4 rounded-2xl border bg-muted/20 p-3">
                    <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                      Executive Summary
                    </div>
                    <p className="mt-1 line-clamp-4 text-sm text-muted-foreground">
                      {item.executive_summary ||
                        "No executive summary available."}
                    </p>
                  </div>

                  <div className="mt-4">
                    <Link
                      href={`/products/${item.product_id}`}
                      className="inline-flex rounded-2xl border px-4 py-2 text-sm font-medium transition hover:bg-muted/40"
                    >
                      Open Analysis
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}