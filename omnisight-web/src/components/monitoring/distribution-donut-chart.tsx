"use client";

import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

type ChartItem = {
  name: string;
  value: number;
};

const COLORS = [
  "#ef4444",
  "#f59e0b",
  "#10b981",
  "#3b82f6",
  "#8b5cf6",
  "#6b7280",
];

export function DistributionDonutChart({
  data,
  emptyTitle = "No data available",
}: {
  data: ChartItem[];
  emptyTitle?: string;
}) {
  const cleaned = (data ?? []).filter((item) => Number(item.value) > 0);

  if (cleaned.length === 0) {
    return <div className="text-sm text-muted-foreground">{emptyTitle}</div>;
  }

  return (
    <div className="h-[320px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={cleaned}
            dataKey="value"
            nameKey="name"
            innerRadius={70}
            outerRadius={110}
            paddingAngle={3}
          >
            {cleaned.map((entry, index) => (
              <Cell
                key={`${entry.name}-${index}`}
                fill={COLORS[index % COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}