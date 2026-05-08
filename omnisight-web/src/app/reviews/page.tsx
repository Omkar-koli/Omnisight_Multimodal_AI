import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { canReview } from "@/lib/roles";
import { fastapiGet } from "@/lib/server-api";
import { MetricCard } from "@/components/dashboard/metric-card";
import { ReviewOpsTable } from "@/components/dashboard/review-ops-table";
import { SystemStatusCard } from "@/components/dashboard/system-status-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default async function ReviewsPage() {
  const session = await auth();
  const role = session?.user?.role || "viewer";

  if (!session?.user) {
    redirect("/login");
  }

  if (!canReview(role)) {
    redirect("/unauthorized");
  }

  const [queue, stats, systemStatus] = await Promise.all([
    fastapiGet("/reviews/queue?limit=200"),
    fastapiGet("/dashboard/review-stats"),
    fastapiGet("/system/status"),
  ]);

  const exportUrl = "/api/reviews/export";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Review Operations</h2>
          <p className="text-sm text-muted-foreground">
            Audit trail, reviewer actions, and export controls.
          </p>
        </div>

        <a
          href={exportUrl}
          className="rounded-lg border px-4 py-2 text-sm hover:bg-muted"
        >
          Export CSV
        </a>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard title="Total Reviews" value={stats?.total_reviews ?? 0} />
        <MetricCard title="Approved" value={stats?.approved_count ?? 0} />
        <MetricCard title="Rejected" value={stats?.rejected_count ?? 0} />
        <MetricCard title="Deferred" value={stats?.deferred_count ?? 0} />
      </div>

      <SystemStatusCard status={systemStatus} />

      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle>Review Queue</CardTitle>
        </CardHeader>
        <CardContent>
          <ReviewOpsTable items={queue?.items ?? []} />
        </CardContent>
      </Card>
    </div>
  );
}