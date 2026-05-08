"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type CategoryHealthItem = {
  name: string;
  critical: number;
  low_stock: number;
  trending_up: number;
};

export function CategoryHealthChart({
  data,
}: {
  data: CategoryHealthItem[];
}) {
  if (!data.length) {
    return (
      <div className="rounded-md border border-dashed py-10 text-center text-sm text-muted-foreground">
        No category chart data available.
      </div>
    );
  }

  return (
    <div className="h-[320px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 8, right: 12, left: -8, bottom: 16 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--border)"
            vertical={false}
          />
          <XAxis
            dataKey="name"
            angle={-15}
            textAnchor="end"
            height={56}
            interval={0}
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
            stroke="var(--border)"
          />
          <YAxis
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
          <Legend wrapperStyle={{ fontSize: "12px" }} iconType="circle" />
          <Bar
            dataKey="critical"
            stackId="a"
            fill="oklch(0.58 0.22 25)"
            name="Critical"
            radius={[0, 0, 0, 0]}
          />
          <Bar
            dataKey="low_stock"
            stackId="a"
            fill="var(--chart-3)"
            name="Low Stock"
          />
          <Bar
            dataKey="trending_up"
            stackId="a"
            fill="var(--chart-1)"
            name="Trending Up"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
