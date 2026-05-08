import Link from "next/link";
import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { fastapiGet } from "@/lib/server-api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type QueueItem = {
  product_id: string;
  title: string;
  category?: string;
  current_inventory?: number;
  weekly_units_sold?: number;
  days_to_stockout?: number;
  stockout_risk_score?: number;
  overstock_risk_score?: number;
  review_risk_score?: number;
  trend_strength_score?: number;
  action?: string;
  confidence?: number;
  evidence_summary?: string;
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

function getSingleParam(
  value: string | string[] | undefined,
  fallback = ""
): string {
  if (Array.isArray(value)) return value[0] ?? fallback;
  return value ?? fallback;
}

function actionClasses(action: string) {
  if (action === "RESTOCK_NOW") {
    return "bg-red-100 text-red-800 border border-red-200";
  }
  if (action === "RESTOCK_CAUTIOUSLY") {
    return "bg-amber-100 text-amber-800 border border-amber-200";
  }
  if (action === "SLOW_REPLENISHMENT") {
    return "bg-slate-100 text-slate-800 border border-slate-200";
  }
  if (action === "HOLD") {
    return "bg-zinc-100 text-zinc-800 border border-zinc-200";
  }
  if (action === "CHECK_QUALITY_BEFORE_RESTOCK") {
    return "bg-purple-100 text-purple-800 border border-purple-200";
  }
  return "bg-blue-100 text-blue-800 border border-blue-200";
}

function confidenceClasses(confidence: number) {
  if (confidence < 0.4) return "text-red-700";
  if (confidence < 0.7) return "text-amber-700";
  return "text-emerald-700";
}

function normalizeActionLabel(action?: string) {
  return (action || "MONITOR").replaceAll("_", " ");
}

function buildQueueQuery(params: {
  categorySlug?: string;
  action?: string;
  search?: string;
  limit?: number;
}) {
  const sp = new URLSearchParams();

  if (params.categorySlug) sp.set("category_slug", params.categorySlug);
  if (params.action) sp.set("action", params.action);
  if (params.search) sp.set("search", params.search);
  sp.set("limit", String(params.limit ?? 500));

  return `/products/queue?${sp.toString()}`;
}

function buildFilterHref(
  current: {
    categorySlug: string;
    action: string;
    search: string;
  },
  next: Partial<{
    categorySlug: string;
    action: string;
    search: string;
  }>
) {
  const params = new URLSearchParams();

  const merged = {
    categorySlug: next.categorySlug ?? current.categorySlug,
    action: next.action ?? current.action,
    search: next.search ?? current.search,
  };

  if (merged.categorySlug) params.set("category_slug", merged.categorySlug);
  if (merged.action) params.set("action", merged.action);
  if (merged.search) params.set("search", merged.search);

  const qs = params.toString();
  return qs ? `/products?${qs}` : "/products";
}

function buildCategoryStats(
  categoryItems: CategorySummaryItem[],
  slug: string
): CategorySummaryItem | undefined {
  return categoryItems.find((item) => item.category_slug === slug);
}

function categoryCardClasses(isActive: boolean) {
  return isActive
    ? "border-foreground bg-muted"
    : "border-border bg-background hover:bg-muted/40";
}

