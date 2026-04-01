import Sidebar from "@/components/Sidebar";
import StatusBadge from "@/components/StatusBadge";
import AnalyzeButton from "@/components/AnalyzeButton";
import { unstable_cache } from "next/cache";
import PermitJourneyTimeline, { derivePhase, deriveCompleted } from "@/components/PermitJourneyTimeline";
import NextActions from "@/components/NextActions";
import { api } from "@/lib/api";
import { MOCK_PROJECTS } from "@/lib/mockData";
import Link from "next/link";

// Per-project mock clearances shown when API is offline
const MOCK_CLEARANCES_BY_PROJECT: Record<string, any[]> = {
  default: [
    { id: "mc-1", clearance_type: "Coastal Zone Review", department: "Planning", status: "in_review", is_bottleneck: true, predicted_days: 42 },
    { id: "mc-2", clearance_type: "Structural Plan Check", department: "LADBS", status: "not_started", is_bottleneck: false, predicted_days: 21 },
    { id: "mc-3", clearance_type: "Fire Hazard Clearance", department: "Fire", status: "approved", is_bottleneck: false, predicted_days: 14 },
    { id: "mc-4", clearance_type: "Utility Service Check", department: "DWP", status: "in_review", is_bottleneck: false, predicted_days: 18 },
    { id: "mc-5", clearance_type: "Grading Review", department: "LADBS", status: "not_started", is_bottleneck: false, predicted_days: 28 },
    { id: "mc-6", clearance_type: "Environmental Health", department: "Health", status: "approved", is_bottleneck: false, predicted_days: 7 },
  ],
};

export default async function ProjectDetailPage({
  params,
}: {
  params: { id: string };
}) {
  let project: any = null;
  let clearances: any[] = [];

  const fetchProjectData = unstable_cache(
    async (id: string) => {
      const [projectResult, clearancesResult] = await Promise.allSettled([
        api.projects.get(id),
        api.clearances.list(id),
      ]);
      return {
        project: projectResult.status === "fulfilled"
          ? projectResult.value
          : (MOCK_PROJECTS.items.find((p) => p.id === id) ?? MOCK_PROJECTS.items[0]),
        clearances: clearancesResult.status === "fulfilled" && Array.isArray(clearancesResult.value) && clearancesResult.value.length > 0
          ? clearancesResult.value
          : (MOCK_CLEARANCES_BY_PROJECT[id] ?? MOCK_CLEARANCES_BY_PROJECT.default),
      };
    },
    [`project-detail-${params.id}`],
    { revalidate: 30 }
  );

  ({ project, clearances } = await fetchProjectData(params.id));

  const overlays = [
    { label: "Coastal Zone", active: project.is_coastal, color: "bg-cyan-100 text-cyan-700" },
    { label: "Hillside", active: project.is_hillside, color: "bg-amber-100 text-amber-700" },
    { label: "VHFSZ", active: project.is_vhfsz, color: "bg-orange-100 text-orange-700" },
    { label: "HPOZ", active: project.is_hpoz, color: "bg-purple-100 text-purple-700" },
  ].filter((o) => o.active);

  const clearancesByStatus: Record<string, any[]> = {};
  clearances.forEach((c) => {
    const key = c.is_bottleneck ? "bottleneck" : c.status;
    if (!clearancesByStatus[key]) clearancesByStatus[key] = [];
    clearancesByStatus[key].push(c);
  });

  const statusOrder = ["bottleneck", "in_review", "not_started", "conditional", "approved", "denied"];

  return (
    <div className="flex h-full min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        {/* Header */}
        <div className="bg-white border-b border-slate-100 px-8 py-6">
          <div className="flex items-start justify-between">
            <div>
              <Link href="/projects" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-indigo-600 transition-colors mb-2">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                </svg>
                Projects
              </Link>
              <h1 className="text-2xl font-bold text-slate-900">{project.address}</h1>
              <div className="flex items-center gap-3 mt-2 flex-wrap">
                <StatusBadge status={project.status} />
                {project.pathway && (
                  <span className="badge bg-indigo-100 text-indigo-700 font-semibold">
                    {project.pathway.toUpperCase()}
                  </span>
                )}
                {overlays.map((o) => (
                  <span key={o.label} className={`badge ${o.color}`}>{o.label}</span>
                ))}
              </div>
            </div>
            <Link href={`/projects/${params.id}/what-if`} className="btn-secondary">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              What-if Analysis
            </Link>
          </div>
        </div>

        <div className="px-8 py-8 space-y-6">
          {/* Stats row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              { label: "Pathway", value: project.pathway?.toUpperCase() || "—" },
              { label: "Predicted Days", value: project.predicted_days != null ? `${project.predicted_days}d` : "—" },
              { label: "APN", value: project.apn || "—" },
              { label: "Created", value: project.created_at ? new Date(project.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—" },
            ].map((stat) => (
              <div key={stat.label} className="card">
                <p className="stat-label">{stat.label}</p>
                <p className="text-lg font-bold text-slate-900 mt-1">{stat.value}</p>
              </div>
            ))}
          </div>

          {/* Permit journey timeline */}
          <PermitJourneyTimeline
            currentPhase={derivePhase(clearances)}
            completedPhases={deriveCompleted(clearances)}
          />

          {/* Recommended next actions */}
          <NextActions clearances={clearances} projectId={params.id} />

          {/* Clearances */}
          <div className="card">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-semibold text-slate-800">
                Clearances
                <span className="ml-2 text-sm font-normal text-slate-400">({clearances.length})</span>
              </h3>
              <Link href="/clearances" className="text-xs text-indigo-600 hover:text-indigo-700 font-medium">
                Manage all →
              </Link>
            </div>

            {clearances.length > 0 ? (
              <div className="space-y-2">
                {clearances
                  .sort((a, b) => {
                    const ai = statusOrder.indexOf(a.is_bottleneck ? "bottleneck" : a.status);
                    const bi = statusOrder.indexOf(b.is_bottleneck ? "bottleneck" : b.status);
                    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
                  })
                  .map((c: any) => (
                    <div
                      key={c.id}
                      className={`flex items-center justify-between p-4 rounded-xl border transition-colors ${
                        c.is_bottleneck
                          ? "border-red-200 bg-red-50/60 hover:bg-red-50"
                          : "border-slate-100 hover:bg-slate-50/60"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                          c.is_bottleneck ? "bg-red-500" :
                          c.status === "approved" ? "bg-emerald-500" :
                          c.status === "in_review" ? "bg-blue-500" :
                          "bg-slate-300"
                        }`} />
                        <div>
                          <p className="font-medium text-sm text-slate-800">{c.clearance_type}</p>
                          <p className="text-xs text-slate-500 mt-0.5">{c.department}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        {c.predicted_days != null && (
                          <span className="text-xs text-slate-400 font-medium">{c.predicted_days}d predicted</span>
                        )}
                        <StatusBadge status={c.is_bottleneck ? "bottleneck" : c.status} />
                      </div>
                    </div>
                  ))}
              </div>
            ) : (
              <p className="text-slate-400 text-sm">No clearances found for this project.</p>
            )}
          </div>

          {/* PathfinderAI Analysis */}
          <div className="card">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="font-semibold text-slate-800">PathfinderAI Analysis</h3>
            </div>
            <AnalyzeButton projectId={params.id} />
          </div>
        </div>
      </main>
    </div>
  );
}
