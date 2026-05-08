import Link from "next/link";
import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { fastapiGet } from "@/lib/server-api";
import { Card, CardContent } from "@/components/ui/card";
import { ChevronRight, Search, ArrowRight } from "lucide-react";

type QueueItem = {
  product_id: string;
  title: string;
  category?: string;
  current_inventory?: number;
  weekly_units_sold?: number;
  days_to_stockout?: number;
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

function getSingleParam(value: string | string[] | undefined, fallback = ""): string {
  if (Array.isArray(value)) return value[0] ?? fallback;
  return value ?? fallback;
}

function actionPill(action: string) {
  if (action === "RESTOCK_NOW")
    return "bg-destructive/10 text-destructive border-destructive/30";
  if (action === "RESTOCK_CAUTIOUSLY")
    return "bg-primary/10 text-primary border-primary/30";
  if (action === "SLOW_REPLENISHMENT" || action === "HOLD")
    return "bg-muted text-muted-foreground border-border";
  if (action === "CHECK_QUALITY_BEFORE_RESTOCK")
    return "bg-accent text-accent-foreground border-border";
  return "bg-muted/60 text-muted-foreground border-border";
}

function confidenceClasses(c: number) {
  if (c < 0.4) return "text-destructive";
  if (c < 0.7) return "text-primary";
  return "text-emerald-600 dark:text-emerald-400";
}

function normalizeAction(a?: string) {
  return (a || "MONITOR").replaceAll("_", " ");
}

function buildQueueQuery(p: {
  action?: string;
  search?: string;
  limit?: number;
}) {
  const sp = new URLSearchParams();
  if (p.action) sp.set("action", p.action);
  if (p.search) sp.set("search", p.search);
  sp.set("limit", String(p.limit ?? 500));
  return `/products/queue?${sp.toString()}`;
}

export default async function ProductsPage({
  searchParams,
}: {
  searchParams?: Promise<{
    action?: string | string[];
    search?: string | string[];
  }>;
}) {
  const session = await auth();
  if (!session?.user) redirect("/login");

  const resolvedSearchParams = await searchParams;
  const action = getSingleParam(resolvedSearchParams?.action);
  const search = getSingleParam(resolvedSearchParams?.search).trim();

  const [queue, categories] = await Promise.all([
    fastapiGet(buildQueueQuery({ action, search, limit: 500 })),
    fastapiGet("/categories/summary"),
  ]);

  const items: QueueItem[] = queue?.items ?? [];
  const categoryItems: CategorySummaryItem[] = categories?.items ?? [];

  // Action filter chips
  const actionOptions = [
    { label: "All", value: "" },
    { label: "Restock Now", value: "RESTOCK_NOW" },
    { label: "Cautious", value: "RESTOCK_CAUTIOUSLY" },
    { label: "Monitor", value: "MONITOR" },
    { label: "Hold", value: "HOLD" },
  ];

  return (
    <div className="space-y-6">
      {/* ── Slim header ── */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Products</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Browse by category or search across the catalog.
          </p>
        </div>
      </div>

      {/* ── Search bar ── */}
      <Card className="rounded-xl">
        <CardContent className="px-4 py-3">
          <form action="/products" method="GET" className="flex flex-col gap-2 md:flex-row">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                name="search"
                defaultValue={search}
                placeholder="Search by product title or ID…"
                className="w-full rounded-md border bg-background px-9 py-2 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
            </div>
            <div className="flex gap-2">
              {action ? <input type="hidden" name="action" value={action} /> : null}
              <button
                type="submit"
                className="rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background transition hover:opacity-90"
              >
                Search
              </button>
              {(search || action) ? (
                <Link
                  href="/products"
                  className="rounded-md border bg-card px-4 py-2 text-sm font-medium transition hover:bg-muted/50"
                >
                  Reset
                </Link>
              ) : null}
            </div>
          </form>
        </CardContent>
      </Card>

      {/* ── Categories — the primary navigation ── */}
      <section>
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-base font-semibold">Browse by Category</h2>
          <span className="text-xs text-muted-foreground">
            {categoryItems.length} categor{categoryItems.length === 1 ? "y" : "ies"}
          </span>
        </div>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {categoryItems.map((c) => (
            <Link
              key={c.category_slug}
              href={`/products/category/${c.category_slug}`}
              className="group rounded-xl border bg-card p-5 transition hover:border-foreground/30 hover:shadow-sm"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                    Category
                  </div>
                  <div className="mt-1 text-lg font-semibold">
                    {c.category_label || c.category_slug}
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
              </div>

              <div className="mt-4 grid grid-cols-4 gap-2 text-center">
                <div>
                  <div className="text-lg font-semibold tabular-nums">
                    {c.total_products}
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Total
                  </div>
                </div>
                <div>
                  <div className="text-lg font-semibold tabular-nums text-destructive">
                    {c.critical_count}
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Critical
                  </div>
                </div>
                <div>
                  <div className="text-lg font-semibold tabular-nums text-primary">
                    {c.low_stock_count}
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Low
                  </div>
                </div>
                <div>
                  <div className="text-lg font-semibold tabular-nums">
                    {c.trending_up_count}
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                    Up
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ── Search results / action-filtered list (only show if user is searching) ── */}
      {(search || action) ? (
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold">
              {search ? `Results for “${search}”` : "Filtered Products"}
            </h2>
            <div className="flex gap-1.5">
              {actionOptions.map((opt) => {
                const params = new URLSearchParams();
                if (search) params.set("search", search);
                if (opt.value) params.set("action", opt.value);
                const href = params.toString() ? `/products?${params.toString()}` : "/products";
                const isActive = action === opt.value;
                return (
                  <Link
                    key={opt.value || "all"}
                    href={href}
                    className={`rounded-full border px-2.5 py-1 text-[11px] font-medium transition ${
                      isActive
                        ? "border-foreground bg-foreground text-background"
                        : "border-border text-muted-foreground hover:border-foreground/30 hover:text-foreground"
                    }`}
                  >
                    {opt.label}
                  </Link>
                );
              })}
            </div>
          </div>

          <Card className="rounded-xl">
            <CardContent className="p-5">
              {items.length === 0 ? (
                <div className="rounded-md border border-dashed py-10 text-center text-sm text-muted-foreground">
                  No products match.
                </div>
              ) : (
                <div className="divide-y">
                  {items.slice(0, 50).map((item) => (
                    <Link
                      key={item.product_id}
                      href={`/products/${item.product_id}`}
                      className="group flex items-center gap-4 py-3 transition hover:bg-muted/30"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-medium">
                          {item.title}
                        </div>
                        <div className="mt-0.5 text-xs text-muted-foreground">
                          {item.category || "—"} · {item.product_id}
                        </div>
                      </div>

                      <span
                        className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${actionPill(
                          item.action || "MONITOR"
                        )}`}
                      >
                        {normalizeAction(item.action)}
                      </span>

                      <div className="hidden md:block w-20 text-right">
                        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                          Stock
                        </div>
                        <div className="text-sm font-semibold tabular-nums">
                          {Number(item.current_inventory ?? 0).toFixed(0)}
                        </div>
                      </div>

                      <div className="w-20 text-right">
                        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                          Confidence
                        </div>
                        <div
                          className={`text-sm font-semibold tabular-nums ${confidenceClasses(
                            Number(item.confidence ?? 0)
                          )}`}
                        >
                          {(Number(item.confidence ?? 0) * 100).toFixed(0)}%
                        </div>
                      </div>

                      <ChevronRight className="hidden h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 sm:block" />
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </section>
      ) : null}
    </div>
  );
}
