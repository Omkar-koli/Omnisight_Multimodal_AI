"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { EmptyState } from "./empty-state";

export function BarMetricChart({
  data = [],
  xKey,
  barKey,
  emptyTitle,
  emptyDescription,
}: {
  data?: Record<string, any>[];
  xKey: string;
  barKey: string;
  emptyTitle: string;
  emptyDescription: string;
}) {
  const hasData = data.some((d) => Number(d?.[barKey] ?? 0) > 0);

  if (!hasData) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <div className="h-[320px] w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Bar dataKey={barKey} radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}