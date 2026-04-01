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

interface TrendDataPoint {
  period: string;
  value: number;
}

interface TrendChartProps {
  data: TrendDataPoint[];
  metricLabel: string;
  period: string;
}

function formatDate(dateStr: string, period: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  if (period === "month") {
    return d.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
  }
  if (period === "week") {
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default function TrendChart({ data, metricLabel, period }: TrendChartProps) {
  const chartData = data.map((d) => ({
    ...d,
    label: formatDate(d.period, period),
  }));

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
        No trend data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 12, fill: "#6b7280" }}
          tickLine={false}
          axisLine={{ stroke: "#e5e7eb" }}
        />
        <YAxis
          tick={{ fontSize: 12, fill: "#6b7280" }}
          tickLine={false}
          axisLine={{ stroke: "#e5e7eb" }}
          allowDecimals={false}
          label={{
            value: metricLabel,
            angle: -90,
            position: "insideLeft",
            style: { fontSize: 12, fill: "#6b7280" },
          }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#fff",
            border: "1px solid #e5e7eb",
            borderRadius: "8px",
            fontSize: "13px",
          }}
          labelStyle={{ fontWeight: 600 }}
          formatter={(value: number) => [value, metricLabel]}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke="#4f46e5"
          strokeWidth={2}
          dot={{ fill: "#4f46e5", r: 3 }}
          activeDot={{ r: 5, fill: "#4f46e5" }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
