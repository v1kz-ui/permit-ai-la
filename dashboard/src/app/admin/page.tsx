"use client";

import { useEffect, useState } from "react";
import Sidebar from "@/components/Sidebar";
import { api } from "@/lib/api";
import { MOCK_HEALTH } from "@/lib/mockData";
import Link from "next/link";
import { useToast } from "@/components/Toast";

interface UserRow {
  id: string;
  email: string;
  name: string;
  role: string;
  created_at: string | null;
}

interface HealthData {
  status: string;
  database?: { status: string; detail?: string };
  redis?: { status: string; used_memory_human?: string; detail?: string };
  queue_depth?: number | null;
  active_projects?: number | null;
}

const ROLES = ["homeowner", "staff", "admin", "liaison"];

export default function AdminPage() {
  const { toast } = useToast();
  const [users, setUsers] = useState<UserRow[]>([]);
  const [userPage, setUserPage] = useState(1);
  const [userTotal, setUserTotal] = useState(0);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [auditItems, setAuditItems] = useState<any[]>([]);
  const [cacheClearing, setCacheClearing] = useState(false);
  const [editingRole, setEditingRole] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadUsers();
    loadHealth();
    loadRecentAudit();
  }, [userPage]);

  async function loadUsers() {
    try {
      const data = await api.admin.users({ page: userPage, size: 20 });
      setUsers(data.items);
      setUserTotal(data.total);
    } catch {
      // API unavailable — leave users empty (no error banner for system unavailability)
    }
  }

  async function loadHealth() {
    try {
      const data = await api.admin.systemHealth();
      setHealth(data);
    } catch {
      setHealth(MOCK_HEALTH);
    }
  }

  async function loadRecentAudit() {
    try {
      const now = new Date();
      const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      const data = await api.admin.audit({
        start_date: weekAgo.toISOString(),
        end_date: now.toISOString(),
        size: 20,
      });
      setAuditItems(data.items || []);
    } catch {}
  }

  async function handleRoleChange(userId: string, newRole: string) {
    try {
      await api.admin.changeRole(userId, newRole);
      setEditingRole(null);
      loadUsers();
      toast({ title: "Role updated", description: `User role changed to ${newRole}`, type: "success" });
    } catch (e: any) {
      setError(e.message);
      toast({ title: "Role change failed", description: e.message || "Could not update user role", type: "error" });
    }
  }

  async function handleClearCache() {
    if (!confirm("Are you sure you want to clear the entire Redis cache?")) return;
    setCacheClearing(true);
    try {
      await api.admin.clearCache();
      toast({ title: "Cache cleared", description: "Redis cache has been flushed", type: "success" });
    } catch (e: any) {
      setError(e.message);
      toast({ title: "Cache clear failed", description: e.message || "Could not clear cache", type: "error" });
    } finally {
      setCacheClearing(false);
    }
  }

  const roleBadgeColor: Record<string, string> = {
    admin: "bg-red-100 text-red-700 border border-red-200",
    staff: "bg-indigo-100 text-indigo-700 border border-indigo-200",
    homeowner: "bg-emerald-100 text-emerald-700 border border-emerald-200",
    liaison: "bg-violet-100 text-violet-700 border border-violet-200",
  };

  const healthCards = [
    {
      title: "Database",
      status: health?.database?.status,
      detail: health?.database?.detail,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
        </svg>
      ),
    },
    {
      title: "Redis Cache",
      status: health?.redis?.status,
      detail: health?.redis?.used_memory_human || health?.redis?.detail,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      ),
    },
    {
      title: "Queue Depth",
      status: health?.queue_depth != null ? "info" : undefined,
      detail: health?.queue_depth != null ? `${health.queue_depth} tasks` : undefined,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      ),
    },
    {
      title: "Active Projects",
      status: health?.active_projects != null ? "info" : undefined,
      detail: health?.active_projects != null ? `${health.active_projects} projects` : undefined,
      icon: (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
        </svg>
      ),
    },
  ];

  const statusStyle = (s?: string) => {
    if (!s) return "border-slate-200 bg-slate-50";
    if (s === "connected" || s === "ok") return "border-emerald-300 bg-emerald-50";
    if (s === "error") return "border-red-300 bg-red-50";
    if (s === "info") return "border-indigo-200 bg-indigo-50";
    if (s === "unavailable") return "border-amber-300 bg-amber-50";
    return "border-slate-200 bg-slate-50";
  };

  const statusDot = (s?: string) => {
    if (!s) return "bg-slate-300";
    if (s === "connected" || s === "ok") return "bg-emerald-500";
    if (s === "error") return "bg-red-500";
    if (s === "info") return "bg-indigo-500";
    return "bg-slate-300";
  };

  return (
    <div className="flex h-full min-h-screen">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        {/* Header */}
        <div className="bg-white border-b border-slate-100 px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Admin Panel</h1>
              <p className="text-sm text-slate-500 mt-0.5">System health, user management, and audit logs</p>
            </div>
            <Link href="/admin/audit" className="btn-secondary">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              Audit Log
            </Link>
          </div>
        </div>

        <div className="px-8 py-8 space-y-8">
          {error && (
            <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
              <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01" />
              </svg>
              <span className="flex-1">{error}</span>
              <button className="text-red-500 hover:text-red-700" onClick={() => setError(null)}>✕</button>
            </div>
          )}

          {/* System Health */}
          <section>
            <h2 className="text-base font-semibold text-slate-700 mb-4">System Health</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {healthCards.map((card) => (
                <div key={card.title} className={`card border ${statusStyle(card.status)}`}>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-slate-500">{card.icon}</span>
                    <span className={`w-2 h-2 rounded-full ${statusDot(card.status)}`} />
                  </div>
                  <p className="text-sm font-medium text-slate-600">{card.title}</p>
                  <p className="text-base font-bold text-slate-900 mt-0.5 capitalize">
                    {card.status || "—"}
                  </p>
                  {card.detail && (
                    <p className="text-xs text-slate-500 mt-1">{card.detail}</p>
                  )}
                </div>
              ))}
            </div>
          </section>

          {/* Cache Management */}
          <section className="card flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-800">Cache Management</h2>
              <p className="text-sm text-slate-500 mt-0.5">Clear the entire Redis cache. This will slow down the next few requests while data reloads.</p>
            </div>
            <button
              onClick={handleClearCache}
              disabled={cacheClearing}
              className="btn-danger ml-6 flex-shrink-0"
            >
              {cacheClearing ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Clearing...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  Clear All Cache
                </>
              )}
            </button>
          </section>

          {/* User Management */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-slate-700">
                User Management
                <span className="ml-2 text-sm font-normal text-slate-400">({userTotal} users)</span>
              </h2>
            </div>
            <div className="card !p-0 overflow-hidden overflow-x-auto">
              <table className="table-base">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Joined</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td className="font-medium text-slate-800">{u.name || "—"}</td>
                      <td className="text-slate-500">{u.email}</td>
                      <td>
                        {editingRole === u.id ? (
                          <select
                            defaultValue={u.role}
                            onChange={(e) => handleRoleChange(u.id, e.target.value)}
                            onBlur={() => setEditingRole(null)}
                            className="select w-auto text-xs py-1.5"
                            autoFocus
                          >
                            {ROLES.map((r) => (
                              <option key={r} value={r}>{r}</option>
                            ))}
                          </select>
                        ) : (
                          <span className={`badge ${roleBadgeColor[u.role] || "bg-slate-100 text-slate-600"}`}>
                            {u.role}
                          </span>
                        )}
                      </td>
                      <td className="text-slate-500 text-sm">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                      </td>
                      <td>
                        <button
                          onClick={() => setEditingRole(u.id)}
                          className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
                        >
                          Edit Role
                        </button>
                      </td>
                    </tr>
                  ))}
                  {users.length === 0 && (
                    <tr>
                      <td colSpan={5} className="text-center py-8 text-slate-400">No users found</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="flex items-center gap-2 mt-3">
              <button
                disabled={userPage <= 1}
                onClick={() => setUserPage((p) => p - 1)}
                className="btn-secondary !py-1.5 !px-3 text-xs disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-sm text-slate-500">Page {userPage}</span>
              <button
                disabled={users.length < 20}
                onClick={() => setUserPage((p) => p + 1)}
                className="btn-secondary !py-1.5 !px-3 text-xs disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </section>

          {/* Recent Audit */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-slate-700">Recent Audit Log</h2>
              <Link href="/admin/audit" className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
                View all →
              </Link>
            </div>
            <div className="card !p-0 overflow-hidden max-h-80 overflow-y-auto overflow-x-auto scrollbar-thin">
              <table className="table-base">
                <thead className="sticky top-0">
                  <tr>
                    <th>Time</th>
                    <th>Action</th>
                    <th>Table</th>
                    <th>Record</th>
                  </tr>
                </thead>
                <tbody>
                  {auditItems.map((item: any, idx: number) => (
                    <tr key={idx}>
                      <td className="text-slate-500 whitespace-nowrap text-xs">
                        {new Date(item.changed_at).toLocaleString()}
                      </td>
                      <td>
                        <span className="badge bg-slate-100 text-slate-700">{item.action}</span>
                      </td>
                      <td className="font-medium">{item.table_name}</td>
                      <td className="font-mono text-xs text-slate-400">
                        {item.record_id?.slice(0, 8)}…
                      </td>
                    </tr>
                  ))}
                  {auditItems.length === 0 && (
                    <tr>
                      <td colSpan={4} className="text-center py-8 text-slate-400">No recent audit entries</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
