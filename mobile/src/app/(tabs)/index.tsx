import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { useRouter } from "expo-router";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { api } from "../../services/api";
import OnboardingFlow, { ONBOARDING_KEY } from "../../components/OnboardingFlow";
import { useTranslation } from "react-i18next";

const PATHWAY_COLORS: Record<string, string> = {
  standard: "#3b82f6",
  expedited: "#f59e0b",
  emergency: "#ef4444",
};

interface Project {
  id: string;
  address: string;
  pathway?: string;
  status?: string;
  progress?: number;
}

export default function HomeScreen() {
  const router = useRouter();
  const { t } = useTranslation();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showOnboarding, setShowOnboarding] = useState<boolean | null>(null);

  useEffect(() => {
    AsyncStorage.getItem(ONBOARDING_KEY).then((val) => {
      setShowOnboarding(val !== "true");
    });
  }, []);

  const fetchProjects = useCallback(async () => {
    try {
      setError(null);
      const data = await api.projects.list();
      setProjects(data);
    } catch (err: any) {
      setError(err.message || "Failed to load projects");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchProjects();
  }, [fetchProjects]);

  const renderProject = ({ item }: { item: Project }) => {
    const pathwayColor = PATHWAY_COLORS[item.pathway || ""] || "#6b7280";
    const progress = item.progress ?? 0;

    const progressPct = Math.round(progress * 100);
    const a11yLabel = [
      item.address || "Unknown Address",
      item.pathway ? `${item.pathway} pathway` : null,
      item.status ? `status: ${item.status.replace(/_/g, " ")}` : null,
      `${progressPct}% complete`,
      "Tap to view details",
    ]
      .filter(Boolean)
      .join(", ");

    return (
      <TouchableOpacity
        style={styles.card}
        onPress={() => router.push(`/project/${item.id}`)}
        activeOpacity={0.7}
        accessibilityRole="button"
        accessibilityLabel={a11yLabel}
      >
        <Text style={styles.cardTitle}>{item.address || "Unknown Address"}</Text>
        <View style={styles.cardMeta}>
          {item.pathway && (
            <View
              style={[styles.badge, { backgroundColor: pathwayColor }]}
              accessibilityLabel={`Pathway: ${item.pathway}`}
            >
              <Text style={styles.badgeText}>{item.pathway}</Text>
            </View>
          )}
          {item.status && (
            <Text style={styles.statusText} accessibilityLabel={`Status: ${item.status.replace(/_/g, " ")}`}>
              {item.status}
            </Text>
          )}
        </View>
        <View
          style={styles.progressContainer}
          accessibilityRole="progressbar"
          accessibilityValue={{ min: 0, max: 100, now: progressPct }}
          accessibilityLabel={`Permit progress: ${progressPct} percent`}
        >
          <View style={styles.progressBar}>
            <View
              style={[
                styles.progressFill,
                { width: `${Math.min(progress * 100, 100)}%` },
              ]}
            />
          </View>
          <Text style={styles.progressText}>
            {progressPct}%
          </Text>
        </View>
      </TouchableOpacity>
    );
  };

  // Onboarding check not yet loaded
  if (showOnboarding === null) return null;

  // Show onboarding for new users
  if (showOnboarding) {
    return <OnboardingFlow onComplete={() => setShowOnboarding(false)} />;
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#1e3a5f" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>{t("home.title")}</Text>
        <Text style={styles.subtitle}>{t("home.subtitle")}</Text>
      </View>

      {error ? (
        <View style={styles.errorContainer}>
          <MaterialCommunityIcons name="cloud-off-outline" size={48} color="#f59e0b" />
          <Text style={styles.errorTitle}>{t("home.errorTitle")}</Text>
          <Text style={styles.errorSubtext}>{t("home.errorSubtext")}</Text>
          <TouchableOpacity
            style={styles.retryBtn}
            onPress={fetchProjects}
            accessibilityRole="button"
            accessibilityLabel="Try loading projects again"
          >
            <Text style={styles.retryText}>{t("home.tryAgain")}</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={projects}
          keyExtractor={(item) => item.id}
          renderItem={renderProject}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
          }
          ListEmptyComponent={
            <View style={styles.empty}>
              <MaterialCommunityIcons name="home-heart" size={56} color="#1e3a5f" />
              <Text style={styles.emptyTitle}>{t("home.noProjects")}</Text>
              <Text style={styles.emptyText}>{t("home.noProjectsHelp")}</Text>
              <TouchableOpacity
                style={styles.emptyBtn}
                onPress={() => router.push("/create-project")}
                accessibilityRole="button"
                accessibilityLabel={t("home.createA11y")}
              >
                <Text style={styles.emptyBtnText}>{t("home.startFirst")}</Text>
              </TouchableOpacity>
            </View>
          }
        />
      )}

      {/* Floating action button */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => router.push("/create-project")}
        activeOpacity={0.8}
        accessibilityRole="button"
        accessibilityLabel="Create new rebuild project"
      >
        <MaterialCommunityIcons name="plus" size={28} color="#ffffff" />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  header: { padding: 20, paddingTop: 60 },
  title: { fontSize: 28, fontWeight: "bold", color: "#1e3a5f" },
  subtitle: { fontSize: 16, color: "#6b7280", marginTop: 4 },
  list: { paddingHorizontal: 20, paddingBottom: 100 },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardTitle: { fontSize: 18, fontWeight: "600", color: "#374151" },
  cardMeta: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 8,
    gap: 8,
  },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 12,
  },
  badgeText: {
    color: "#ffffff",
    fontSize: 12,
    fontWeight: "600",
    textTransform: "capitalize",
  },
  statusText: { fontSize: 14, color: "#6b7280", textTransform: "capitalize" },
  progressContainer: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 12,
  },
  progressBar: {
    flex: 1,
    height: 6,
    backgroundColor: "#e5e7eb",
    borderRadius: 3,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    backgroundColor: "#1e3a5f",
    borderRadius: 3,
  },
  progressText: {
    marginLeft: 10,
    fontSize: 13,
    color: "#6b7280",
    fontWeight: "500",
  },
  empty: { alignItems: "center", marginTop: 60, paddingHorizontal: 40 },
  emptyTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: "#1e3a5f",
    marginTop: 16,
    textAlign: "center",
  },
  emptyText: {
    fontSize: 15,
    color: "#6b7280",
    marginTop: 8,
    textAlign: "center",
    lineHeight: 22,
  },
  emptyBtn: {
    marginTop: 24,
    backgroundColor: "#1e3a5f",
    paddingHorizontal: 28,
    paddingVertical: 14,
    borderRadius: 12,
  },
  emptyBtnText: { color: "#ffffff", fontWeight: "700", fontSize: 16 },
  errorContainer: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 40,
    marginTop: 40,
  },
  errorTitle: {
    fontSize: 18,
    fontWeight: "600",
    color: "#374151",
    marginTop: 16,
    textAlign: "center",
  },
  errorSubtext: {
    fontSize: 14,
    color: "#6b7280",
    marginTop: 8,
    textAlign: "center",
    lineHeight: 20,
  },
  retryBtn: {
    marginTop: 20,
    paddingHorizontal: 24,
    paddingVertical: 12,
    backgroundColor: "#1e3a5f",
    borderRadius: 10,
  },
  retryText: { color: "#ffffff", fontWeight: "600", fontSize: 15 },
  fab: {
    position: "absolute",
    bottom: 90,
    right: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "#f59e0b",
    justifyContent: "center",
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 6,
    elevation: 6,
  },
});
