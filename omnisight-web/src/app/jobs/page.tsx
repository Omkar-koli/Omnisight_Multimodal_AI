import { auth } from "@/auth";
import { redirect } from "next/navigation";
import { fastapiGet } from "@/lib/server-api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FreshnessTable } from "@/components/dashboard/freshness-table";
import { JobRunsTable } from "@/components/dashboard/job-runs-table";
import { JobTriggerPanel } from "@/components/dashboard/job-trigger-panel";
import { SchedulerPanel } from "@/components/dashboard/scheduler-panel";

export default async function JobsPage() {
  const session = await auth();

  if (!session?.user) {
    redirect("/login");
  }

  const [freshness, runs, scheduler] = await Promise.all([
    fastapiGet("/freshness/summary"),
    fastapiGet("/jobs/runs"),
    fastapiGet("/jobs/scheduler/status"),
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold">Jobs & Freshness</h2>
        <p className="text-sm text-muted-foreground">
          Refresh status, job history, dataset freshness, and background scheduler controls.
        </p>
      </div>

      <JobTriggerPanel />

      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle>Scheduler</CardTitle>
        </CardHeader>
        <CardContent>
          <SchedulerPanel
            running={scheduler?.running ?? false}
            timezone={scheduler?.timezone ?? "UTC"}
            jobs={scheduler?.jobs ?? []}
          />
        </CardContent>
      </Card>

      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle>Dataset Freshness</CardTitle>
        </CardHeader>
        <CardContent>
          <FreshnessTable items={freshness?.items ?? []} />
        </CardContent>
      </Card>

      <Card className="rounded-2xl">
        <CardHeader>
          <CardTitle>Recent Job Runs</CardTitle>
        </CardHeader>
        <CardContent>
          <JobRunsTable items={runs?.items ?? []} />
        </CardContent>
      </Card>
    </div>
  );
}