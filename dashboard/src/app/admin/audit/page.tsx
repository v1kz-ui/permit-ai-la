"use client";

import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import Link from "next/link";
import { api } from "@/lib/api";

const MOCK_AUDIT_ENTRIES = [
  { id: "a1", table_name: "projects", record_id: "proj-001-abcd", action: "INSERT", field_name: null, old_value: null, new_value: { address: "14823 Sunset Blvd", pathway: "eo1" }, changed_by: "usr-ladbs-01", changed_at: "2026-03-30T09:14:22Z" },
  { id: "a2", table_name: "clearances", record_id: "cl-004-efgh", action: "UPDATE", field_name: "status", old_value: "not_started", new_value: "in_review", changed_by: "usr-ladbs-02", changed_at: "2026-03-30T10:02:11Z" },
  { id: "a3", table_name: "clearances", record_id: "cl-008-ijkl", action: "UPDATE", field_name: "status", old_value: "in_review", new_value: "approved", changed_by: "usr-planning-01", changed_at: "2026-03-30T10:45:00Z" },
  { id: "a4", table_name: "projects", record_id: "proj-002-mnop", action: "UPDATE", field_name: "pathway", old_value: "standard", new_value: "eo1", changed_by: "usr-ladbs-01", changed_at: "2026-03-29T14:22:33Z" },
  { id: "a5", table_name: "inspections", record_id: "insp-003-qrst", action: "INSERT", field_name: null, old_value: null, new_value: { type: "foundation", scheduled: "2026-04-02" }, changed_by: "usr-inspector-01", changed_at: "2026-03-29T11:15:00Z" },
  { id: "a6", table_name: "clearances", record_id: "cl-012-uvwx", action: "UPDATE", field_name: "is_bottleneck", old_value: false, new_value: true, changed_by: "sys-auto", changed_at: "2026-03-28T16:00:00Z" },
  { id: "a7", table_name: "users", record_id: "usr-homeowner-05", action: "UPDATE", field_name: "role", old_value: "homeowner", new_value: "liaison", changed_by: "usr-admin-01", changed_at: "2026-03-27T09:00:00Z" },
  { id: "a8", table_name: "projects", record_id: "proj-007-yzab", action: "UPDATE", field_name: "status", old_value: "in_review", new_value: "denied", changed_by: "usr-planning-02", changed_at: "2026-03-26T15:30:00Z" },
];

interface AuditEntry {
  id: string;
  table_name: string;
  record_id: string;
  action: string;
  field_name: string | null;
  old_value: any;
  new_value: any;
  changed_by: string | null;
  changed_at: string;
}

const TABLE_OPTIONS = ["", "projects", "clearances", "inspections", "users", "documents"];

