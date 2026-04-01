"use client";

import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import StatusBadge from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { MOCK_INSPECTIONS_STATS, MOCK_INSPECTIONS } from "@/lib/mockData";
import { useToast } from "@/components/Toast";

interface Inspection {
  id: string;
  project_id: string;
  address: string;
  inspection_type: string;
  status: string;
  scheduled_date: string | null;
  completed_date: string | null;
  inspector_name: string | null;
  failure_reasons: string[];
  notes: string | null;
}

interface Stats {
  total_scheduled: number;
  pass_rate: number;
  avg_days_between: number;
  most_common_failure: string;
}

interface ScheduleForm {
  project_id: string;
  inspection_type: string;
  scheduled_date: string;
  inspector_name: string;
  notes: string;
}

const STATUS_OPTIONS = ["all", "scheduled", "passed", "failed", "cancelled"];

const INSPECTION_TYPES = [
  "Foundation", "Framing", "Rough Electrical", "Rough Plumbing",
  "Rough Mechanical", "Insulation", "Drywall", "Final Electrical",
  "Final Plumbing", "Final Mechanical", "Final Building",
];

const EMPTY_FORM: ScheduleForm = {
  project_id: "",
  inspection_type: "Foundation",
  scheduled_date: "",
  inspector_name: "",
  notes: "",
};

function ScheduleModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: (i: Inspection) => void }) {
  const [form, setForm] = useState<ScheduleForm>(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.project_id.trim()) { setError("Project ID is required."); return; }
    if (!form.scheduled_date) { setError("Please select a scheduled date."); return; }
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.inspections.schedule({
        project_id: form.project_id.trim(),
        inspection_type: form.inspection_type.toLowerCase().replace(/\s+/g, "_"),
        scheduled_date: form.scheduled_date,
        inspector_name: form.inspector_name || null,
        notes: form.notes || null,
      });
      setForm(EMPTY_FORM);
      setSubmitting(false);
      onSuccess(result);
    } catch (err: any) {
      setError(err.message || "Failed to schedule inspection.");
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 animate-in">
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100">
          <div>
            <h2 className="text-lg font-bold text-slate-900">Schedule Inspection</h2>
            <p className="text-xs text-slate-500 mt-0.5">Add a new inspection to the queue</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600 transition-colors">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {error && (
            <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
              <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01" />
              </svg>
              {error}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Project ID <span className="text-red-500">*</span></label>
            <input type="text" name="project_id" value={form.project_id} onChange={handleChange} placeholder="e.g. proj_abc123" className="input" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Inspection Type <span className="text-red-500">*</span></label>
            <select name="inspection_type" value={form.inspection_type} onChange={handleChange} className="select">
              {INSPECTION_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Scheduled Date <span className="text-red-500">*</span></label>
            <input type="date" name="scheduled_date" value={form.scheduled_date} onChange={handleChange} className="input" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Inspector Name</label>
            <input type="text" name="inspector_name" value={form.inspector_name} onChange={handleChange} placeholder="Optional" className="input" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Notes</label>
            <textarea name="notes" value={form.notes} onChange={handleChange} rows={3} placeholder="Optional notes..." className="input resize-none" />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={submitting} className="btn-primary">
              {submitting ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Scheduling...
                </>
              ) : "Schedule Inspection"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function InspectionsPage() {
  const { toast } = useToast();
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadData() {
      setLoading(true);
      // Run stats + inspections list in parallel; fall back to mock on any failure
      const [statsResult, inspResult] = await Promise.allSettled([
        api.inspections.stats(),
        api.staff.projects({ size: 20 }).then(async (projectData) => {
          const projects: any[] = projectData.items ?? [];
          const results: Inspection[] = [];
          await Promise.allSettled(
            projects.slice(0, 8).map(async (p: any) => {
              try {
                const list = await api.inspections.listForProject(p.id);
                if (Array.isArray(list)) {
                  list.forEach((insp: any) => results.push({
                    id: insp.id,
                    project_id: p.id,
                    address: insp.address ?? p.address ?? p.id,
                    inspection_type: insp.inspection_type ?? insp.type ?? "unknown",
                    status: insp.status ?? "scheduled",
                    scheduled_date: insp.scheduled_date ?? null,
                    completed_date: insp.completed_date ?? null,
                    inspector_name: insp.inspector_name ?? null,
                    failure_reasons: insp.failure_reasons ?? [],
                    notes: insp.notes ?? null,
                  }));
                }
              } catch {}
            })
          );
          return results;
        }),
      ]);

      if (!cancelled) {
        if (statsResult.status === "fulfilled" && statsResult.value) {
          const s = statsResult.value as any;
          setStats({
            total_scheduled: s.total_scheduled ?? 0,
            pass_rate: s.pass_rate ?? 0,
            avg_days_between: s.avg_days_between ?? 0,
            most_common_failure: s.most_common_failure ?? "N/A",
          });
        } else {
          setStats(MOCK_INSPECTIONS_STATS);
        }

        if (inspResult.status === "fulfilled" && Array.isArray(inspResult.value) && inspResult.value.length > 0) {
          setInspections(inspResult.value);
        } else {
          setInspections(MOCK_INSPECTIONS as Inspection[]);
        }
        setLoading(false);
      }
    }
    loadData();
    return () => { cancelled = true; };
  }, []);

  const allTypes = Array.from(new Set(inspections.map((i) => i.inspection_type))).sort();
  const filtered = inspections.filter((i) => {
    if (statusFilter !== "all" && i.status !== statusFilter) return false;
    if (typeFilter !== "all" && i.inspection_type !== typeFilter) return false;
    if (search && !i.address.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const kpiCards = [
    {
      label: "Total Scheduled",
      value: stats?.total_scheduled ?? 0,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      ),
      color: "from-indigo-500 to-violet-600",
    },
    {
      label: "Pass Rate",
      value: `${stats?.pass_rate ?? 0}%`,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      color: "from-emerald-400 to-teal-500",
    },
    {
      label: "Avg Days Between",
      value: stats?.avg_days_between ?? 0,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      color: "from-amber-400 to-orange-500",
    },
    {
      label: "Most Common Failure",
      value: stats?.most_common_failure ?? "N/A",
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      ),
      color: "from-red-400 to-rose-500",
    },
  ];

  return (
    <div className="flex h-full min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        {/* Header */}
        <div className="bg-white border-b border-slate-100 px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Inspections</h1>
              <p className="text-sm text-slate-500 mt-0.5">Track scheduled and completed inspections across all projects</p>
            </div>
            <button onClick={() => setShowModal(true)} className="btn-primary">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Schedule Inspection
            </button>
          </div>
        </div>

        <div className="px-8 py-8 space-y-6">
          {/* KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {kpiCards.map((card, i) => (
              <div key={i} className="card animate-in" style={{ animationDelay: `${i * 60}ms` }}>
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${card.color} flex items-center justify-center text-white mb-4 shadow-sm`}>
                  {card.icon}
                </div>
                <p className="text-sm text-slate-500 font-medium">{card.label}</p>
                <p className="text-2xl font-bold text-slate-900 mt-1">
                  {loading ? <span className="text-slate-200 animate-pulse">—</span> : card.value}
                </p>
              </div>
            ))}
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3">
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="select w-auto">
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>{s === "all" ? "All Statuses" : s.charAt(0).toUpperCase() + s.slice(1)}</option>
              ))}
            </select>
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="select w-auto">
              <option value="all">All Types</option>
              {allTypes.map((t) => (
                <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
              ))}
            </select>
            <div className="relative">
              <svg className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search address..."
                className="input pl-9 w-56"
              />
            </div>
            {(statusFilter !== "all" || typeFilter !== "all" || search) && (
              <button onClick={() => { setStatusFilter("all"); setTypeFilter("all"); setSearch(""); }}
                className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
                Clear filters
              </button>
            )}
          </div>

          {/* Table */}
          {loading ? (
            <div className="card animate-pulse text-center py-16 text-slate-300">Loading inspections…</div>
          ) : filtered.length === 0 ? (
            <div className="card text-center py-16">
              <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-4">
                <svg className="w-7 h-7 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <h3 className="font-semibold text-slate-700 mb-1">No inspections found</h3>
              <p className="text-sm text-slate-400 mb-5">
                {inspections.length === 0
                  ? "Inspections will appear once projects reach the inspection phase."
                  : "Try adjusting your filters."}
              </p>
              <button onClick={() => setShowModal(true)} className="btn-primary mx-auto">
                Schedule Inspection
              </button>
            </div>
          ) : (
            <div className="card !p-0 overflow-hidden overflow-x-auto">
              <table className="table-base">
                <thead>
                  <tr>
                    <th>Address</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Scheduled</th>
                    <th>Completed</th>
                    <th>Inspector</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((insp) => (
                    <tr key={insp.id}>
                      <td className="font-medium text-slate-800">{insp.address}</td>
                      <td className="capitalize text-slate-700">{insp.inspection_type.replace(/_/g, " ")}</td>
                      <td><StatusBadge status={insp.status} /></td>
                      <td className="text-slate-500">
                        {insp.scheduled_date ? new Date(insp.scheduled_date).toLocaleDateString() : "—"}
                      </td>
                      <td className="text-slate-500">
                        {insp.completed_date ? new Date(insp.completed_date).toLocaleDateString() : "—"}
                      </td>
                      <td className="text-slate-500">{insp.inspector_name || "—"}</td>
                      <td className="text-slate-400 max-w-xs truncate text-xs">
                        {insp.failure_reasons.length > 0 ? insp.failure_reasons.join(", ") : insp.notes || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="px-5 py-3 bg-slate-50 border-t border-slate-100 text-xs text-slate-400">
                Showing {filtered.length} of {inspections.length} inspection{inspections.length !== 1 ? "s" : ""}
              </div>
            </div>
          )}
        </div>

        {showModal && (
          <ScheduleModal
            onClose={() => setShowModal(false)}
            onSuccess={(inspection) => { setInspections((prev) => [inspection, ...prev]); setShowModal(false); toast({ title: "Inspection scheduled", description: "Added to queue", type: "success" }); }}
          />
        )}
      </main>
    </div>
  );
}
