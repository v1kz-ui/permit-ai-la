import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
  ScrollView,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { api } from "../../services/api";

type InspectionStatus =
  | "scheduled"
  | "completed_pass"
  | "completed_fail"
  | "cancelled"
  | "no_show";

interface Inspection {
  id: string;
  project_id: string;
  project_address?: string;
  inspection_type: string;
  status: InspectionStatus;
  scheduled_date: string | null;
  completed_date: string | null;
  inspector_name: string | null;
  failure_reasons: string[] | null;
  notes: string | null;
}

const STATUS_CONFIG: Record<
  InspectionStatus,
  { label: string; color: string; bg: string; icon: string }
> = {
  scheduled: {
    label: "Scheduled",
    color: "#2563eb",
    bg: "#dbeafe",
    icon: "calendar-clock",
  },
  completed_pass: {
    label: "Passed",
    color: "#059669",
    bg: "#d1fae5",
    icon: "check-circle",
  },
  completed_fail: {
    label: "Failed",
    color: "#dc2626",
    bg: "#fee2e2",
    icon: "close-circle",
  },
  cancelled: {
    label: "Cancelled",
    color: "#6b7280",
    bg: "#f3f4f6",
    icon: "cancel",
  },
  no_show: {
    label: "No Show",
    color: "#d97706",
    bg: "#fef3c7",
    icon: "alert-circle",
  },
};

const INSPECTION_TYPE_LABELS: Record<string, string> = {
  foundation: "Foundation",
  framing: "Framing",
  electrical: "Electrical",
  plumbing: "Plumbing",
  mechanical: "Mechanical",
  insulation: "Insulation",
  drywall: "Drywall",
  final: "Final Inspection",
};

const MOCK_INSPECTIONS: Inspection[] = [
  {
    id: "i-1",
    project_id: "p-1",
    project_address: "1234 Palisades Dr, Los Angeles",
    inspection_type: "foundation",
    status: "completed_pass",
    scheduled_date: "2026-03-15T10:00:00Z",
    completed_date: "2026-03-15T11:30:00Z",
    inspector_name: "J. Rodriguez",
    failure_reasons: null,
    notes: "Foundation meets all requirements.",
  },
  {
    id: "i-2",
    project_id: "p-1",
    project_address: "1234 Palisades Dr, Los Angeles",
    inspection_type: "framing",
    status: "scheduled",
    scheduled_date: "2026-04-05T09:00:00Z",
    completed_date: null,
    inspector_name: "M. Chen",
    failure_reasons: null,
    notes: null,
  },
  {
    id: "i-3",
    project_id: "p-2",
    project_address: "567 Sunset Blvd, Pacific Palisades",
    inspection_type: "electrical",
    status: "completed_fail",
    scheduled_date: "2026-03-28T14:00:00Z",
    completed_date: "2026-03-28T15:00:00Z",
    inspector_name: "K. Williams",
    failure_reasons: ["Panel spacing does not meet NEC 110.26", "GFCI required in kitchen"],
    notes: "Corrections required before re-inspection.",
  },
  {
    id: "i-4",
    project_id: "p-3",
    project_address: "89 Topanga Canyon Rd",
    inspection_type: "plumbing",
    status: "scheduled",
    scheduled_date: "2026-04-08T11:00:00Z",
    completed_date: null,
    inspector_name: null,
    failure_reasons: null,
    notes: null,
  },
];