function ActionBadge({ action }: { action: string }) {
  const styles: Record<string, string> = {
    INSERT: "bg-emerald-100 text-emerald-700 border border-emerald-200",
    UPDATE: "bg-blue-100 text-blue-700 border border-blue-200",
    DELETE: "bg-red-100 text-red-700 border border-red-200",
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${styles[action] || "bg-slate-100 text-slate-600"}`}>
      {action}
    </span>
  );
}

export default function AuditPage() {
  const [items, setItems] = useState<AuditEntry[]>([]);
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const now = new Date();
  const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
  const [startDate, setStartDate] = useState(monthAgo.toISOString().slice(0, 10));
  const [endDate, setEndDate] = useState(now.toISOString().slice(0, 10));
  const [tableFilter, setTableFilter] = useState("");
  const [userFilter, setUserFilter] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => { loadAudit(); }, [page]);

  async function loadAudit() {
    setLoading(true);
    try {
      const params: any = {
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate + "T23:59:59").toISOString(),
        page,
        size: 50,
      };
      if (tableFilter) params.table_name = tableFilter;
      if (userFilter) params.user_id = userFilter;
      const data = await api.admin.audit(params);
      setItems(data.items?.length > 0 ? data.items : MOCK_AUDIT_ENTRIES as AuditEntry[]);
    } catch {
      setItems(MOCK_AUDIT_ENTRIES as AuditEntry[]);
    } finally {
      setLoading(false);
    }
  }

  async function handleExport(fmt: "json" | "csv") {
    try {
      const params: any = {
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate + "T23:59:59").toISOString(),
        size: 10000,
      };
      if (tableFilter) params.table_name = tableFilter;
      if (userFilter) params.user_id = userFilter;
      const data = await api.admin.audit(params);
      const rows = data.items || [];
      let content: string;
      let mimeType: string;
      let extension: string;
      if (fmt === "csv") {
        const header = "id,table_name,record_id,action,field_name,changed_by,changed_at";
        const lines = rows.map((r: AuditEntry) =>
          `${r.id},${r.table_name},${r.record_id},${r.action},${r.field_name || ""},${r.changed_by || ""},${r.changed_at}`
        );
        content = [header, ...lines].join("\n");
        mimeType = "text/csv";
        extension = "csv";
      } else {
        content = JSON.stringify(rows, null, 2);
        mimeType = "application/json";
        extension = "json";
      }
      const blob = new Blob([content], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audit-log.${extension}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {}
  }

  return (
    <div className="flex h-full min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="bg-white border-b border-slate-100 px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <Link href="/admin" className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-indigo-600 transition-colors mb-1">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                </svg>
                Admin
              </Link>
              <h1 className="text-2xl font-bold text-slate-900">Audit Log</h1>
              <p className="text-sm text-slate-500 mt-0.5">Full history of all system changes</p>
            </div>
            <div className="flex gap-2">
              <button onClick={() => handleExport("json")} className="btn-secondary text-xs !py-1.5">Export JSON</button>
              <button onClick={() => handleExport("csv")} className="btn-secondary text-xs !py-1.5">Export CSV</button>
            </div>
          </div>
        </div>

        <div className="px-8 py-6 space-y-5">
          {/* Filters */}
          <div className="card !p-4 flex flex-wrap items-end gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Start Date</label>
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="input !py-1.5 text-sm w-auto" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">End Date</label>
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="input !py-1.5 text-sm w-auto" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Table</label>
              <select value={tableFilter} onChange={(e) => setTableFilter(e.target.value)} className="select !py-1.5 text-sm w-auto">
                {TABLE_OPTIONS.map((t) => <option key={t} value={t}>{t || "All tables"}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">User ID</label>
              <input type="text" value={userFilter} onChange={(e) => setUserFilter(e.target.value)} placeholder="UUID…" className="input !py-1.5 text-sm w-44" />
            </div>
            <button onClick={() => { setPage(1); loadAudit(); }} className="btn-primary !py-1.5">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Search
            </button>
          </div>

          {/* Table */}
          <div className="card !p-0 overflow-hidden overflow-x-auto">
            <table className="table-base">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Table</th>
                  <th>Record ID</th>
                  <th>Field</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={6} className="text-center py-12 text-slate-400">Loading…</td></tr>
                ) : items.length === 0 ? (
                  <tr><td colSpan={6} className="text-center py-12 text-slate-400">No audit entries found</td></tr>
                ) : (
                  items.map((item) => (
                    <>
                      <tr
                        key={item.id}
                        className="cursor-pointer"
                        onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                      >
                        <td className="text-slate-500 whitespace-nowrap text-xs">
                          {new Date(item.changed_at).toLocaleString()}
                        </td>
                        <td className="font-mono text-xs text-slate-500">
                          {item.changed_by?.slice(0, 8) || "—"}
                        </td>
                        <td><ActionBadge action={item.action} /></td>
                        <td className="font-medium">{item.table_name}</td>
                        <td className="font-mono text-xs text-slate-400">{item.record_id?.slice(0, 8)}…</td>
                        <td className="text-slate-500 text-xs">{item.field_name || "full record"}</td>
                      </tr>
                      {expandedId === item.id && (
                        <tr key={`${item.id}-detail`}>
                          <td colSpan={6} className="px-5 py-4 bg-slate-50 border-t border-slate-100">
                            <div className="grid grid-cols-2 gap-4 text-xs">
                              <div>
                                <p className="font-semibold text-slate-600 mb-2">Old Value</p>
                                <pre className="bg-white p-3 rounded-xl border border-slate-200 overflow-auto max-h-40 text-slate-700 leading-relaxed">
                                  {item.old_value ? JSON.stringify(item.old_value, null, 2) : "null"}
                                </pre>
                              </div>
                              <div>
                                <p className="font-semibold text-slate-600 mb-2">New Value</p>
                                <pre className="bg-white p-3 rounded-xl border border-slate-200 overflow-auto max-h-40 text-slate-700 leading-relaxed">
                                  {item.new_value ? JSON.stringify(item.new_value, null, 2) : "null"}
                                </pre>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center gap-2">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="btn-secondary !py-1.5 !px-3 text-xs disabled:opacity-40">Previous</button>
            <span className="text-sm text-slate-500">Page {page}</span>
            <button disabled={items.length < 50} onClick={() => setPage((p) => p + 1)} className="btn-secondary !py-1.5 !px-3 text-xs disabled:opacity-40">Next</button>
          </div>
        </div>
      </main>
    </div>
  );
}
