import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  SectionList,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  TouchableOpacity,
} from "react-native";
import { api } from "../../services/api";

const STATUS_COLORS: Record<string, string> = {
  not_started: "#9ca3af",
  in_review: "#3b82f6",
  approved: "#10b981",
  conditional: "#f59e0b",
  denied: "#ef4444",
};

const STATUS_LABELS: Record<string, string> = {
  not_started: "Not Started",
  in_review: "In Review",
  approved: "Approved",
  conditional: "Conditional",
  denied: "Denied",
};

const SECTION_ORDER = ["in_review", "pending", "approved", "denied", "conditional", "not_started"];

interface Clearance {
  id: string;
  department_name: string;
  clearance_type: string;
  status: string;
  predicted_days?: number;
}

interface Project {
  id: string;
  address: string;
}

interface Section {
  title: string;
  status: string;
  data: Clearance[];
}

const FILTER_OPTIONS = ["All", "In Review", "Approved", "Pending", "Denied"];

function shortAddress(address: string): string {
  // Return first part before comma, trimmed, max 22 chars
  const parts = address.split(",");
  const short = parts[0].trim();
  return short.length > 22 ? short.slice(0, 20) + "…" : short;
}

export default function ClearancesScreen() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [clearances, setClearances] = useState<Clearance[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState("All");

  const fetchProjects = useCallback(async () => {
    const data = await api.projects.list();
    setProjects(data);
    return data;
  }, []);

  const fetchClearances = useCallback(async (projectId: string) => {
    const data = await api.clearances.list(projectId);
    setClearances(data);
  }, []);

  const loadAll = useCallback(async () => {
    try {
      setError(null);
      const projs = await fetchProjects();
      if (projs.length > 0) {
        const pid = selectedProjectId && projs.find((p: Project) => p.id === selectedProjectId)
          ? selectedProjectId
          : projs[0].id;
        setSelectedProjectId(pid);
        await fetchClearances(pid);
      } else {
        setClearances([]);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [fetchProjects, fetchClearances, selectedProjectId]);

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSelectProject = useCallback(
    async (projectId: string) => {
      setSelectedProjectId(projectId);
      setLoading(true);
      try {
        await fetchClearances(projectId);
      } catch (err: any) {
        setError(err.message || "Failed to load clearances");
      } finally {
        setLoading(false);
      }
    },
    [fetchClearances]
  );

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    loadAll();
  }, [loadAll]);

  // Filter clearances
  const filteredClearances = clearances.filter((c) => {
    if (activeFilter === "All") return true;
    if (activeFilter === "In Review") return c.status === "in_review";
    if (activeFilter === "Approved") return c.status === "approved";
    if (activeFilter === "Pending") return c.status === "not_started";
    if (activeFilter === "Denied") return c.status === "denied";
    return true;
  });

  // Group into sections
  const sectionMap: Record<string, Clearance[]> = {};
  filteredClearances.forEach((c) => {
    if (!sectionMap[c.status]) sectionMap[c.status] = [];
    sectionMap[c.status].push(c);
  });

  const sections: Section[] = SECTION_ORDER
    .filter((s) => sectionMap[s] && sectionMap[s].length > 0)
    .map((s) => ({
      title: STATUS_LABELS[s] || s,
      status: s,
      data: sectionMap[s],
    }));

  // Progress bar stats
  const approvedCount = clearances.filter((c) => c.status === "approved").length;
  const totalCount = clearances.length;
  const progressPct = totalCount > 0 ? approvedCount / totalCount : 0;

  const renderClearanceItem = ({ item }: { item: Clearance }) => {
    const statusColor = STATUS_COLORS[item.status] || "#9ca3af";
    const statusLabel = STATUS_LABELS[item.status] || item.status;
    return (
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <Text style={styles.department}>{item.department_name}</Text>
          <View style={[styles.badge, { backgroundColor: statusColor }]}>
            <Text style={styles.badgeText}>{statusLabel}</Text>
          </View>
        </View>
        <Text style={styles.type}>{item.clearance_type}</Text>
        {item.predicted_days != null && (
          <Text style={styles.predicted}>Est. {item.predicted_days} days remaining</Text>
        )}
      </View>
    );
  };

  const renderSectionHeader = ({ section }: { section: Section }) => (
    <View style={[styles.sectionHeader, { borderLeftColor: STATUS_COLORS[section.status] || "#9ca3af" }]}>
      <Text style={styles.sectionTitle}>{section.title}</Text>
      <View style={[styles.countBadge, { backgroundColor: STATUS_COLORS[section.status] || "#9ca3af" }]}>
        <Text style={styles.countText}>{section.data.length}</Text>
      </View>
    </View>
  );

  if (loading && !refreshing) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#1e3a5f" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error}</Text>
        <TouchableOpacity style={styles.retryBtn} onPress={() => { setLoading(true); loadAll(); }}>
          <Text style={styles.retryText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>Clearance Tracker</Text>
      </View>

      {/* Project selector */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.projectScroll}
      >
        {projects.map((proj) => {
          const isActive = proj.id === selectedProjectId;
          return (
            <TouchableOpacity
              key={proj.id}
              style={[styles.projectChip, isActive && styles.projectChipActive]}
              onPress={() => handleSelectProject(proj.id)}
            >
              <Text style={[styles.projectChipText, isActive && styles.projectChipTextActive]}>
                {shortAddress(proj.address)}
              </Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* Progress bar */}
      {totalCount > 0 && (
        <View style={styles.progressContainer}>
          <View style={styles.progressLabelRow}>
            <Text style={styles.progressLabel}>
              {approvedCount} of {totalCount} clearances approved
            </Text>
            <Text style={styles.progressPct}>{Math.round(progressPct * 100)}%</Text>
          </View>
          <View style={styles.progressTrack}>
            <View style={[styles.progressFill, { width: `${progressPct * 100}%` }]} />
          </View>
        </View>
      )}

      {/* Filter chips */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.filterScroll}
      >
        {FILTER_OPTIONS.map((f) => {
          const isActive = f === activeFilter;
          return (
            <TouchableOpacity
              key={f}
              style={[styles.filterChip, isActive && styles.filterChipActive]}
              onPress={() => setActiveFilter(f)}
            >
              <Text style={[styles.filterChipText, isActive && styles.filterChipTextActive]}>{f}</Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {/* Grouped list */}
      <SectionList
        sections={sections}
        keyExtractor={(item) => item.id}
        renderItem={renderClearanceItem}
        renderSectionHeader={renderSectionHeader}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No clearances match this filter</Text>
          </View>
        }
        stickySectionHeadersEnabled={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
  center: { flex: 1, justifyContent: "center", alignItems: "center", padding: 20 },
  header: { paddingHorizontal: 20, paddingTop: 60, paddingBottom: 8 },
  title: { fontSize: 28, fontWeight: "bold", color: "#1e3a5f" },

  // Project selector
  projectScroll: { paddingHorizontal: 20, paddingVertical: 10, gap: 8 },
  projectChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: "#e5e7eb",
    marginRight: 8,
  },
  projectChipActive: { backgroundColor: "#1e3a5f" },
  projectChipText: { fontSize: 13, fontWeight: "500", color: "#374151" },
  projectChipTextActive: { color: "#ffffff" },

  // Progress bar
  progressContainer: { paddingHorizontal: 20, paddingBottom: 8 },
  progressLabelRow: { flexDirection: "row", justifyContent: "space-between", marginBottom: 4 },
  progressLabel: { fontSize: 13, color: "#6b7280" },
  progressPct: { fontSize: 13, fontWeight: "600", color: "#10b981" },
  progressTrack: {
    height: 8,
    backgroundColor: "#e5e7eb",
    borderRadius: 4,
    overflow: "hidden",
  },
  progressFill: {
    height: 8,
    backgroundColor: "#10b981",
    borderRadius: 4,
  },

  // Filter chips
  filterScroll: { paddingHorizontal: 20, paddingVertical: 8, gap: 8 },
  filterChip: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#d1d5db",
    marginRight: 8,
  },
  filterChipActive: { backgroundColor: "#1e3a5f", borderColor: "#1e3a5f" },
  filterChipText: { fontSize: 13, color: "#374151" },
  filterChipTextActive: { color: "#ffffff", fontWeight: "600" },

  // Section header
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 10,
    marginTop: 8,
    borderLeftWidth: 4,
    marginLeft: 20,
    marginRight: 20,
    borderRadius: 4,
    backgroundColor: "#f3f4f6",
  },
  sectionTitle: { fontSize: 15, fontWeight: "700", color: "#374151", flex: 1 },
  countBadge: {
    minWidth: 24,
    height: 24,
    borderRadius: 12,
    paddingHorizontal: 6,
    alignItems: "center",
    justifyContent: "center",
  },
  countText: { color: "#ffffff", fontSize: 12, fontWeight: "700" },

  // Cards
  list: { paddingHorizontal: 20, paddingBottom: 30, paddingTop: 4 },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 12,
    padding: 16,
    marginBottom: 10,
    marginTop: 6,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 3,
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  department: { fontSize: 15, fontWeight: "600", color: "#374151", flex: 1 },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    marginLeft: 8,
  },
  badgeText: { color: "#ffffff", fontSize: 12, fontWeight: "600" },
  type: { fontSize: 13, color: "#6b7280", marginBottom: 4 },
  predicted: { fontSize: 12, color: "#f59e0b", fontWeight: "500" },

  // Empty / error
  empty: { alignItems: "center", marginTop: 60 },
  emptyText: { fontSize: 15, color: "#9ca3af" },
  errorText: { fontSize: 15, color: "#ef4444", textAlign: "center", marginBottom: 12 },
  retryBtn: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    backgroundColor: "#1e3a5f",
    borderRadius: 8,
  },
  retryText: { color: "#ffffff", fontWeight: "600" },
});
