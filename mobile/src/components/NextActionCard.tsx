import React from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";

export interface NextAction {
  title: string;
  description: string;
  icon: string;
  actionLabel: string;
  onPress: () => void;
  urgent?: boolean;
}

export function deriveNextActions(
  clearances: any[],
  router: any,
  projectId: string
): NextAction[] {
  const actions: NextAction[] = [];

  const bottlenecks = clearances.filter((c) => c.is_bottleneck);
  const notStarted = clearances.filter((c) => c.status === "not_started");
  const inReview = clearances.filter((c) => c.status === "in_review");
  const allApproved =
    clearances.length > 0 && clearances.every((c) => c.status === "approved");

  if (bottlenecks.length > 0) {
    actions.push({
      title: `${bottlenecks[0].department} needs attention`,
      description: `Your ${bottlenecks[0].clearance_type} has been flagged as delayed. Consider contacting the department for an update.`,
      icon: "alert-circle-outline",
      actionLabel: "View Clearances",
      onPress: () => router.push("/(tabs)/clearances"),
      urgent: true,
    });
  }

  if (notStarted.length > 0) {
    actions.push({
      title: `${notStarted.length} clearance${notStarted.length > 1 ? "s" : ""} not yet started`,
      description: `Uploading required documents can help ${notStarted[0].department} begin their review sooner.`,
      icon: "upload",
      actionLabel: "Upload Documents",
      onPress: () =>
        router.push({ pathname: "/upload", params: { projectId } }),
    });
  }

  if (inReview.length > 0 && actions.length < 2) {
    actions.push({
      title: `${inReview.length} clearance${inReview.length > 1 ? "s" : ""} under review`,
      description:
        "These are actively being processed. You'll receive a notification when there's an update.",
      icon: "clock-outline",
      actionLabel: "Track Progress",
      onPress: () => router.push("/(tabs)/clearances"),
    });
  }

  if (allApproved) {
    actions.push({
      title: "All clearances approved!",
      description:
        "Great news — your permit is nearly ready. The next step is scheduling your final inspection.",
      icon: "check-decagram",
      actionLabel: "Ask the Assistant",
      onPress: () => router.push("/(tabs)/chat"),
    });
  }

  return actions.slice(0, 2);
}

interface Props {
  actions: NextAction[];
}

export default function NextActionCard({ actions }: Props) {
  if (actions.length === 0) return null;

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>What's Next</Text>
      {actions.map((action, i) => (
        <TouchableOpacity
          key={i}
          style={[styles.card, action.urgent && styles.cardUrgent]}
          onPress={action.onPress}
          activeOpacity={0.75}
          accessibilityRole="button"
          accessibilityLabel={`${action.title}. ${action.description}. Tap to ${action.actionLabel.toLowerCase()}.`}
        >
          <View
            style={[
              styles.iconCircle,
              action.urgent ? styles.iconCircleUrgent : styles.iconCircleDefault,
            ]}
          >
            <MaterialCommunityIcons
              name={action.icon as any}
              size={20}
              color={action.urgent ? "#ef4444" : "#1e3a5f"}
            />
          </View>
          <View style={styles.content}>
            <Text style={[styles.title, action.urgent && styles.titleUrgent]}>
              {action.title}
            </Text>
            <Text style={styles.description}>{action.description}</Text>
            <Text style={[styles.link, action.urgent && styles.linkUrgent]}>
              {action.actionLabel} →
            </Text>
          </View>
        </TouchableOpacity>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginHorizontal: 20, marginBottom: 16 },
  heading: {
    fontSize: 15,
    fontWeight: "700",
    color: "#374151",
    marginBottom: 10,
  },
  card: {
    backgroundColor: "#f0f9ff",
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
    flexDirection: "row",
    alignItems: "flex-start",
    borderWidth: 1,
    borderColor: "#bae6fd",
  },
  cardUrgent: {
    backgroundColor: "#fff7f7",
    borderColor: "#fecaca",
  },
  iconCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: "center",
    alignItems: "center",
    marginRight: 12,
    flexShrink: 0,
  },
  iconCircleDefault: { backgroundColor: "#dbeafe" },
  iconCircleUrgent: { backgroundColor: "#fee2e2" },
  content: { flex: 1 },
  title: {
    fontSize: 14,
    fontWeight: "700",
    color: "#1e3a5f",
    lineHeight: 20,
  },
  titleUrgent: { color: "#dc2626" },
  description: {
    fontSize: 13,
    color: "#6b7280",
    marginTop: 4,
    lineHeight: 18,
  },
  link: {
    fontSize: 13,
    color: "#2563eb",
    fontWeight: "600",
    marginTop: 8,
  },
  linkUrgent: { color: "#dc2626" },
});
