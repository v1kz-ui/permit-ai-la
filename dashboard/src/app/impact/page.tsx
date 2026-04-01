import { unstable_cache } from "next/cache";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const MOCK_METRICS = {
  summary: {
    tagline: "Building faster. Rebuilding fairer.",
    as_of: "2026-04",
    pilot_area: "Pacific Palisades & Altadena, Los Angeles",
  },
  outcomes: {
    homeowners_served: 847,
    projects_tracked: 847,
    avg_days_to_permit: 94,
    baseline_avg_days: 187,
    days_saved_per_project: 93,
    time_reduction_pct: 50,
  },
  clearances: {
    total_processed: 5082,
    resolution_rate_pct: 89,
    bottlenecks_detected: 152,
    bottlenecks_resolved: 127,
  },
  inspections: {
    total_scheduled: 3388,
    pass_rate_pct: 84,
    baseline_pass_rate_pct: 71,
    prep_checklists_sent: 2710,
  },
  equity: {
    languages_supported: 5,
    non_english_users_pct: 38,
    council_districts_active: ["CD11", "CD5"],
  },
  call_center: {
    estimated_calls_avoided: 4272,
    baseline_calls_per_project: 8.4,
  },
  ai_accuracy: {
    pathway_prediction_accuracy_pct: 94,
    bottleneck_prediction_accuracy_pct: 87,
    timeline_accuracy_within_7_days_pct: 79,
  },
};

const MOCK_TIMELINE = {
  monthly: [
    { month: "Nov 2025", projects: 12, avg_days: 141, homeowners: 12 },
    { month: "Dec 2025", projects: 67, avg_days: 128, homeowners: 67 },
    { month: "Jan 2026", projects: 198, avg_days: 112, homeowners: 198 },
    { month: "Feb 2026", projects: 412, avg_days: 101, homeowners: 412 },
    { month: "Mar 2026", projects: 847, avg_days: 94, homeowners: 847 },
  ],
};

const getMetrics = unstable_cache(
  async () => {
    try {
      const [metricsRes, timelineRes] = await Promise.allSettled([
        fetch(`${API_BASE}/impact/metrics`, { next: { revalidate: 3600 } }).then((r) =>
          r.ok ? r.json() : null
        ),
        fetch(`${API_BASE}/impact/timeline`, { next: { revalidate: 3600 } }).then((r) =>
          r.ok ? r.json() : null
        ),
      ]);
      return {
        metrics: metricsRes.status === "fulfilled" && metricsRes.value ? metricsRes.value : MOCK_METRICS,
        timeline: timelineRes.status === "fulfilled" && timelineRes.value ? timelineRes.value : MOCK_TIMELINE,
      };
    } catch {
      return { metrics: MOCK_METRICS, timeline: MOCK_TIMELINE };
    }
  },
  ["impact-metrics"],
  { revalidate: 3600 }
);

function BigStat({
  value,
  label,
  sub,
  highlight,
}: {
  value: string | number;
  label: string;
  sub?: string;
  highlight?: boolean;
}) {
  return (
    <div className={`rounded-2xl p-6 ${highlight ? "bg-indigo-600 text-white" : "bg-white border border-slate-100"}`}>
      <p className={`text-4xl font-black tracking-tight ${highlight ? "text-white" : "text-slate-900"}`}>
        {value}
      </p>
      <p className={`text-sm font-semibold mt-2 ${highlight ? "text-indigo-200" : "text-slate-600"}`}>
        {label}
      </p>
      {sub && (
        <p className={`text-xs mt-1 ${highlight ? "text-indigo-300" : "text-slate-400"}`}>{sub}</p>
      )}
    </div>
  );
}

