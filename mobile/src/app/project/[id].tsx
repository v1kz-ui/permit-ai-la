import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { api } from "../../services/api";
import PermitJourneyMap, {
  deriveCurrentPhase,
  deriveCompletedPhases,
} from "../../components/PermitJourneyMap";
import NextActionCard, { deriveNextActions } from "../../components/NextActionCard";

const STATUS_COLORS: Record<string, string> = {
  not_started: "#9ca3af",
  in_review: "#3b82f6",
  approved: "#10b981",
  conditional: "#f59e0b",
  denied: "#ef4444",
};

const PATHWAY_COLORS: Record<string, string> = {
  standard: "#3b82f6",
  expedited: "#f59e0b",
  emergency: "#ef4444",
};

export default function ProjectDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const [project, setProject] = useState<any>(null);
  const [clearances, setClearances] = useState<any[]>([]);
  const [timeline, setTimeline] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      api.projects.get(id),
      api.clearances.list(id),
      api.pathfinder.timeline(id).catch(() => null),
    ])
      .then(([proj, clr, tl]) => {
        setProject(proj);
        setClearances(clr);
        setTimeline(tl);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#1e3a5f" />
      </View>
    );
  }

  if (!project) {
    return (
      <View style={styles.center}>
        <MaterialCommunityIcons name="file-search-outline" size={52} color="#9ca3af" />
        <Text style={[styles.errorText, { color: "#374151", marginTop: 14, fontSize: 18, fontWeight: "600" }]}>
          We couldn't find this project
        </Text>
        <Text style={{ fontSize: 14, color: "#6b7280", marginTop: 8, textAlign: "center", paddingHorizontal: 40, lineHeight: 20 }}>
          It may have been moved or the link might be outdated. Try going back to your project list.
        </Text>
        <TouchableOpacity
          style={{ marginTop: 20, paddingHorizontal: 24, paddingVertical: 12, backgroundColor: "#1e3a5f", borderRadius: 10 }}
          onPress={() => router.back()}
          accessibilityRole="button"
          accessibilityLabel="Go back to project list"
        >
          <Text style={{ color: "#fff", fontWeight: "600", fontSize: 15 }}>Go Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const statusCounts: Record<string, number> = {};
  clearances.forEach((c) => {
    statusCounts[c.status] = (statusCounts[c.status] || 0) + 1;
  });

  const pathwayColor = PATHWAY_COLORS[project.pathway] || "#3b82f6";

  return (
    <ScrollView style={styles.container}>
      {/* Back button */}
      <View style={styles.topBar}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.backBtn}
          accessibilityRole="button"
          accessibilityLabel="Go back to project list"
        >
          <MaterialCommunityIcons name="arrow-left" size={24} color="#1e3a5f" />
          <Text style={styles.backText}>Back</Text>
        </TouchableOpacity>
      </View>

      {/* Project header */}
      <View style={styles.header}>
        <Text style={styles.address} accessibilityRole="header">
          {project.address || "Unknown Address"}
        </Text>
        <View style={styles.badges}>
          {project.pathway && (
            <View
              style={[styles.badge, { backgroundColor: pathwayColor }]}
              accessibilityLabel={`Pathway: ${project.pathway}`}
            >
              <Text style={styles.badgeText}>{project.pathway}</Text>
            </View>
          )}
          {project.status && (
            <View
              style={[styles.badge, { backgroundColor: "#6b7280" }]}
              accessibilityLabel={`Status: ${project.status.replace(/_/g, " ")}`}
            >
              <Text style={styles.badgeText}>{project.status}</Text>
            </View>
          )}
        </View>
      </View>

      {/* Permit journey map */}
      <PermitJourneyMap
        currentPhase={deriveCurrentPhase(clearances)}
        completedPhases={deriveCompletedPhases(clearances)}
      />

      {/* Next actions */}
      <NextActionCard actions={deriveNextActions(clearances, router, id!)} />

      {/* Clearance summary */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Clearance Summary</Text>
        {Object.keys(statusCounts).length === 0 ? (
          <Text style={styles.muted}>No clearances yet</Text>
        ) : (
          <View style={styles.summaryRow}>
            {Object.entries(statusCounts).map(([status, count]) => (
              <View key={status} style={styles.summaryItem}>
                <View
                  style={[
                    styles.dot,
                    { backgroundColor: STATUS_COLORS[status] || "#9ca3af" },
                  ]}
                />
                <Text style={styles.summaryCount}>{count}</Text>
                <Text style={styles.summaryLabel}>
                  {status.replace(/_/g, " ")}
                </Text>
              </View>
            ))}
          </View>
        )}
      </View>

      {/* Timeline */}
      {timeline && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Timeline Estimate</Text>
          <Text style={styles.timelineValue}>
            {timeline.estimated_days
              ? `~${timeline.estimated_days} days`
              : timeline.estimated_completion || "Calculating..."}
          </Text>
        </View>
      )}

      {/* Actions */}
      <TouchableOpacity
        style={styles.primaryBtn}
        onPress={() => router.push({ pathname: "/upload", params: { projectId: id } })}
        accessibilityRole="button"
        accessibilityLabel="Upload a document for this project"
      >
        <MaterialCommunityIcons name="upload" size={20} color="#ffffff" />
        <Text style={styles.primaryBtnText}>Upload Document</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={styles.secondaryBtn}
        onPress={() => router.push("/(tabs)/clearances")}
        accessibilityRole="button"
        accessibilityLabel="View all clearances for this project"
      >
        <MaterialCommunityIcons name="clipboard-check" size={20} color="#1e3a5f" />
        <Text style={styles.secondaryBtnText}>View All Clearances</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={[styles.secondaryBtn, { marginTop: 12 }]}
        onPress={() =>
          router.push({
            pathname: "/what-if",
            params: {
              address: project.address || "",
              original_sqft: String(project.original_sqft || project.sqft || 1000),
              proposed_sqft: String(project.proposed_sqft || project.sqft || 1200),
            },
          })
        }
        accessibilityRole="button"
        accessibilityLabel="Run what-if scenario analysis"
      >
        <MaterialCommunityIcons name="chart-timeline-variant" size={20} color="#1e3a5f" />
        <Text style={styles.secondaryBtnText}>What-if Scenarios</Text>
      </TouchableOpacity>

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  errorText: { fontSize: 16, color: "#ef4444" },
  topBar: { paddingTop: 56, paddingHorizontal: 16 },
  backBtn: { flexDirection: "row", alignItems: "center" },
  backText: { fontSize: 16, color: "#1e3a5f", marginLeft: 4, fontWeight: "500" },
  header: { padding: 20, paddingTop: 12 },
  address: { fontSize: 24, fontWeight: "bold", color: "#1e3a5f" },
  badges: { flexDirection: "row", marginTop: 10, gap: 8 },
  badge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  badgeText: { color: "#ffffff", fontSize: 13, fontWeight: "600", textTransform: "capitalize" },
  card: {
    backgroundColor: "#ffffff",
    marginHorizontal: 20,
    marginBottom: 16,
    borderRadius: 12,
    padding: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardTitle: { fontSize: 16, fontWeight: "600", color: "#374151", marginBottom: 12 },
  muted: { fontSize: 14, color: "#9ca3af" },
  summaryRow: { flexDirection: "row", flexWrap: "wrap", gap: 16 },
  summaryItem: { alignItems: "center" },
  dot: { width: 12, height: 12, borderRadius: 6, marginBottom: 4 },
  summaryCount: { fontSize: 20, fontWeight: "bold", color: "#374151" },
  summaryLabel: { fontSize: 11, color: "#6b7280", textTransform: "capitalize" },
  timelineValue: { fontSize: 22, fontWeight: "bold", color: "#f59e0b" },
  primaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#1e3a5f",
    marginHorizontal: 20,
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  primaryBtnText: { color: "#ffffff", fontSize: 16, fontWeight: "600", marginLeft: 8 },
  secondaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#ffffff",
    marginHorizontal: 20,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#1e3a5f",
  },
  secondaryBtnText: { color: "#1e3a5f", fontSize: 16, fontWeight: "600", marginLeft: 8 },
});
