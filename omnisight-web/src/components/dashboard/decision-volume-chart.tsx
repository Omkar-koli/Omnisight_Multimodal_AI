"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { EmptyState } from "./empty-state";

export function DecisionVolumeChart({
  data = [],
}: {
  data?: { date: string; decision_count: number; review_count: number }[];
}) {
  const hasData = data.some(
    (d) => Number(d?.decision_count ?? 0) > 0 || Number(d?.review_count ?? 0) > 0
  );

  if (!hasData) {
    return (
      <EmptyState
        title="No time-series activity yet"
        description="Open product pages and save reviews to populate decision and review trends."
      />
    );
  }

  return (
    <div className="h-[320px] w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Line type="monotone" dataKey="decision_count" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="review_count" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}