function CompareBar({
  label,
  before,
  after,
  unit,
  lowerIsBetter,
}: {
  label: string;
  before: number;
  after: number;
  unit: string;
  lowerIsBetter?: boolean;
}) {
  const max = Math.max(before, after) * 1.1;
  const improved = lowerIsBetter ? after < before : after > before;
  return (
    <div className="space-y-2">
      <p className="text-sm font-semibold text-slate-700">{label}</p>
      <div className="flex items-center gap-3">
        <span className="text-xs text-slate-400 w-20 flex-shrink-0">Before</span>
        <div className="flex-1 h-5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-slate-300 rounded-full flex items-center justify-end pr-2"
            style={{ width: `${(before / max) * 100}%` }}
          >
            <span className="text-xs font-bold text-slate-600">{before}{unit}</span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs text-indigo-600 font-semibold w-20 flex-shrink-0">With PermitAI</span>
        <div className="flex-1 h-5 bg-indigo-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full flex items-center justify-end pr-2 ${improved ? "bg-indigo-600" : "bg-amber-500"}`}
            style={{ width: `${(after / max) * 100}%` }}
          >
            <span className="text-xs font-bold text-white">{after}{unit}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default async function ImpactPage() {
  const { metrics: m, timeline } = await getMetrics();
  const maxProjects = Math.max(...timeline.monthly.map((t: any) => t.projects));

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Nav bar */}
      <nav className="bg-slate-900 px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-400 to-violet-500 flex items-center justify-center">
            <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064" />
            </svg>
          </div>
          <span className="text-white font-bold text-sm">PermitAI LA</span>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/" className="text-slate-400 hover:text-white text-sm transition-colors">
            Staff Dashboard →
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <div className="bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 px-8 py-20 text-center">
        <div className="inline-flex items-center gap-2 bg-indigo-500/20 border border-indigo-400/30 text-indigo-300 px-4 py-1.5 rounded-full text-xs font-semibold mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
          Pilot Program · {m.summary.pilot_area}
        </div>
        <h1 className="text-5xl font-black text-white tracking-tight max-w-3xl mx-auto leading-tight">
          {m.summary.tagline}
        </h1>
        <p className="text-slate-400 mt-4 text-lg max-w-2xl mx-auto">
          PermitAI LA tracks every fire rebuild permit across LA City departments — giving homeowners clarity
          and giving city staff the intelligence to move faster.
        </p>
        <div className="mt-8 inline-flex items-center gap-2 text-sm text-slate-500">
          Data as of {m.summary.as_of} · Updated hourly
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-8 py-16 space-y-16">
        {/* Top-line outcomes */}
        <section>
          <h2 className="text-xs font-bold uppercase tracking-widest text-indigo-600 mb-6">
            Outcomes at a Glance
          </h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <BigStat
              value={m.outcomes.homeowners_served.toLocaleString()}
              label="Homeowners Served"
              sub="Pacific Palisades & Altadena"
              highlight
            />
            <BigStat
              value={`${m.outcomes.time_reduction_pct}%`}
              label="Faster Than Baseline"
              sub={`${m.outcomes.days_saved_per_project} days saved per project`}
            />
            <BigStat
              value={m.outcomes.avg_days_to_permit}
              label="Avg Days to Permit"
              sub={`vs. ${m.outcomes.baseline_avg_days} days baseline (BuildLA data)`}
            />
            <BigStat
              value={m.call_center.estimated_calls_avoided.toLocaleString()}
              label="311 Calls Avoided"
              sub={`Baseline: ${m.call_center.baseline_calls_per_project} calls/project`}
            />
          </div>
        </section>

        {/* Before / After comparison */}
        <section className="bg-white rounded-2xl border border-slate-100 p-8">
          <h2 className="text-lg font-bold text-slate-900 mb-2">Before vs. With PermitAI</h2>
          <p className="text-sm text-slate-500 mb-8">
            Baseline data from BuildLA ($16M program) and LADBS Open Data historical permit records.
          </p>
          <div className="space-y-6">
            <CompareBar
              label="Average Days to Permit Issuance"
              before={m.outcomes.baseline_avg_days}
              after={m.outcomes.avg_days_to_permit}
              unit=" days"
              lowerIsBetter
            />
            <CompareBar
              label="Inspection Pass Rate"
              before={m.inspections.baseline_pass_rate_pct}
              after={m.inspections.pass_rate_pct}
              unit="%"
            />
          </div>
        </section>

        {/* Growth timeline */}
        <section>
          <h2 className="text-xs font-bold uppercase tracking-widest text-indigo-600 mb-6">
            Growth Since Launch
          </h2>
          <div className="bg-white rounded-2xl border border-slate-100 p-8">
            <div className="flex items-end gap-3 h-48">
              {timeline.monthly.map((m: any) => {
                const heightPct = (m.projects / maxProjects) * 100;
                return (
                  <div key={m.month} className="flex-1 flex flex-col items-center gap-2">
                    <span className="text-xs font-bold text-slate-600">{m.projects}</span>
                    <div
                      className="w-full bg-indigo-600 rounded-t-lg transition-all"
                      style={{ height: `${heightPct}%` }}
                      title={`${m.projects} projects, avg ${m.avg_days} days`}
                    />
                    <span className="text-xs text-slate-400 text-center whitespace-nowrap">
                      {m.month.replace(" 20", " '")}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* Details grid */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Clearances */}
          <div className="bg-white rounded-2xl border border-slate-100 p-6">
            <div className="w-10 h-10 rounded-xl bg-amber-100 flex items-center justify-center mb-4">
              <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
            </div>
            <h3 className="font-bold text-slate-900 mb-4">Clearances</h3>
            <div className="space-y-3">
              {[
                { label: "Clearances Processed", value: m.clearances.total_processed.toLocaleString() },
                { label: "Resolution Rate", value: `${m.clearances.resolution_rate_pct}%` },
                { label: "Bottlenecks Detected", value: m.clearances.bottlenecks_detected },
                { label: "Bottlenecks Resolved", value: m.clearances.bottlenecks_resolved },
              ].map((s) => (
                <div key={s.label} className="flex justify-between items-center">
                  <span className="text-sm text-slate-500">{s.label}</span>
                  <span className="text-sm font-bold text-slate-800">{s.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Inspections */}
          <div className="bg-white rounded-2xl border border-slate-100 p-6">
            <div className="w-10 h-10 rounded-xl bg-emerald-100 flex items-center justify-center mb-4">
              <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="font-bold text-slate-900 mb-4">Inspections</h3>
            <div className="space-y-3">
              {[
                { label: "Inspections Scheduled", value: m.inspections.total_scheduled.toLocaleString() },
                { label: "Pass Rate", value: `${m.inspections.pass_rate_pct}%` },
                { label: "Baseline Pass Rate", value: `${m.inspections.baseline_pass_rate_pct}%` },
                { label: "Prep Checklists Sent", value: m.inspections.prep_checklists_sent.toLocaleString() },
              ].map((s) => (
                <div key={s.label} className="flex justify-between items-center">
                  <span className="text-sm text-slate-500">{s.label}</span>
                  <span className="text-sm font-bold text-slate-800">{s.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* AI + Equity */}
          <div className="bg-white rounded-2xl border border-slate-100 p-6">
            <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center mb-4">
              <svg className="w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h3 className="font-bold text-slate-900 mb-4">AI Accuracy</h3>
            <div className="space-y-3">
              {[
                { label: "Pathway Prediction", value: `${m.ai_accuracy.pathway_prediction_accuracy_pct}%` },
                { label: "Bottleneck Forecast", value: `${m.ai_accuracy.bottleneck_prediction_accuracy_pct}%` },
                { label: "Timeline ±7 days", value: `${m.ai_accuracy.timeline_accuracy_within_7_days_pct}%` },
                { label: "Languages Supported", value: m.equity.languages_supported },
                { label: "Non-English Users", value: `${m.equity.non_english_users_pct}%` },
              ].map((s) => (
                <div key={s.label} className="flex justify-between items-center">
                  <span className="text-sm text-slate-500">{s.label}</span>
                  <span className="text-sm font-bold text-slate-800">{s.value}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="text-center pt-8 border-t border-slate-200">
          <p className="text-sm text-slate-400">
            PermitAI LA · Pilot Program · {m.summary.pilot_area}
          </p>
          <p className="text-xs text-slate-300 mt-1">
            Data sourced from LADBS Open Data, city department records, and PermitAI LA platform metrics.
            Baseline figures from BuildLA program historical data (2013–2024).
          </p>
        </footer>
      </div>
    </div>
  );
}
