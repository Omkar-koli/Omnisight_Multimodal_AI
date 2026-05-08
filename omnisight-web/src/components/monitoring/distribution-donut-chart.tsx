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

/**
 * Charcoal + amber palette.
 * Critical states keep a warm-red so semantics stay readable;
 * everything else moves through the brand.
 */
const COLORS = [
  "var(--chart-2)", // charcoal
  "var(--chart-1)", // amber
  "var(--chart-3)", // warm orange
  "var(--chart-4)", // olive amber
  "var(--chart-5)", // warm taupe
];

/** Status-aware overrides, used when the slice name implies a severity. */
const STATUS_COLORS: Record<string, string> = {
  Critical: "oklch(0.58 0.22 25)",   // destructive red
  "Low Stock": "var(--chart-3)",     // warm orange
  Sufficient: "var(--chart-1)",      // amber primary
  Overstock: "var(--chart-4)",       // olive amber
  "Trending Up": "var(--chart-1)",
  "Trending Down": "var(--chart-2)",
  Stable: "var(--chart-5)",
};

function colorFor(name: string, index: number) {
  return STATUS_COLORS[name] ?? COLORS[index % COLORS.length];
}

export function DistributionDonutChart({
  data,
  emptyTitle = "No data available",
}: {
  data: ChartItem[];
  emptyTitle?: string;
}) {
  const cleaned = (data ?? []).filter((item) => Number(item.value) > 0);

  if (cleaned.length === 0) {
    return (
      <div className="rounded-md border border-dashed py-10 text-center text-sm text-muted-foreground">
        {emptyTitle}
      </div>
    );
  }

  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={cleaned}
            dataKey="value"
            nameKey="name"
            innerRadius={68}
            outerRadius={104}
            paddingAngle={2}
            stroke="var(--background)"
            strokeWidth={2}
          >
            {cleaned.map((entry, index) => (
              <Cell
                key={`${entry.name}-${index}`}
                fill={colorFor(entry.name, index)}
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--popover)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              fontSize: "12px",
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: "12px" }}
            iconType="circle"
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
