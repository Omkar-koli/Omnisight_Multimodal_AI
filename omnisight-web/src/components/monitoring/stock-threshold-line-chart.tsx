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
      <div className="text-sm text-muted-foreground">
        No stock/threshold chart data available.
      </div>
    );
  }

  return (
    <div className="h-[340px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 12, right: 16, left: 0, bottom: 16 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="name"
            angle={-20}
            textAnchor="end"
            height={70}
            interval={0}
          />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="current_quantity"
            stroke="#10b981"
            strokeWidth={2}
            dot={false}
            name="Current Stock"
          />
          <Line
            type="monotone"
            dataKey="threshold_units"
            stroke="#ef4444"
            strokeWidth={2}
            dot={false}
            name="Threshold"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}