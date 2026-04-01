const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Fail fast so mock-data fallbacks kick in immediately when backend is offline
function withTimeout<T>(promise: Promise<T>, ms = 500): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) =>
      setTimeout(() => reject(new Error("API request timed out")), ms)
    ),
  ]);
}

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await withTimeout(
    fetch(`${API_BASE}${path}`, {
      ...options,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    })
  );

  if (!response.ok) {
    if (response.status === 401) {
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

export const api = {
  health: () => fetchAPI<{ status: string }>("/health"),

  projects: {
    list: (params?: { status?: string; page?: number; size?: number }) =>
      fetchAPI<any[]>(`/projects?${new URLSearchParams(params as any)}`),
    get: (id: string) => fetchAPI<any>(`/projects/${id}`),
    create: (data: any) =>
      fetchAPI<any>("/projects", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: any) =>
      fetchAPI<any>(`/projects/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
  },

  clearances: {
    list: (projectId: string) =>
      fetchAPI<any[]>(`/clearances?project_id=${projectId}`),
    update: (id: string, data: any) =>
      fetchAPI<any>(`/clearances/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    updateStatus: (id: string, status: string) =>
      fetchAPI<any>(`/clearances/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
  },

  parcels: {
    get: (apn: string) => fetchAPI<any>(`/parcels/${apn}`),
    lookup: (lat: number, lng: number) =>
      fetchAPI<any>(`/parcels/lookup/by-coordinates?lat=${lat}&lng=${lng}`),
    mapData: () => fetchAPI<{
      type: "FeatureCollection";
      features: Array<{
        type: "Feature";
        geometry: { type: "Point"; coordinates: [number, number] };
        properties: {
          id: string;
          address: string;
          status: string;
          pathway: string | null;
          predicted_total_days: number | null;
          has_bottleneck: boolean;
        };
      }>;
    }>("/parcels/map-data"),
  },

  staff: {
    stats: () => fetchAPI<{
      active_projects: number;
      pending_clearances: number;
      avg_days_to_issue: number;
      bottlenecks_detected: number;
    }>("/staff/dashboard/stats"),

    departmentWorkload: () =>
      fetchAPI<any[]>("/staff/dashboard/department-workload"),

    bottlenecks: () =>
      fetchAPI<any[]>("/staff/dashboard/bottlenecks"),

    kanban: (params?: { department?: string }) => {
      const query = params?.department
        ? `?department=${encodeURIComponent(params.department)}`
        : "";
      return fetchAPI<{
        not_started: any[];
        in_review: any[];
        approved: any[];
        conditional: any[];
        denied: any[];
      }>(`/staff/dashboard/kanban${query}`);
    },

    projects: (params?: {
      status?: string;
      pathway?: string;
      page?: number;
      size?: number;
    }) => {
      const searchParams = new URLSearchParams();
      if (params?.status) searchParams.set("status", params.status);
      if (params?.pathway) searchParams.set("pathway", params.pathway);
      if (params?.page) searchParams.set("page", String(params.page));
      if (params?.size) searchParams.set("size", String(params.size));
      const query = searchParams.toString();
      return fetchAPI<{
        items: any[];
        total: number;
        page: number;
        size: number;
        pages: number;
      }>(`/staff/dashboard/projects${query ? `?${query}` : ""}`);
    },
  },

  pathfinder: {
    analyze: (projectId: string) =>
      fetchAPI<any>(`/pathfinder/analyze/${projectId}`, { method: "POST" }),

    quickAnalysis: (projectId: string) =>
      fetchAPI<any>(`/pathfinder/quick-analysis/${projectId}`),

    conflicts: (projectId: string) =>
      fetchAPI<any[]>(`/pathfinder/conflicts/${projectId}`),

    timeline: (projectId: string) =>
      fetchAPI<any>(`/pathfinder/timeline/${projectId}`),

    whatIf: (params: { address: string; original_sqft?: number; proposed_sqft?: number }) =>
      fetchAPI<any>(`/pathfinder/what-if`, {
        method: "POST",
        body: JSON.stringify(params),
      }),
  },

  analytics: {
    pipeline: (params?: { start_date?: string; end_date?: string }) => {
      const searchParams = new URLSearchParams();
      if (params?.start_date) searchParams.set("start_date", params.start_date);
      if (params?.end_date) searchParams.set("end_date", params.end_date);
      const query = searchParams.toString();
      return fetchAPI<any>(`/analytics/pipeline${query ? `?${query}` : ""}`);
    },

    geographic: () => fetchAPI<any>("/analytics/geographic"),

    department: (department: string) =>
      fetchAPI<any>(`/analytics/department/${encodeURIComponent(department)}`),

    trends: (metric: string, period: string = "day") =>
      fetchAPI<any>(`/analytics/trends?metric=${encodeURIComponent(metric)}&period=${encodeURIComponent(period)}`),

    equity: () => fetchAPI<any>("/analytics/equity"),

    export: (format: "csv" | "json" = "json") => {
      if (format === "csv") {
        return fetch(`${API_BASE}/analytics/export?format=csv`, {
          headers: { "Content-Type": "application/json" },
        }).then((res) => res.blob());
      }
      return fetchAPI<any>("/analytics/export?format=json");
    },
  },

  reports: {
    weekly: (week: string) =>
      fetchAPI<any>(`/reports/weekly?week=${encodeURIComponent(week)}`),

    department: (department: string, start: string, end: string) =>
      fetchAPI<any>(
        `/reports/department/${encodeURIComponent(department)}?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`
      ),

    project: (projectId: string) =>
      fetchAPI<any>(`/reports/project/${projectId}`),

    schedule: (data: {
      report_type: string;
      department?: string;
      frequency?: string;
      recipients?: string[];
    }) =>
      fetchAPI<any>("/reports/schedule", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  admin: {
    users: (params?: { page?: number; size?: number; role?: string }) => {
      const searchParams = new URLSearchParams();
      if (params?.page) searchParams.set("page", String(params.page));
      if (params?.size) searchParams.set("size", String(params.size));
      if (params?.role) searchParams.set("role", params.role);
      const query = searchParams.toString();
      return fetchAPI<{
        items: any[];
        total: number;
        page: number;
        size: number;
        pages: number;
      }>(`/admin/users${query ? `?${query}` : ""}`);
    },

    changeRole: (userId: string, role: string) =>
      fetchAPI<any>(`/admin/users/${userId}/role?role=${encodeURIComponent(role)}`, {
        method: "PATCH",
      }),

    audit: (params: {
      start_date: string;
      end_date: string;
      table_name?: string;
      user_id?: string;
      page?: number;
      size?: number;
    }) => {
      const searchParams = new URLSearchParams();
      searchParams.set("start_date", params.start_date);
      searchParams.set("end_date", params.end_date);
      if (params.table_name) searchParams.set("table_name", params.table_name);
      if (params.user_id) searchParams.set("user_id", params.user_id);
      if (params.page) searchParams.set("page", String(params.page));
      if (params.size) searchParams.set("size", String(params.size));
      return fetchAPI<{ items: any[]; page: number; size: number }>(
        `/admin/audit?${searchParams.toString()}`
      );
    },

    auditRecord: (recordId: string, limit?: number) =>
      fetchAPI<any[]>(
        `/admin/audit/${recordId}${limit ? `?limit=${limit}` : ""}`
      ),

    bulkUpdateClearances: (updates: { clearance_id: string; status: string }[]) =>
      fetchAPI<any>("/admin/bulk-update-clearances", {
        method: "POST",
        body: JSON.stringify(updates),
      }),

    systemHealth: () => fetchAPI<any>("/admin/system-health"),

    clearCache: (pattern?: string) =>
      fetchAPI<any>(
        `/admin/cache${pattern ? `?pattern=${encodeURIComponent(pattern)}` : ""}`,
        { method: "DELETE" }
      ),
  },

  impact: {
    metrics: () => fetchAPI<any>("/impact/metrics"),
    timeline: () => fetchAPI<any>("/impact/timeline"),
  },

  compliance: {
    check: (projectId: string) =>
      fetchAPI<any>(`/compliance/check/${projectId}`),

    requirements: (pathway: string) =>
      fetchAPI<any>(`/compliance/requirements/${pathway}`),

    validateSequence: (projectId: string) =>
      fetchAPI<any>(`/compliance/validate-sequence/${projectId}`, {
        method: "POST",
      }),
  },

  inspections: {
    stats: () => fetchAPI<any>("/inspections/stats/overview"),
    listForProject: (projectId: string) => fetchAPI<any[]>(`/inspections/${projectId}`),
    schedule: (data: any) =>
      fetchAPI<any>("/inspections", { method: "POST", body: JSON.stringify(data) }),
    forecast: (projectId: string) => fetchAPI<any>(`/inspections/${projectId}/forecast`),
  },

  chat: {
    send: (projectId: string, message: string, history: any[]) =>
      fetchAPI<{ response: string; sources: string[] }>(`/chat/${projectId}`, {
        method: "POST",
        body: JSON.stringify({ message, conversation_history: history }),
      }),
  },
};
