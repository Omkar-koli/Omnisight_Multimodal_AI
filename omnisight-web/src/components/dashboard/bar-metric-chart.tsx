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
    <div className="h-[300px] w-full min-w-0">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 8, right: 12, left: -8, bottom: 8 }}
        >
          <CartesianGrid
            vertical={false}
            stroke="var(--border)"
            strokeDasharray="3 3"
          />
          <XAxis
            dataKey={xKey}
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            stroke="var(--border)"
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            stroke="var(--border)"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              fontSize: "12px",
            }}
            cursor={{ fill: "var(--muted)" }}
          />
          <Bar
            dataKey={barKey}
            fill="var(--chart-1)"
            radius={[6, 6, 0, 0]}
            maxBarSize={56}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
