"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface DepartmentData {
  department: string;
  total: number;
  completed: number;
  completion_rate: number;
  avg_processing_days: number | null;
  bottleneck_count: number;
}

interface DepartmentChartProps {
  data: DepartmentData[];
}

function getBarColor(bottleneckCount: number): string {
  if (bottleneckCount >= 5) return "#ef4444"; // red - high bottleneck
  if (bottleneckCount >= 2) return "#f59e0b"; // amber - moderate
  return "#22c55e"; // green - low
}

function formatDeptName(name: string): string {
  return name.replace(/_/g, " ").toUpperCase();
}

export default function DepartmentChart({ data }: DepartmentChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
        No department data available
      </div>
    );
  }

  const chartData = data.map((d) => ({
    ...d,
    displayName: formatDeptName(d.department),
    avgDays: d.avg_processing_days ?? 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={350}>
      <BarChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 60 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="displayName"
          tick={{ fontSize: 11, fill: "#6b7280" }}
          tickLine={false}
          axisLine={{ stroke: "#e5e7eb" }}
          angle={-35}
          textAnchor="end"
          interval={0}
        />
        <YAxis
          tick={{ fontSize: 12, fill: "#6b7280" }}
          tickLine={false}
          axisLine={{ stroke: "#e5e7eb" }}
          label={{
            value: "Avg Processing Days",
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
          formatter={(value: number, name: string) => {
            if (name === "avgDays") return [`${value} days`, "Avg Processing"];
            return [value, name];
          }}
          labelFormatter={(label) => `Department: ${label}`}
        />
        <Bar dataKey="avgDays" radius={[4, 4, 0, 0]} maxBarSize={50}>
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={getBarColor(entry.bottleneck_count)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
