"use client";

import { useState } from "react";

export function JobTriggerPanel() {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function runAllJobs() {
    try {
      setLoading(true);
      setMessage("");

      const res = await fetch("/api/jobs/run/all", {
        method: "POST",
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(JSON.stringify(data));
      }

      setMessage("Refresh jobs completed.");
      window.location.reload();
    } catch (error: any) {
      setMessage(String(error?.message || error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-2xl border p-4">
      <div className="mb-3 text-base font-medium">Manual Refresh Jobs</div>
      <button
        onClick={runAllJobs}
        disabled={loading}
        className="rounded-lg border px-4 py-2 text-sm hover:bg-muted disabled:opacity-50"
      >
        {loading ? "Running..." : "Run All Refresh Jobs"}
      </button>

      {message ? (
        <div className="mt-3 text-sm text-muted-foreground">{message}</div>
      ) : null}
    </div>
  );
}