const PREP_CHECKLISTS: Record<string, string[]> = {
  foundation: [
    "Ensure all rebar is in place per approved plans",
    "Clear access around perimeter for inspector",
    "Have approved structural drawings on-site",
    "Soil compaction report available",
    "Anchor bolt placement verified",
  ],
  framing: [
    "All framing lumber stamped per grade",
    "Hurricane ties and hold-downs installed",
    "Fire blocking installed per code",
    "Shear wall nailing complete",
    "Approved plans on-site",
    "Temporary bracing removed",
  ],
  electrical: [
    "All rough-in wiring complete",
    "Panel installed and labeled",
    "GFCI outlets installed in wet locations",
    "Arc-fault breakers where required",
    "Junction boxes accessible",
    "Approved plans on-site",
  ],
  plumbing: [
    "All pipes pressure-tested (air or water)",
    "Cleanouts accessible",
    "Water heater installed per code",
    "DWV system complete",
    "Approved plans on-site",
  ],
  final: [
    "All trades inspections complete and passed",
    "CO detectors installed",
    "Smoke detectors installed",
    "Address numbers visible from street",
    "Landscaping per water-efficient ordinance",
    "All corrections from prior inspections resolved",
  ],
};

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function ChecklistModal({
  inspection,
  onClose,
}: {
  inspection: Inspection;
  onClose: () => void;
}) {
  const checklist =
    PREP_CHECKLISTS[inspection.inspection_type] ||
    PREP_CHECKLISTS.final;
  const [checked, setChecked] = useState<boolean[]>(
    checklist.map(() => false)
  );
  const doneCount = checked.filter(Boolean).length;

  return (
    <View style={styles.modalOverlay}>
      <View style={styles.modalCard}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>
            {INSPECTION_TYPE_LABELS[inspection.inspection_type] ||
              inspection.inspection_type}{" "}
            Prep Checklist
          </Text>
          <TouchableOpacity
            onPress={onClose}
            accessibilityRole="button"
            accessibilityLabel="Close checklist"
          >
            <MaterialCommunityIcons name="close" size={20} color="#6b7280" />
          </TouchableOpacity>
        </View>
        <Text style={styles.modalSubtitle}>
          {doneCount}/{checklist.length} items ready
        </Text>
        <View style={styles.progressBar}>
          <View
            style={[
              styles.progressFill,
              { width: `${(doneCount / checklist.length) * 100}%` as any },
            ]}
          />
        </View>
        <ScrollView style={styles.checklistScroll}>
          {checklist.map((item, i) => (
            <TouchableOpacity
              key={i}
              style={styles.checkItem}
              onPress={() => {
                const next = [...checked];
                next[i] = !next[i];
                setChecked(next);
              }}
              accessibilityRole="checkbox"
              accessibilityState={{ checked: checked[i] }}
              accessibilityLabel={item}
            >
              <View
                style={[
                  styles.checkbox,
                  checked[i] && styles.checkboxChecked,
                ]}
              >
                {checked[i] && (
                  <MaterialCommunityIcons name="check" size={14} color="#fff" />
                )}
              </View>
              <Text
                style={[
                  styles.checkText,
                  checked[i] && styles.checkTextDone,
                ]}
              >
                {item}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
        {doneCount === checklist.length && (
          <View style={styles.allDone}>
            <MaterialCommunityIcons name="check-decagram" size={20} color="#059669" />
            <Text style={styles.allDoneText}>Ready for inspection!</Text>
          </View>
        )}
      </View>
    </View>
  );
}

function InspectionCard({
  inspection,
  onChecklist,
}: {
  inspection: Inspection;
  onChecklist: (i: Inspection) => void;
}) {
  const cfg = STATUS_CONFIG[inspection.status] || STATUS_CONFIG.scheduled;
  const isUpcoming = inspection.status === "scheduled";
  const typeLabel =
    INSPECTION_TYPE_LABELS[inspection.inspection_type] ||
    inspection.inspection_type;

  return (
    <View
      style={[styles.card, inspection.status === "completed_fail" && styles.cardFail]}
    >
      <View style={styles.cardTop}>
        <View style={[styles.statusBadge, { backgroundColor: cfg.bg }]}>
          <MaterialCommunityIcons
            name={cfg.icon as any}
            size={14}
            color={cfg.color}
          />
          <Text style={[styles.statusText, { color: cfg.color }]}>
            {cfg.label}
          </Text>
        </View>
        <Text style={styles.inspectionType}>{typeLabel}</Text>
      </View>

      {inspection.project_address && (
        <Text style={styles.address}>{inspection.project_address}</Text>
      )}

      <View style={styles.cardMeta}>
        <View style={styles.metaRow}>
          <MaterialCommunityIcons name="calendar" size={14} color="#9ca3af" />
          <Text style={styles.metaText}>
            {isUpcoming ? "Scheduled: " : "Date: "}
            {formatDate(inspection.scheduled_date || inspection.completed_date)}
          </Text>
        </View>
        {inspection.inspector_name && (
          <View style={styles.metaRow}>
            <MaterialCommunityIcons name="account" size={14} color="#9ca3af" />
            <Text style={styles.metaText}>{inspection.inspector_name}</Text>
          </View>
        )}
      </View>

      {inspection.failure_reasons && inspection.failure_reasons.length > 0 && (
        <View style={styles.failureBox}>
          <Text style={styles.failureTitle}>Corrections required:</Text>
          {inspection.failure_reasons.map((r, i) => (
            <Text key={i} style={styles.failureItem}>
              • {r}
            </Text>
          ))}
        </View>
      )}

      {isUpcoming && (
        <TouchableOpacity
          style={styles.checklistBtn}
          onPress={() => onChecklist(inspection)}
          accessibilityRole="button"
          accessibilityLabel={`View prep checklist for ${typeLabel} inspection`}
        >
          <MaterialCommunityIcons name="clipboard-list" size={16} color="#1e3a5f" />
          <Text style={styles.checklistBtnText}>View Prep Checklist</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

export default function InspectionsScreen() {
  const router = useRouter();
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeChecklist, setActiveChecklist] = useState<Inspection | null>(null);
  const [filter, setFilter] = useState<"all" | "upcoming" | "completed">("all");

  const load = useCallback(async () => {
    try {
      const data = await api.inspections.listAll();
      setInspections(data.length > 0 ? data : MOCK_INSPECTIONS);
    } catch {
      setInspections(MOCK_INSPECTIONS);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = inspections.filter((i) => {
    if (filter === "upcoming") return i.status === "scheduled";
    if (filter === "completed")
      return i.status === "completed_pass" || i.status === "completed_fail";
    return true;
  });

  const upcoming = inspections.filter((i) => i.status === "scheduled");
  const passRate =
    inspections.filter((i) => i.status === "completed_pass").length /
    Math.max(
      inspections.filter((i) =>
        ["completed_pass", "completed_fail"].includes(i.status)
      ).length,
      1
    );

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#1e3a5f" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {activeChecklist && (
        <ChecklistModal
          inspection={activeChecklist}
          onClose={() => setActiveChecklist(null)}
        />
      )}

      <FlatList
        data={filtered}
        keyExtractor={(item) => item.id}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              load();
            }}
            tintColor="#1e3a5f"
          />
        }
        ListHeaderComponent={
          <>
            {/* Header */}
            <View style={styles.header}>
              <Text style={styles.headerTitle}>Inspections</Text>
              <Text style={styles.headerSubtitle}>
                {upcoming.length} upcoming · {Math.round(passRate * 100)}% pass rate
              </Text>
            </View>

            {/* Stats row */}
            <View style={styles.statsRow}>
              {[
                { label: "Upcoming", value: upcoming.length, color: "#2563eb", bg: "#dbeafe" },
                {
                  label: "Pass Rate",
                  value: `${Math.round(passRate * 100)}%`,
                  color: "#059669",
                  bg: "#d1fae5",
                },
                {
                  label: "Need Re-Inspect",
                  value: inspections.filter((i) => i.status === "completed_fail").length,
                  color: "#dc2626",
                  bg: "#fee2e2",
                },
              ].map((s) => (
                <View
                  key={s.label}
                  style={[styles.statCard, { backgroundColor: s.bg }]}
                >
                  <Text style={[styles.statValue, { color: s.color }]}>
                    {s.value}
                  </Text>
                  <Text style={[styles.statLabel, { color: s.color }]}>
                    {s.label}
                  </Text>
                </View>
              ))}
            </View>

            {/* Filter pills */}
            <View style={styles.filterRow}>
              {(["all", "upcoming", "completed"] as const).map((f) => (
                <TouchableOpacity
                  key={f}
                  style={[styles.filterPill, filter === f && styles.filterPillActive]}
                  onPress={() => setFilter(f)}
                  accessibilityRole="button"
                  accessibilityState={{ selected: filter === f }}
                  accessibilityLabel={`Filter: ${f}`}
                >
                  <Text
                    style={[
                      styles.filterText,
                      filter === f && styles.filterTextActive,
                    ]}
                  >
                    {f.charAt(0).toUpperCase() + f.slice(1)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </>
        }
        renderItem={({ item }) => (
          <InspectionCard
            inspection={item}
            onChecklist={setActiveChecklist}
          />
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            <MaterialCommunityIcons
              name="clipboard-search-outline"
              size={48}
              color="#d1d5db"
            />
            <Text style={styles.emptyTitle}>No inspections found</Text>
            <Text style={styles.emptyText}>
              Inspections will appear here once scheduled for your projects.
            </Text>
          </View>
        }
        contentContainerStyle={styles.list}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8fafc" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  list: { paddingBottom: 32 },
  header: {
    backgroundColor: "#1e3a5f",
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 24,
  },
  headerTitle: { fontSize: 26, fontWeight: "bold", color: "#ffffff" },
  headerSubtitle: { fontSize: 14, color: "#93c5fd", marginTop: 4 },
  statsRow: {
    flexDirection: "row",
    gap: 10,
    paddingHorizontal: 20,
    paddingVertical: 16,
  },
  statCard: {
    flex: 1,
    borderRadius: 12,
    padding: 12,
    alignItems: "center",
  },
  statValue: { fontSize: 20, fontWeight: "bold" },
  statLabel: { fontSize: 11, fontWeight: "600", marginTop: 2, textAlign: "center" },
  filterRow: {
    flexDirection: "row",
    gap: 8,
    paddingHorizontal: 20,
    paddingBottom: 12,
  },
  filterPill: {
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 20,
    backgroundColor: "#e2e8f0",
  },
  filterPillActive: { backgroundColor: "#1e3a5f" },
  filterText: { fontSize: 13, fontWeight: "600", color: "#64748b" },
  filterTextActive: { color: "#ffffff" },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 14,
    marginHorizontal: 20,
    marginBottom: 12,
    padding: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  cardFail: { borderLeftWidth: 3, borderLeftColor: "#dc2626" },
  cardTop: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 8 },
  statusBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
  },
  statusText: { fontSize: 11, fontWeight: "700" },
  inspectionType: { fontSize: 15, fontWeight: "700", color: "#1e293b", flex: 1 },
  address: { fontSize: 13, color: "#64748b", marginBottom: 10 },
  cardMeta: { gap: 5, marginBottom: 10 },
  metaRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  metaText: { fontSize: 13, color: "#6b7280" },
  failureBox: {
    backgroundColor: "#fef2f2",
    borderRadius: 8,
    padding: 10,
    marginBottom: 10,
  },
  failureTitle: { fontSize: 12, fontWeight: "700", color: "#dc2626", marginBottom: 4 },
  failureItem: { fontSize: 12, color: "#dc2626", lineHeight: 18 },
  checklistBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: "#eff6ff",
    borderRadius: 8,
    alignSelf: "flex-start",
  },
  checklistBtnText: { fontSize: 13, fontWeight: "600", color: "#1e3a5f" },
  empty: { alignItems: "center", padding: 40 },
  emptyTitle: { fontSize: 16, fontWeight: "600", color: "#374151", marginTop: 12 },
  emptyText: {
    fontSize: 13,
    color: "#9ca3af",
    textAlign: "center",
    marginTop: 6,
    lineHeight: 20,
  },
  // Modal
  modalOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0,0,0,0.5)",
    zIndex: 100,
    justifyContent: "flex-end",
  },
  modalCard: {
    backgroundColor: "#fff",
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    maxHeight: "80%",
  },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 4,
  },
  modalTitle: { fontSize: 17, fontWeight: "700", color: "#1e293b", flex: 1 },
  modalSubtitle: { fontSize: 13, color: "#6b7280", marginBottom: 10 },
  progressBar: {
    height: 4,
    backgroundColor: "#e5e7eb",
    borderRadius: 2,
    marginBottom: 16,
    overflow: "hidden",
  },
  progressFill: { height: "100%", backgroundColor: "#1e3a5f", borderRadius: 2 },
  checklistScroll: { maxHeight: 320 },
  checkItem: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#f1f5f9",
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: "#d1d5db",
    justifyContent: "center",
    alignItems: "center",
    flexShrink: 0,
    marginTop: 1,
  },
  checkboxChecked: { backgroundColor: "#1e3a5f", borderColor: "#1e3a5f" },
  checkText: { fontSize: 14, color: "#374151", flex: 1, lineHeight: 20 },
  checkTextDone: { color: "#9ca3af", textDecorationLine: "line-through" },
  allDone: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 16,
    padding: 12,
    backgroundColor: "#d1fae5",
    borderRadius: 10,
  },
  allDoneText: { fontSize: 14, fontWeight: "600", color: "#059669" },
});