function ProductMiniMetric({
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

export default async function ProductsPage({
  searchParams,
}: {
  searchParams?: Promise<{
    category_slug?: string | string[];
    action?: string | string[];
    search?: string | string[];
  }>;
}) {
  const session = await auth();

  if (!session?.user) {
    redirect("/login");
  }

  const resolvedSearchParams = await searchParams;

  const categorySlug = getSingleParam(resolvedSearchParams?.category_slug);
  const action = getSingleParam(resolvedSearchParams?.action);
  const search = getSingleParam(resolvedSearchParams?.search).trim();

  const [queue, categories] = await Promise.all([
    fastapiGet(
      buildQueueQuery({
        categorySlug,
        action,
        search,
        limit: 500,
      })
    ),
    fastapiGet("/categories/summary"),
  ]);

  const items: QueueItem[] = queue?.items ?? [];
  const categoryItems: CategorySummaryItem[] = categories?.items ?? [];

  const grouped = items.reduce<Record<string, QueueItem[]>>((acc, item) => {
    const key = item.category || "Unknown Category";
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});

  const orderedGroups = Object.entries(grouped).sort((a, b) =>
    a[0].localeCompare(b[0])
  );

  const currentFilters = {
    categorySlug,
    action,
    search,
  };

  const visibleCategoryCount = orderedGroups.length;
  const restockNowCount = items.filter(
    (item) => (item.action || "MONITOR") === "RESTOCK_NOW"
  ).length;
  const cautiousCount = items.filter(
    (item) => (item.action || "MONITOR") === "RESTOCK_CAUTIOUSLY"
  ).length;
  const holdSlowCount = items.filter((item) =>
    ["HOLD", "SLOW_REPLENISHMENT"].includes(item.action || "MONITOR")
  ).length;

  const selectedCategoryStats = categorySlug
    ? buildCategoryStats(categoryItems, categorySlug)
    : undefined;

  const actionOptions = [
    { label: "All", value: "" },
    { label: "Restock Now", value: "RESTOCK_NOW" },
    { label: "Restock Cautiously", value: "RESTOCK_CAUTIOUSLY" },
    { label: "Monitor", value: "MONITOR" },
    { label: "Slow Replenishment", value: "SLOW_REPLENISHMENT" },
    { label: "Hold", value: "HOLD" },
    { label: "Check Quality", value: "CHECK_QUALITY_BEFORE_RESTOCK" },
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 xl:grid-cols-[1.3fr_0.7fr]">
        <Card className="rounded-3xl">
          <CardContent className="p-6">
            <div className="space-y-3">
              <div className="text-sm font-medium text-muted-foreground">
                Category-first inventory workspace
              </div>
              <div>
                <h1 className="text-3xl font-semibold tracking-tight">Products</h1>
                <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
                  Browse products by category, search quickly, and jump into the
                  full analysis page without scrolling through one long list.
                </p>
              </div>

              <form
                action="/products"
                method="GET"
                className="grid gap-3 pt-2 md:grid-cols-[1fr_auto]"
              >
                <input
                  type="text"
                  name="search"
                  defaultValue={search}
                  placeholder="Search by product title or product ID"
                  className="rounded-2xl border bg-background px-4 py-3 text-sm outline-none placeholder:text-muted-foreground"
                />
                <div className="flex gap-2">
                  {categorySlug ? (
                    <input type="hidden" name="category_slug" value={categorySlug} />
                  ) : null}
                  {action ? <input type="hidden" name="action" value={action} /> : null}
                  <button
                    type="submit"
                    className="rounded-2xl border px-4 py-3 text-sm font-medium transition hover:bg-muted/40"
                  >
                    Search
                  </button>
                  <Link
                    href="/products"
                    className="rounded-2xl border px-4 py-3 text-sm font-medium transition hover:bg-muted/40"
                  >
                    Reset
                  </Link>
                </div>
              </form>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
          <Card className="rounded-3xl">
            <CardContent className="p-5">
              <div className="text-sm text-muted-foreground">Displayed Products</div>
              <div className="mt-2 text-3xl font-semibold">{items.length}</div>
              <div className="mt-2 text-xs text-muted-foreground">
                Filtered by current search, category, and action selections.
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-3xl">
            <CardContent className="p-5">
              <div className="text-sm text-muted-foreground">Visible Categories</div>
              <div className="mt-2 text-3xl font-semibold">{visibleCategoryCount}</div>
              <div className="mt-2 text-xs text-muted-foreground">
                Categories still visible after applying current filters.
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-4">
        <Card className="rounded-2xl">
          <CardContent className="p-4">
            <div className="text-sm text-muted-foreground">Restock Now</div>
            <div className="mt-1 text-2xl font-semibold">{restockNowCount}</div>
          </CardContent>
        </Card>
        <Card className="rounded-2xl">
          <CardContent className="p-4">
            <div className="text-sm text-muted-foreground">Restock Cautiously</div>
            <div className="mt-1 text-2xl font-semibold">{cautiousCount}</div>
          </CardContent>
        </Card>
        <Card className="rounded-2xl">
          <CardContent className="p-4">
            <div className="text-sm text-muted-foreground">Hold / Slow Signals</div>
            <div className="mt-1 text-2xl font-semibold">{holdSlowCount}</div>
          </CardContent>
        </Card>
        <Card className="rounded-2xl">
          <CardContent className="p-4">
            <div className="text-sm text-muted-foreground">Selected Category</div>
            <div className="mt-1 text-lg font-semibold">
              {selectedCategoryStats?.category_label ||
                selectedCategoryStats?.category_slug ||
                "All Categories"}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-3xl">
        <CardHeader>
          <CardTitle>Browse by Category</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Link
              href={buildFilterHref(currentFilters, { categorySlug: "" })}
              className={`rounded-3xl border p-5 transition ${categoryCardClasses(
                !categorySlug
              )}`}
            >
              <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                All Categories
              </div>
              <div className="mt-2 text-xl font-semibold">Everything</div>
              <div className="mt-3 text-sm text-muted-foreground">
                View all products across categories with current filters applied.
              </div>
            </Link>

            {categoryItems.map((item, index) => (
              <Link
                key={`${item.category_slug}-${item.category_label || "unknown"}-${index}`}
                href={buildFilterHref(currentFilters, {
                  categorySlug: item.category_slug,
                })}
                className={`rounded-3xl border p-5 transition ${categoryCardClasses(
                  categorySlug === item.category_slug
                )}`}
              >
                <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Category
                </div>
                <div className="mt-2 text-xl font-semibold">
                  {item.category_label || item.category_slug}
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-xl bg-muted/50 p-3">
                    <div className="text-xs text-muted-foreground">Products</div>
                    <div className="mt-1 font-semibold">{item.total_products}</div>
                  </div>
                  <div className="rounded-xl bg-muted/50 p-3">
                    <div className="text-xs text-muted-foreground">Trending Up</div>
                    <div className="mt-1 font-semibold">{item.trending_up_count}</div>
                  </div>
                  <div className="rounded-xl bg-muted/50 p-3">
                    <div className="text-xs text-muted-foreground">Critical</div>
                    <div className="mt-1 font-semibold">{item.critical_count}</div>
                  </div>
                  <div className="rounded-xl bg-muted/50 p-3">
                    <div className="text-xs text-muted-foreground">Low Stock</div>
                    <div className="mt-1 font-semibold">{item.low_stock_count}</div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-3xl">
        <CardHeader>
          <CardTitle>Action Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {actionOptions.map((option) => (
              <Link
                key={option.value || "all-actions"}
                href={buildFilterHref(currentFilters, { action: option.value })}
                className={`rounded-full border px-3 py-1.5 text-sm transition ${
                  action === option.value ? "bg-muted" : "hover:bg-muted/40"
                }`}
              >
                {option.label}
              </Link>
            ))}
          </div>
        </CardContent>
      </Card>

      {orderedGroups.length === 0 ? (
        <Card className="rounded-3xl">
          <CardContent className="py-10 text-sm text-muted-foreground">
            No products match the selected filters.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-8">
          {orderedGroups.map(([groupName, groupItems]) => (
            <section key={groupName} className="space-y-4">
              <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
                <div>
                  <h2 className="text-xl font-semibold">{groupName}</h2>
                  <p className="text-sm text-muted-foreground">
                    {groupItems.length} product{groupItems.length === 1 ? "" : "s"} in
                    this view
                  </p>
                </div>
              </div>

              <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
                {groupItems.map((item) => (
                  <Link
                    key={item.product_id}
                    href={`/products/${item.product_id}`}
                    className="block rounded-3xl border bg-background p-5 transition hover:bg-muted/30"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <h3 className="line-clamp-2 text-base font-semibold">
                          {item.title}
                        </h3>
                        <div className="text-xs text-muted-foreground">
                          {item.product_id}
                        </div>
                      </div>

                      <div
                        className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${actionClasses(
                          item.action || "MONITOR"
                        )}`}
                      >
                        {normalizeActionLabel(item.action)}
                      </div>
                    </div>

                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <ProductMiniMetric
                        label="Current Stock"
                        value={Number(item.current_inventory ?? 0).toFixed(0)}
                      />
                      <ProductMiniMetric
                        label="Weekly Demand"
                        value={Number(item.weekly_units_sold ?? 0).toFixed(1)}
                      />
                      <ProductMiniMetric
                        label="Days to Stockout"
                        value={Number(item.days_to_stockout ?? 0).toFixed(1)}
                      />
                      <div className="rounded-xl bg-muted/40 p-3">
                        <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                          Confidence
                        </div>
                        <div
                          className={`mt-1 text-base font-semibold ${confidenceClasses(
                            Number(item.confidence ?? 0)
                          )}`}
                        >
                          {(Number(item.confidence ?? 0) * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 rounded-2xl border bg-muted/20 p-3">
                      <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
                        Summary
                      </div>
                      <p className="mt-1 line-clamp-3 text-sm text-muted-foreground">
                        {item.evidence_summary ||
                          "Open the product page for full analysis."}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}