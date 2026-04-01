import { unstable_cache } from "next/cache";
import Sidebar from "@/components/Sidebar";
import ProjectMap from "@/components/ProjectMap";
import DataSourceBanner from "@/components/DataSourceBanner";
import { api } from "@/lib/api";
import { MOCK_STATS, MOCK_BOTTLENECKS } from "@/lib/mockData";
import Link from "next/link";

const getStats = unstable_cache(
  async () => {
    try {
      const data = await api.staff.stats();
      return { data, source: "live" as const };
    } catch {
      return { data: MOCK_STATS, source: "mock" as const };
    }
  },
  ["dashboard-stats"],
  { revalidate: 30 }
);

const getBottlenecks = unstable_cache(
  async () => {
    try {
      const data = await api.staff.bottlenecks();
      return { data, source: "live" as const };
    } catch {
      return { data: MOCK_BOTTLENECKS, source: "mock" as const };
    }
  },
  ["dashboard-bottlenecks"],
  { revalidate: 30 }
);

const statCards = [
  {
    key: "active_projects",
    label: "Active Projects",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
      </svg>
    ),
    gradient: "from-indigo-500 to-violet-600",
    bg: "bg-indigo-50",
    text: "text-indigo-700",
    change: "+12% vs last month",
    positive: true,
  },
  {
    key: "pending_clearances",
    label: "Pending Clearances",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
    gradient: "from-amber-400 to-orange-500",
    bg: "bg-amber-50",
    text: "text-amber-700",
    change: "34 resolved today",
    positive: true,
  },
  {
    key: "avg_days_to_issue",
    label: "Avg. Days to Issue",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    gradient: "from-emerald-400 to-teal-500",
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    change: "−3 days vs Q3",
    positive: true,
    suffix: "d",
  },
  {
    key: "bottlenecks_detected",
    label: "Needs Attention",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    gradient: "from-amber-400 to-orange-500",
    bg: "bg-amber-50",
    text: "text-amber-700",
    change: "Review recommended",
    positive: false,
  },
  {
    key: "on_track",
    label: "On Track",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    gradient: "from-emerald-400 to-teal-500",
    bg: "bg-emerald-50",
    text: "text-emerald-700",
    change: "Progressing normally",
    positive: true,
  },
];

