import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { auth } from "@/auth";
import { fastapiGet } from "@/lib/server-api";
import { MetricCard } from "@/components/dashboard/metric-card";
import { Card, CardContent } from "@/components/ui/card";
import { BarMetricChart } from "@/components/dashboard/bar-metric-chart";
import { DistributionDonutChart } from "@/components/monitoring/distribution-donut-chart";
import { StockThresholdLineChart } from "@/components/monitoring/stock-threshold-line-chart";
import {
  ChevronRight,
  ChevronLeft,
  AlertTriangle,
  TrendingUp,
} from "lucide-react";

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

export default async function CategoryDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const session = await auth();
  if (!session?.user) redirect("/login");

  const { slug } = await params;

  const [categories, products, allAlerts] = await Promise.all([
    fastapiGet("/categories/summary"),
    fastapiGet(
      `/monitoring/products?category_slug=${encodeURIComponent(slug)}&limit=500`
    ),
    fastapiGet("/alerts/list?limit=50"),
  ]);

  const categoryItems: CategorySummaryItem[] = categories?.items ?? [];
  const category = categoryItems.find((c) => c.category_slug === slug);

  if (!category) {
    notFound();
  }

  const items: MonitoringProductItem[] = products?.items ?? [];
  const alertItems: AlertItem[] = (allAlerts?.items ?? []).filter(
    (a: AlertItem) => a.category_slug === slug
  );

  // ── Aggregations (for THIS category only)
  const criticalCount = items.filter((i) => i.stock_flag === "CRITICAL").length;
  const lowStockCount = items.filter((i) => i.stock_flag === "LOW STOCK").length;
  const overstockCount = items.filter((i) => i.stock_flag === "OVERSTOCK").length;
  const trendingUpCount = items.filter(
    (i) => i.trend_classification === "Trending Up"
  ).length;
  const manualReviewCount = items.filter((i) => Boolean(i.manual_review_required)).length;

  const criticalAlerts = alertItems.filter((a) => a.severity === "critical").length;

  const stockFlagData = [
    { name: "Critical", value: criticalCount },
    { name: "Low Stock", value: lowStockCount },
    {
      name: "Sufficient",
      value: items.filter((i) => i.stock_flag === "SUFFICIENT").length,
    },
    { name: "Overstock", value: overstockCount },
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

  return (
    <div className="space-y-6">
      {/* ── Breadcrumb + header ── */}
      <div>
        <nav className="mb-3 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Link href="/products" className="transition hover:text-foreground">
            Products
          </Link>
          <ChevronRight className="h-3 w-3" />
          <span className="text-foreground">
            {category.category_label || category.category_slug}
          </span>
        </nav>

        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <Link
              href="/products"
              className="mb-2 inline-flex items-center gap-1 text-xs text-muted-foreground transition hover:text-foreground"
            >
              <ChevronLeft className="h-3 w-3" /> All categories
            </Link>
            <h1 className="text-2xl font-semibold tracking-tight">
              {category.category_label || category.category_slug}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {category.total_products} product
              {category.total_products === 1 ? "" : "s"} in this category.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <Link
              href={`/monitoring?category_slug=${encodeURIComponent(slug)}`}
              className="rounded-md border bg-card px-3.5 py-2 text-sm font-medium transition hover:bg-muted/50"
            >
              View in Monitoring
            </Link>
          </div>
        </div>
      </div>

      {/* ── KPIs (5 metrics for this category) ── */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <MetricCard
          title="Total"
          value={category.total_products}
          subtitle="products"
          accent
        />
        <MetricCard
          title="Critical"
          value={category.critical_count}
          subtitle="immediate"
        />
        <MetricCard
          title="Low Stock"
          value={category.low_stock_count}
          subtitle="watching"
        />
        <MetricCard
          title="Trending Up"
          value={category.trending_up_count}
          subtitle="rising"
        />
        <MetricCard
          title="Manual Review"
          value={manualReviewCount}
          subtitle="needs analyst"
        />
      </div>

      {/* ── Alert strip (only this category) ── */}
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
                    {alertItems.length} alert
                    {alertItems.length === 1 ? "" : "s"} in this category
                    {criticalAlerts > 0 ? (
                      <span className="ml-2 inline-flex rounded-full border border-destructive/30 bg-destructive/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-destructive">
                        {criticalAlerts} critical
                      </span>
                    ) : null}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Tap to expand
                  </div>
                </div>
              </div>
              <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform group-open:rotate-90" />
            </summary>

            <div className="border-t px-5 py-4 space-y-2">
              {alertItems.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  No alerts active for this category.
                </div>
              ) : (
                alertItems.slice(0, 8).map((a) => (
                  <div
                    key={a.alert_id}
                    className="flex items-start justify-between gap-3 rounded-md border bg-background px-3 py-2.5"
                  >
                    <div className="min-w-0 flex-1 space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${alertPill(
                            a.severity
                          )}`}
                        >
                          {a.severity}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {a.alert_type.replaceAll("_", " ")}
                        </span>
                      </div>
                      <div className="truncate text-sm font-medium">
                        {a.title}
                      </div>
                      <div className="text-xs text-muted-foreground line-clamp-1">
                        {a.message}
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

      {/* ── Charts row 1: stock distribution + trend distribution ── */}
      <div className="grid gap-3 lg:grid-cols-2">
        <Card className="rounded-xl">
          <CardContent className="p-5">
            <div className="mb-3">
              <h3 className="text-sm font-semibold">Stock Flag Distribution</h3>
              <p className="text-xs text-muted-foreground">
                Where pressure sits in this category
              </p>
            </div>
            <DistributionDonutChart
              data={stockFlagData}
              emptyTitle="No stock flag data for this category."
            />
          </CardContent>
        </Card>

        <Card className="rounded-xl">
          <CardContent className="p-5">
            <div className="mb-3">
              <h3 className="text-sm font-semibold">Trend Distribution</h3>
              <p className="text-xs text-muted-foreground">
                Demand direction for this category
              </p>
            </div>
            <BarMetricChart
              data={trendDistributionData}
              xKey="name"
              barKey="value"
              emptyTitle="No trend data"
              emptyDescription="Trend categories appear after analysis runs."
            />
          </CardContent>
        </Card>
      </div>

      {/* ── Top pressure chart ── */}
      <Card className="rounded-xl">
        <CardContent className="p-5">
          <div className="mb-3">
            <h3 className="text-sm font-semibold">
              Top Pressure: Stock vs Threshold
            </h3>
            <p className="text-xs text-muted-foreground">
              The 10 products with the largest gap between current stock and threshold
            </p>
          </div>
          <StockThresholdLineChart data={stockThresholdChartData} />
        </CardContent>
      </Card>

      {/* ── Products list for this category ── */}
      <Card className="rounded-xl">
        <CardContent className="p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold">Products</h2>
              <p className="text-xs text-muted-foreground">
                {items.length} product{items.length === 1 ? "" : "s"}
              </p>
            </div>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </div>

          {items.length === 0 ? (
            <div className="rounded-md border border-dashed py-10 text-center text-sm text-muted-foreground">
              No products in this category yet.
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

                  <div className="hidden md:block w-20 text-right">
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
