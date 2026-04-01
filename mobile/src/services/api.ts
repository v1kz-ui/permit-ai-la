import { offlineCache } from "../lib/offlineCache";
import { offlineQueue } from "../lib/offlineQueue";

const API_BASE = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/** Thrown when a mutation was saved to the offline queue instead of sent live. */
export class OfflineQueuedError extends Error {
  constructor(message = "Saved offline, will sync when connected") {
    super(message);
    this.name = "OfflineQueuedError";
  }
}

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

/** Try cache first; on miss, fetch from network and populate cache. */
async function withCache<T>(
  key: string,
  fetcher: () => Promise<T>,
  ttl?: number
): Promise<T> {
  const cached = await offlineCache.get<T>(key);
  if (cached !== null) return cached;
  const data = await fetcher();
  await offlineCache.set(key, data, ttl);
  return data;
}

export const api = {
  projects: {
    list: () =>
      withCache<any[]>("projects:list", () => fetchAPI<any[]>("/projects")),

    get: (id: string) =>
      withCache<any>(`projects:${id}`, () => fetchAPI<any>(`/projects/${id}`)),

    create: async (data: any): Promise<any> => {
      try {
        const result = await fetchAPI<any>("/projects", {
          method: "POST",
          body: JSON.stringify(data),
        });
        // Invalidate list cache so next fetch is fresh
        await offlineCache.invalidate("projects:list");
        return result;
      } catch (err: any) {
        // Network-level failure — queue for later
        if (
          err instanceof TypeError ||
          err?.message?.includes("Network request failed")
        ) {
          await offlineQueue.enqueue("POST", "/projects", data);
          throw new OfflineQueuedError();
        }
        throw err;
      }
    },
  },

  clearances: {
    list: (projectId: string) =>
      withCache<any[]>(
        `clearances:${projectId}`,
        () => fetchAPI<any[]>(`/clearances?project_id=${projectId}`),
        2 * 60 * 1000 // 2 minutes
      ),
  },

  chat: {
    send: (projectId: string, message: string, history: any[]) =>
      fetchAPI<any>(`/chat/${projectId}`, {
        method: "POST",
        body: JSON.stringify({ message, history }),
      }),
  },

  documents: {
    list: (projectId: string) =>
      fetchAPI<any[]>(`/documents/${projectId}`),

    upload: async (projectId: string, file: any, type: string) => {
      const formData = new FormData();
      formData.append("file", {
        uri: file.uri,
        name: file.name || "upload",
        type: file.mimeType || "application/octet-stream",
      } as any);
      formData.append("document_type", type);

      const response = await fetch(
        `${API_BASE}/documents/upload/${projectId}`,
        {
          method: "POST",
          body: formData,
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `Upload failed: ${response.status}`);
      }

      return response.json();
    },

    delete: (id: string) =>
      fetchAPI<any>(`/documents/${id}`, { method: "DELETE" }),
  },

  pathfinder: {
    timeline: (projectId: string) =>
      fetchAPI<any>(`/pathfinder/timeline/${projectId}`),

    quickAnalysis: (data: any) =>
      fetchAPI<any>("/pathfinder/quick-analysis", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    whatIf: (data: {
      address: string;
      original_sqft: number;
      proposed_sqft: number;
      stories?: number;
      override_coastal_zone?: boolean | null;
      override_hillside?: boolean | null;
      override_historic?: boolean | null;
      override_fire_severity?: boolean | null;
    }) =>
      fetchAPI<any>("/pathfinder/what-if", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  parcels: {
    get: (apn: string) => fetchAPI<any>(`/parcels/${apn}`),
  },

  inspections: {
    listAll: () =>
      withCache<any[]>(
        "inspections:all",
        () => fetchAPI<any[]>("/inspections/all"),
        5 * 60 * 1000 // 5 minutes
      ),

    listForProject: (projectId: string) =>
      withCache<any[]>(
        `inspections:${projectId}`,
        () => fetchAPI<any[]>(`/inspections/${projectId}`),
        2 * 60 * 1000
      ),

    prepChecklist: (projectId: string, inspectionType: string) =>
      fetchAPI<{ items: string[] }>(
        `/inspections/${projectId}/prep-checklist?type=${encodeURIComponent(inspectionType)}`
      ),

    forecast: (projectId: string) =>
      fetchAPI<any>(`/inspections/${projectId}/forecast`),
  },

  user: {
    me: () => fetchAPI<any>("/users/me"),

    updatePreferences: (prefs: any) =>
      fetchAPI<any>("/users/me/notification-preferences", {
        method: "PUT",
        body: JSON.stringify(prefs),
      }),

    updatePushToken: (token: string) =>
      fetchAPI<any>("/users/me", { method: "PATCH", body: JSON.stringify({ push_token: token }) }),

    exportData: () => fetchAPI<any>("/users/me/data-export"),

    deleteAccount: () =>
      fetchAPI<void>("/users/me/account", { method: "DELETE" }),
  },
};