export default async function DashboardHome() {
  const [statsResult, bottlenecksResult] = await Promise.all([
    getStats(),
    getBottlenecks(),
  ]);
  const stats = statsResult.data;
  const bottlenecks = bottlenecksResult.data;
  const isMockData = statsResult.source === "mock" || bottlenecksResult.source === "mock";
  const fetchTimestamp = Date.now();

  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="flex h-full min-h-screen">
      <Sidebar />

      <main id="main-content" className="flex-1 overflow-y-auto">
        {/* Page header */}
        <div className="bg-white border-b border-slate-100 px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">
                Fire Rebuild Dashboard
              </h1>
              <p className="text-sm text-slate-500 mt-0.5">{today} · Pacific Palisades & Altadena Recovery</p>
            </div>
            <div className="flex items-center gap-3">
              {isMockData ? (
                <span className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-full">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                  Cached data
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-full">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Live data
                </span>
              )}
              <span className="text-xs text-slate-400">Updated {new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}</span>
              <Link href="/projects/new" className="btn-primary">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                </svg>
                New Project
              </Link>
            </div>
          </div>
        </div>

        {isMockData && <div role="alert"><DataSourceBanner source="mock" timestamp={fetchTimestamp} /></div>}

        <div className="px-8 py-8 space-y-8">
          {/* Stat cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-5">
            {statCards.map((card) => {
              const value = card.key === "on_track"
                ? (stats ? (stats.active_projects ?? 0) - (stats.bottlenecks_detected ?? 0) : null)
                : stats?.[card.key as keyof typeof stats];
              return (
                <div key={card.key} className="card animate-in">
                  <div className="flex items-start justify-between">
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${card.gradient} flex items-center justify-center text-white shadow-sm flex-shrink-0`}>
                      {card.icon}
                    </div>
                    <span className={`text-xs font-medium px-2 py-1 rounded-lg ${card.bg} ${card.text}`}>
                      {card.positive ? "↑" : "↓"} {card.change.split(" ").slice(1).join(" ")}
                    </span>
                  </div>
                  <div className="mt-4">
                    <p className="text-sm text-slate-500 font-medium">{card.label}</p>
                    <p className="text-3xl font-bold text-slate-900 mt-1">
                      {value != null ? `${value}${card.suffix ?? ""}` : (
                        <span className="text-slate-300">—</span>
                      )}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Middle section: pipeline + map */}
          <div className="grid grid-cols-5 gap-6">
            {/* Pipeline */}
            <div className="col-span-2 card">
              <div className="flex items-center justify-between mb-5">
                <h3 className="font-semibold text-slate-800">Clearance Pipeline</h3>
                <Link href="/analytics" className="text-xs text-indigo-600 hover:text-indigo-700 font-medium flex items-center gap-1">
                  Full analytics
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                  </svg>
                </Link>
              </div>
              {stats ? (
                <div className="space-y-4">
                  {[
                    { label: "Active Projects", value: stats.active_projects, max: 500, color: "bg-indigo-500", light: "bg-indigo-100" },
                    { label: "Pending Clearances", value: stats.pending_clearances, max: 2000, color: "bg-amber-500", light: "bg-amber-100" },
                    { label: "Bottlenecks", value: stats.bottlenecks_detected, max: 100, color: "bg-red-500", light: "bg-red-100" },
                  ].map((item) => (
                    <div key={item.label}>
                      <div className="flex justify-between text-sm mb-2">
                        <span className="text-slate-600 font-medium">{item.label}</span>
                        <span className="font-bold text-slate-800">{item.value}</span>
                      </div>
                      <div className={`w-full ${item.light} rounded-full h-2.5`}>
                        <div
                          className={`${item.color} h-2.5 rounded-full transition-all duration-700`}
                          style={{ width: `${Math.min((item.value / item.max) * 100, 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                  <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between">
                    <span className="text-sm text-slate-500">Avg. days to issue</span>
                    <span className="text-lg font-bold text-emerald-600">{stats.avg_days_to_issue}d</span>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-40 text-slate-400 text-sm">
                  <svg className="w-8 h-8 mb-2 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  No pipeline data available
                </div>
              )}
            </div>

            {/* Map */}
            <div className="col-span-3 card">
              <div className="flex items-center justify-between mb-5">
                <h3 className="font-semibold text-slate-800">Project Locations</h3>
                <span className="text-xs text-slate-400 bg-slate-50 px-2.5 py-1.5 rounded-lg border border-slate-100">
                  Click marker to view project
                </span>
              </div>
              <div className="rounded-xl overflow-hidden">
                <ProjectMap height={300} />
              </div>
            </div>
          </div>

          {/* Bottlenecks */}
          <div className="card">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                <h3 className="font-semibold text-slate-800">Items Needing Attention</h3>
              </div>
              <Link href="/clearances" className="text-xs text-indigo-600 hover:text-indigo-700 font-medium flex items-center gap-1">
                View all clearances
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            </div>

            {Array.isArray(bottlenecks) && bottlenecks.length > 0 && stats && (
              <div className="flex items-center gap-3 mb-4 p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                <svg className="w-5 h-5 text-emerald-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-sm text-emerald-700">
                  <strong>{(stats.active_projects ?? 0) - bottlenecks.length}</strong> of {stats.active_projects} projects are progressing on schedule
                </p>
              </div>
            )}
            {Array.isArray(bottlenecks) && bottlenecks.length > 0 ? (
              <div className="space-y-2">
                {bottlenecks.slice(0, 5).map((b: any, i: number) => (
                  <Link
                    key={i}
                    href="/clearances"
                    className="flex items-center justify-between p-4 bg-red-50/60 border border-red-100 rounded-xl hover:bg-red-50 transition-colors cursor-pointer group"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-8 h-8 rounded-lg bg-red-100 flex items-center justify-center flex-shrink-0">
                        <svg className="w-4 h-4 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                      </div>
                      <div>
                        <p className="font-medium text-slate-800 text-sm group-hover:text-red-700 transition-colors">
                          {b.address || b.project_address}
                        </p>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {b.department} &middot; {b.clearance_type}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-bold text-red-600 bg-red-100 px-3 py-1 rounded-full">
                        {b.days_stuck ?? b.predicted_days}d
                      </span>
                      <svg className="w-4 h-4 text-slate-300 group-hover:text-red-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-slate-400">
                <div className="w-12 h-12 rounded-2xl bg-emerald-50 flex items-center justify-center mb-3">
                  <svg className="w-6 h-6 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <p className="font-medium text-slate-600">No bottlenecks detected</p>
                <p className="text-sm text-slate-400 mt-1">All clearances are moving on schedule</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
