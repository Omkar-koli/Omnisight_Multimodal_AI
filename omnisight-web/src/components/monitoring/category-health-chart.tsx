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
      <div className="text-sm text-muted-foreground">
        No category chart data available.
      </div>
    );
  }

  return (
    <div className="h-[340px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 12, right: 16, left: 0, bottom: 16 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="name"
            angle={-15}
            textAnchor="end"
            height={60}
            interval={0}
          />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="critical" stackId="a" fill="#ef4444" name="Critical" />
          <Bar dataKey="low_stock" stackId="a" fill="#f59e0b" name="Low Stock" />
          <Bar dataKey="trending_up" stackId="a" fill="#3b82f6" name="Trending Up" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}