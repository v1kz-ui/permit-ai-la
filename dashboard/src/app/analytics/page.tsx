"use client";

import { useEffect, useState } from "react";
import DepartmentChart from "@/components/DepartmentChart";
import ProjectMap from "@/components/ProjectMap";
import Sidebar from "@/components/Sidebar";
import StatusBadge from "@/components/StatusBadge";
import TrendChart from "@/components/TrendChart";
import { SkeletonCard, SkeletonChart } from "@/components/Skeleton";
import { api } from "@/lib/api";
import { MOCK_STATS, MOCK_BOTTLENECKS, MOCK_PIPELINE, MOCK_TREND_DATA, MOCK_EQUITY_DATA } from "@/lib/mockData";
import { useToast } from "@/components/Toast";

type PeriodKey = "day" | "week" | "month";
type MetricKey = "permits_issued" | "clearances_completed" | "bottlenecks_detected";

interface PipelineData {
  departments: any[];
  summary: {
    total_clearances: number;
    total_completed: number;
    overall_completion_rate: number;
    total_bottlenecks: number;
  };
}

export default function AnalyticsPage() {
  const { toast } = useToast();
  const [stats, setStats] = useState<any>(null);
  const [bottlenecks, setBottlenecks] = useState<any[]>([]);
  const [pipeline, setPipeline] = useState<PipelineData | null>(null);
  const [trendData, setTrendData] = useState<any[]>([]);
  const [equityData, setEquityData] = useState<any>(null);
  const [trendMetric, setTrendMetric] = useState<MetricKey>("permits_issued");
  const [trendPeriod, setTrendPeriod] = useState<PeriodKey>("day");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [statsRes, bottlenecksRes, pipelineRes, equityRes] = await Promise.all([
          api.staff.stats().catch(() => null),
          api.staff.bottlenecks().catch(() => []),
          api.analytics.pipeline().catch(() => null),
          api.analytics.equity().catch(() => null),
        ]);
        setStats(statsRes || MOCK_STATS);
        setBottlenecks(Array.isArray(bottlenecksRes) && bottlenecksRes.length > 0 ? bottlenecksRes : MOCK_BOTTLENECKS);
        setPipeline(pipelineRes || MOCK_PIPELINE);
        setEquityData(equityRes || MOCK_EQUITY_DATA);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  useEffect(() => {
    api.analytics.trends(trendMetric, trendPeriod)
      .then((res) => setTrendData(res?.data?.length > 0 ? res.data : MOCK_TREND_DATA[trendMetric] || []))
      .catch(() => setTrendData(MOCK_TREND_DATA[trendMetric] || []));
  }, [trendMetric, trendPeriod]);

  async function handleExport() {
    try {
      const blob = await api.analytics.export("csv");
      if (blob instanceof Blob) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "analytics_export.csv";
        a.click();
        URL.revokeObjectURL(url);
      }
      toast({ title: "Export started", description: "Your CSV download should begin shortly", type: "info" });
    } catch {
      toast({ title: "Export failed", description: "Could not generate the CSV export", type: "error" });
    }
  }

  const metricLabels: Record<MetricKey, string> = {
    permits_issued: "Permits Issued",
    clearances_completed: "Clearances Completed",
    bottlenecks_detected: "Bottlenecks Detected",
  };

  const periodLabels: Record<PeriodKey, string> = {
    day: "7 days",
    week: "30 days",
    month: "90 days",
  };

  const kpiCards = [
    {
      label: "Active Projects",
      value: stats?.active_projects,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
        </svg>
      ),
      gradient: "from-indigo-500 to-violet-600",
      suffix: "",
    },
    {
      label: "Completion Rate",
      value: pipeline?.summary?.overall_completion_rate != null
        ? `${pipeline.summary.overall_completion_rate}%`
        : null,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      gradient: "from-emerald-400 to-teal-500",
      suffix: "",
    },
    {
      label: "Avg. Days to Issue",
      value: stats?.avg_days_to_issue,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      gradient: "from-amber-400 to-orange-500",
      suffix: "d",
    },
    {
      label: "Active Bottlenecks",
      value: pipeline?.summary?.total_bottlenecks ?? stats?.bottlenecks_detected,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
      gradient: "from-red-400 to-rose-500",
      suffix: "",
    },
  ];

  if (loading) {
    return (
      <div className="flex h-full min-h-screen">
        <Sidebar />
        <main className="flex-1 p-8">
          <div className="space-y-6">
            <div className="h-8 w-48 bg-slate-200 rounded-xl animate-pulse" />
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {[1, 2, 3, 4].map((i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
            <SkeletonChart height={320} />
            <SkeletonChart height={256} />
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        {/* Header */}
        <div className="bg-white border-b border-slate-100 px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Analytics</h1>
              <p className="text-sm text-slate-500 mt-0.5">Pipeline performance &amp; equity metrics</p>
            </div>
            <button onClick={handleExport} className="btn-secondary">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Export CSV
            </button>
          </div>
        </div>

        <div className="px-8 py-8 space-y-8">
          {/* KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {kpiCards.map((card, i) => (
              <div key={i} className="card animate-in" style={{ animationDelay: `${i * 60}ms` }}>
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${card.gradient} flex items-center justify-center text-white mb-4 shadow-sm`}>
                  {card.icon}
                </div>
                <p className="text-sm text-slate-500 font-medium">{card.label}</p>
                <p className="text-3xl font-bold text-slate-900 mt-1">
                  {card.value != null ? `${card.value}${card.suffix}` : <span className="text-slate-300">—</span>}
                </p>
              </div>
            ))}
          </div>

          {/* Department chart */}
          <div className="card">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="font-semibold text-slate-800">Department Performance</h3>
                <p className="text-xs text-slate-500 mt-0.5">Green = low bottlenecks · Amber = moderate · Red = high</p>
              </div>
            </div>
            <DepartmentChart data={pipeline?.departments || []} />
          </div>

          {/* Trend chart */}
          <div className="card">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-semibold text-slate-800">Trends</h3>
              <div className="flex items-center gap-2">
                <select
                  value={trendMetric}
                  onChange={(e) => setTrendMetric(e.target.value as MetricKey)}
                  className="select w-auto text-sm"
                >
                  {Object.entries(metricLabels).map(([key, label]) => (
                    <option key={key} value={key}>{label}</option>
                  ))}
                </select>
                <div className="flex rounded-xl border border-slate-200 overflow-hidden">
                  {(Object.entries(periodLabels) as [PeriodKey, string][]).map(([key, label]) => (
                    <button
                      key={key}
                      onClick={() => setTrendPeriod(key)}
                      className={`px-3 py-2 text-xs font-semibold transition-colors ${
                        trendPeriod === key
                          ? "bg-indigo-600 text-white"
                          : "bg-white text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <TrendChart data={trendData} metricLabel={metricLabels[trendMetric]} period={trendPeriod} />
          </div>

          {/* Equity + Language/Pathway */}
          <div className="card">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-semibold text-slate-800">Equity Metrics — Processing by Area</h3>
            </div>
            {equityData?.areas && equityData.areas.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="table-base">
                  <thead>
                    <tr>
                      <th>Area</th>
                      <th className="text-right">Projects</th>
                      <th className="text-right">Avg Predicted Days</th>
                      <th className="text-right">Avg Actual Days</th>
                    </tr>
                  </thead>
                  <tbody>
                    {equityData.areas.map((area: any, i: number) => (
                      <tr key={i}>
                        <td className="font-medium">{area.area}</td>
                        <td className="text-right">{area.project_count}</td>
                        <td className="text-right">{area.avg_predicted_days ?? "—"}</td>
                        <td className="text-right">{area.avg_actual_days ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-slate-400 text-sm">No area data available</p>
            )}
          </div>

          {/* Language + Pathway */}
          <div className="grid grid-cols-2 gap-6">
            <div className="card">
              <h3 className="font-semibold text-slate-800 mb-4">Language Distribution</h3>
              {equityData?.languages && equityData.languages.length > 0 ? (
                <div className="space-y-3">
                  {equityData.languages.map((lang: any, i: number) => (
                    <div key={i} className="flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-600">{lang.language.toUpperCase()}</span>
                      <span className="text-sm font-bold text-slate-800">{lang.count}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-slate-400 text-sm">No language data</p>
              )}
            </div>
            <div className="card">
              <h3 className="font-semibold text-slate-800 mb-4">Pathway Distribution</h3>
              {equityData?.pathways && equityData.pathways.length > 0 ? (
                <div className="space-y-3">
                  {equityData.pathways.map((pw: any, i: number) => (
                    <div key={i} className="flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-600">
                        {pw.pathway.replace(/_/g, " ")}
                      </span>
                      <span className="text-sm font-bold text-slate-800">
                        {pw.count}
                        {pw.avg_predicted_days != null && (
                          <span className="text-slate-400 font-normal ml-1">({pw.avg_predicted_days}d avg)</span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-slate-400 text-sm">No pathway data</p>
              )}
            </div>
          </div>

          {/* Bottlenecks */}
          <div className="card">
            <h3 className="font-semibold text-slate-800 mb-5">Active Bottlenecks</h3>
            {bottlenecks.length > 0 ? (
              <div className="space-y-2">
                {bottlenecks.map((b: any, i: number) => (
                  <div key={i} className="flex items-center justify-between p-4 bg-red-50/60 border border-red-100 rounded-xl">
                    <div>
                      <p className="font-medium text-sm text-slate-800">{b.address || b.project_address}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{b.department} · {b.clearance_type}</p>
                      {b.reason && <p className="text-xs text-red-600 mt-1">{b.reason}</p>}
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-bold text-red-600 bg-red-100 px-3 py-1 rounded-full">
                        {b.days_stuck ?? b.predicted_days ?? "—"}d
                      </span>
                      <StatusBadge status="bottleneck" />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-slate-400 text-sm">No bottlenecks detected</p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
