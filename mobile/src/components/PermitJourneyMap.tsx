import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";

const PHASES = [
  { key: "application", label: "Application", icon: "file-document-outline" as const },
  { key: "clearances", label: "Clearances", icon: "clipboard-check-outline" as const },
  { key: "plan_review", label: "Plan Review", icon: "magnify" as const },
  { key: "inspection", label: "Inspection", icon: "shield-check-outline" as const },
  { key: "permit_issued", label: "Permit\nIssued", icon: "check-decagram" as const },
];

interface Props {
  currentPhase: string;
  completedPhases: string[];
}

export function deriveCurrentPhase(clearances: any[]): string {
  if (!clearances || clearances.length === 0) return "application";
  if (clearances.every((c) => c.status === "approved")) return "inspection";
  return "clearances";
}

export function deriveCompletedPhases(clearances: any[]): string[] {
  const completed = ["application"];
  if (clearances.length > 0 && clearances.every((c) => c.status === "approved")) {
    completed.push("clearances", "plan_review");
  }
  return completed;
}

export default function PermitJourneyMap({ currentPhase, completedPhases }: Props) {
  const currentIndex = PHASES.findIndex((p) => p.key === currentPhase);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Your Permit Journey</Text>
      <View style={styles.timeline}>
        {PHASES.map((phase, i) => {
          const isCompleted = completedPhases.includes(phase.key);
          const isCurrent = phase.key === currentPhase;

          return (
            <View key={phase.key} style={styles.step}>
              <View style={styles.iconRow}>
                {i > 0 && (
                  <View
                    style={[
                      styles.connector,
                      isCompleted ? styles.connectorActive : styles.connectorInactive,
                    ]}
                  />
                )}
                <View
                  style={[
                    styles.circle,
                    isCompleted && styles.circleCompleted,
                    isCurrent && styles.circleCurrent,
                    !isCompleted && !isCurrent && styles.circlePending,
                  ]}
                  accessibilityRole="text"
                  accessibilityLabel={`${phase.label.replace("\n", " ")}: ${
                    isCompleted ? "completed" : isCurrent ? "in progress" : "upcoming"
                  }`}
                >
                  <MaterialCommunityIcons
                    name={isCompleted ? "check" : phase.icon}
                    size={14}
                    color={isCompleted ? "#ffffff" : isCurrent ? "#1e3a5f" : "#9ca3af"}
                  />
                </View>
              </View>
              <Text
                style={[
                  styles.label,
                  isCurrent && styles.labelCurrent,
                  isCompleted && styles.labelCompleted,
                ]}
              >
                {phase.label}
              </Text>
            </View>
          );
        })}
      </View>

      {currentIndex >= 0 && (
        <View style={styles.progressInfo}>
          <Text style={styles.progressText}>
            Step {currentIndex + 1} of {PHASES.length}
          </Text>
          <View style={styles.progressBarOuter}>
            <View
              style={[
                styles.progressBarInner,
                { width: `${((currentIndex + 1) / PHASES.length) * 100}%` as any },
              ]}
            />
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#ffffff",
    borderRadius: 12,
    padding: 16,
    marginHorizontal: 20,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 3,
  },
  title: {
    fontSize: 15,
    fontWeight: "600",
    color: "#374151",
    marginBottom: 16,
  },
  timeline: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
  },
  step: { alignItems: "center", flex: 1 },
  iconRow: {
    alignItems: "center",
    position: "relative",
    width: "100%",
    height: 34,
    justifyContent: "center",
  },
  connector: {
    position: "absolute",
    left: 0,
    right: "50%",
    top: 16,
    height: 2,
  },
  connectorActive: { backgroundColor: "#10b981" },
  connectorInactive: { backgroundColor: "#e5e7eb" },
  circle: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: "center",
    alignItems: "center",
    zIndex: 1,
  },
  circleCompleted: { backgroundColor: "#10b981" },
  circleCurrent: {
    backgroundColor: "#dbeafe",
    borderWidth: 2,
    borderColor: "#1e3a5f",
  },
  circlePending: {
    backgroundColor: "#f3f4f6",
    borderWidth: 1,
    borderColor: "#d1d5db",
  },
  label: {
    fontSize: 9,
    color: "#9ca3af",
    marginTop: 6,
    textAlign: "center",
    lineHeight: 12,
  },
  labelCurrent: { color: "#1e3a5f", fontWeight: "700" },
  labelCompleted: { color: "#10b981", fontWeight: "500" },
  progressInfo: {
    marginTop: 14,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: "#f3f4f6",
  },
  progressText: {
    fontSize: 12,
    color: "#6b7280",
    marginBottom: 6,
    textAlign: "center",
  },
  progressBarOuter: {
    height: 4,
    backgroundColor: "#e5e7eb",
    borderRadius: 2,
    overflow: "hidden",
  },
  progressBarInner: {
    height: "100%",
    backgroundColor: "#1e3a5f",
    borderRadius: 2,
  },
});
