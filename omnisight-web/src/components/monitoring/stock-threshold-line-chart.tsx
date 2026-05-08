"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type StockThresholdItem = {
  name: string;
  current_quantity: number;
  threshold_units: number;
};

export function StockThresholdLineChart({
  data,
}: {
  data: StockThresholdItem[];
}) {
  if (!data.length) {
    return (
      <div className="rounded-md border border-dashed py-10 text-center text-sm text-muted-foreground">
        No stock/threshold chart data available.
      </div>
    );
  }

  return (
    <div className="h-[320px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 8, right: 12, left: -8, bottom: 20 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--border)"
            vertical={false}
          />
          <XAxis
            dataKey="name"
            angle={-20}
            textAnchor="end"
            height={64}
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
          />
          <Legend wrapperStyle={{ fontSize: "12px" }} iconType="circle" />
          <Line
            type="monotone"
            dataKey="current_quantity"
            stroke="var(--chart-1)"
            strokeWidth={2.5}
            dot={{ r: 3, fill: "var(--chart-1)" }}
            activeDot={{ r: 5 }}
            name="Current Stock"
          />
          <Line
            type="monotone"
            dataKey="threshold_units"
            stroke="var(--chart-2)"
            strokeWidth={2}
            strokeDasharray="5 4"
            dot={false}
            name="Threshold"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
