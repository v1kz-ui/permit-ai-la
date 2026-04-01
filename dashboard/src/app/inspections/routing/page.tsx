import Sidebar from "@/components/Sidebar";
import Link from "next/link";
import { api } from "@/lib/api";

// Mock fallback data
const MOCK_ROUTING = {
  date: new Date().toISOString().split("T")[0],
  total_inspections: 10,
  total_inspectors: 3,
  avg_drive_minutes: 24,
  clusters: [
    {
      cluster_id: 1,
      area: "Pacific Palisades North",
      inspector: "J. Rodriguez",
      inspections: [
        { address: "1234 Palisades Dr", type: "framing", time: "9:00 AM" },
        { address: "1256 Palisades Dr", type: "foundation", time: "10:30 AM" },
        { address: "88 Malibu Canyon Rd", type: "electrical", time: "1:00 PM" },
      ],
      estimated_drive_minutes: 22,
      center_lat: 34.0522,
      center_lng: -118.5220,
    },
    {
      cluster_id: 2,
      area: "Pacific Palisades South",
      inspector: "M. Chen",
      inspections: [
        { address: "567 Sunset Blvd", type: "plumbing", time: "9:00 AM" },
        { address: "891 Via de la Paz", type: "framing", time: "11:00 AM" },
        { address: "203 Swarthmore Ave", type: "final", time: "2:00 PM" },
      ],
      estimated_drive_minutes: 18,
      center_lat: 34.0395,
      center_lng: -118.5270,
    },
    {
      cluster_id: 3,
      area: "Altadena / Eaton Fire Zone",
      inspector: "K. Williams",
      inspections: [
        { address: "1122 Altadena Dr", type: "foundation", time: "8:30 AM" },
        { address: "890 Lake Ave", type: "electrical", time: "10:00 AM" },
        { address: "445 Marengo Ave", type: "framing", time: "1:30 PM" },
        { address: "667 Santa Rosa Ave", type: "final", time: "3:00 PM" },
      ],
      estimated_drive_minutes: 31,
      center_lat: 34.1897,
      center_lng: -118.1317,
    },
  ],
};

const INSPECTOR_COLORS = [
  { bg: "bg-indigo-100", text: "text-indigo-700", dot: "bg-indigo-500", border: "border-indigo-200" },
  { bg: "bg-emerald-100", text: "text-emerald-700", dot: "bg-emerald-500", border: "border-emerald-200" },
  { bg: "bg-amber-100", text: "text-amber-700", dot: "bg-amber-500", border: "border-amber-200" },
  { bg: "bg-violet-100", text: "text-violet-700", dot: "bg-violet-500", border: "border-violet-200" },
];

const TYPE_LABELS: Record<string, string> = {
  foundation: "Foundation",
  framing: "Framing",
  electrical: "Electrical",
  plumbing: "Plumbing",
  mechanical: "Mechanical",
  insulation: "Insulation",
  drywall: "Drywall",
  final: "Final",
};

async function getRouting() {
  try {
    const data = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/inspections/routing/assignments`,
      { next: { revalidate: 300 }, credentials: "include" }
    ).then((r) => (r.ok ? r.json() : null));
    return data || MOCK_ROUTING;
  } catch {
    return MOCK_ROUTING;
  }
}

export default async function InspectorRoutingPage() {
  const routing = await getRouting();
  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="flex h-full min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        {/* Header */}
        <div className="bg-white border-b border-slate-100 px-8 py-6">
          <div className="flex items-start justify-between">
            <div>
              <Link
                href="/inspections"
                className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-indigo-600 transition-colors mb-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                </svg>
                Inspections
              </Link>
              <h1 className="text-2xl font-bold text-slate-900">Inspector Routing</h1>
              <p className="text-sm text-slate-500 mt-0.5">{today}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                Geographic clustering active
              </span>
            </div>
          </div>
        </div>

        <div className="px-8 py-8 space-y-6">
          {/* Stats row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            {[
              { label: "Inspections Today", value: routing.total_inspections ?? 10, icon: "🔍" },
              { label: "Inspectors Active", value: routing.total_inspectors ?? routing.clusters?.length ?? 3, icon: "👷" },
              { label: "Avg Drive Time", value: `${routing.avg_drive_minutes ?? 24} min`, icon: "🚗" },
            ].map((s) => (
              <div key={s.label} className="card text-center">
                <div className="text-2xl mb-1">{s.icon}</div>
                <p className="text-2xl font-bold text-slate-900">{s.value}</p>
                <p className="stat-label mt-1">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Cluster cards */}
          <div className="space-y-4">
            <h2 className="text-base font-semibold text-slate-700">
              Assignment Clusters
              <span className="ml-2 text-sm font-normal text-slate-400">
                Grouped by geographic proximity to minimize drive time
              </span>
            </h2>

            {(routing.clusters || []).map((cluster: any, i: number) => {
              const color = INSPECTOR_COLORS[i % INSPECTOR_COLORS.length];
              return (
                <div key={cluster.cluster_id} className={`card border ${color.border}`}>
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-9 h-9 rounded-xl ${color.bg} flex items-center justify-center`}>
                        <div className={`w-3 h-3 rounded-full ${color.dot}`} />
                      </div>
                      <div>
                        <p className="font-semibold text-slate-900">{cluster.area}</p>
                        <p className={`text-sm font-medium ${color.text}`}>
                          Inspector: {cluster.inspector}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-slate-700">
                        ~{cluster.estimated_drive_minutes} min drive
                      </p>
                      <p className="text-xs text-slate-400 mt-0.5">
                        {cluster.inspections?.length ?? 0} inspections
                      </p>
                    </div>
                  </div>

                  {/* Inspection schedule */}
                  <div className="space-y-2">
                    {(cluster.inspections || []).map((insp: any, j: number) => (
                      <div
                        key={j}
                        className="flex items-center gap-3 p-3 rounded-lg bg-slate-50 border border-slate-100"
                      >
                        <div className="w-16 text-xs font-semibold text-slate-500 flex-shrink-0">
                          {insp.time}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-slate-800 truncate">
                            {insp.address}
                          </p>
                        </div>
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${color.bg} ${color.text}`}>
                          {TYPE_LABELS[insp.type] || insp.type}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Map placeholder */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-slate-800">Geographic View</h2>
              <span className="text-xs text-slate-400">Mapbox GL — configure NEXT_PUBLIC_MAPBOX_TOKEN to enable</span>
            </div>
            <div className="h-72 rounded-xl bg-slate-100 flex flex-col items-center justify-center gap-3 border-2 border-dashed border-slate-200">
              <svg className="w-10 h-10 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498l4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 00-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0z" />
              </svg>
              <div className="text-center">
                <p className="text-sm font-medium text-slate-400">Interactive map ready</p>
                <p className="text-xs text-slate-300 mt-1">
                  {(routing.clusters || []).length} clusters across Palisades + Altadena zones
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
