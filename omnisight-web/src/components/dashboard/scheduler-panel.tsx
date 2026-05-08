"use client";

import { useState } from "react";
import { EmptyState } from "./empty-state";

type Job = {
  job_id: string;
  name: string;
  next_run_time: string;
  trigger: string;
  paused: boolean;
};

export function SchedulerPanel({
  running,
  timezone,
  jobs = [],
}: {
  running: boolean;
  timezone: string;
  jobs?: Job[];
}) {
  const [message, setMessage] = useState("");
  const [loadingJob, setLoadingJob] = useState("");

  async function postAction(url: string, label: string) {
    try {
      setLoadingJob(label);
      setMessage("");

      const res = await fetch(url, { method: "POST" });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(JSON.stringify(data));
      }

      setMessage(data?.message || "Action completed.");
      window.location.reload();
    } catch (error: any) {
      setMessage(String(error?.message || error));
    } finally {
      setLoadingJob("");
    }
  }

  if (!jobs.length) {
    return (
      <EmptyState
        title="No scheduler jobs found"
        description="The background scheduler has not registered any jobs yet."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border p-4">
        <div className="text-base font-medium">Scheduler Status</div>
        <div className="mt-2 text-sm text-muted-foreground">
          Running: {running ? "Yes" : "No"} · Timezone: {timezone}
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-left">
            <tr>
              <th className="px-4 py-3">Job</th>
              <th className="px-4 py-3">Next Run</th>
              <th className="px-4 py-3">Trigger</th>
              <th className="px-4 py-3">Paused</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.job_id} className="border-t">
                <td className="px-4 py-3">{job.name}</td>
                <td className="px-4 py-3">{job.next_run_time || "-"}</td>
                <td className="px-4 py-3">{job.trigger}</td>
                <td className="px-4 py-3">{job.paused ? "Yes" : "No"}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() =>
                        postAction(`/api/jobs/scheduler/run-now/${job.job_id}`, `run-${job.job_id}`)
                      }
                      disabled={loadingJob === `run-${job.job_id}`}
                      className="rounded border px-2 py-1 text-xs hover:bg-muted"
                    >
                      Run now
                    </button>

                    {job.paused ? (
                      <button
                        onClick={() =>
                          postAction(`/api/jobs/scheduler/resume/${job.job_id}`, `resume-${job.job_id}`)
                        }
                        disabled={loadingJob === `resume-${job.job_id}`}
                        className="rounded border px-2 py-1 text-xs hover:bg-muted"
                      >
                        Resume
                      </button>
                    ) : (
                      <button
                        onClick={() =>
                          postAction(`/api/jobs/scheduler/pause/${job.job_id}`, `pause-${job.job_id}`)
                        }
                        disabled={loadingJob === `pause-${job.job_id}`}
                        className="rounded border px-2 py-1 text-xs hover:bg-muted"
                      >
                        Pause
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {message ? <div className="text-sm text-muted-foreground">{message}</div> : null}
    </div>
  );
}