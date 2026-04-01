import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useNetworkStatus } from "../lib/useNetworkStatus";

export default function OfflineBanner() {
  const { isOnline, justReconnected } = useNetworkStatus();

  if (justReconnected) {
    return (
      <View
        style={[styles.banner, styles.reconnectedBanner]}
        accessibilityRole="alert"
        accessibilityLabel="Back online. All changes have been synced."
      >
        <MaterialCommunityIcons name="check-circle-outline" size={16} color="#065f46" />
        <Text style={[styles.text, styles.reconnectedText]}>
          Back online — changes synced
        </Text>
      </View>
    );
  }

  if (isOnline) return null;

  return (
    <View
      style={styles.banner}
      accessibilityRole="alert"
      accessibilityLabel="You are offline. Changes will sync automatically when you reconnect."
    >
      <MaterialCommunityIcons name="wifi-off" size={16} color="#92400e" />
      <Text style={styles.text}>You're offline — changes will sync when reconnected</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    backgroundColor: "#fef3c7",
    borderBottomWidth: 1,
    borderBottomColor: "#fde68a",
    paddingVertical: 8,
    paddingHorizontal: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  reconnectedBanner: {
    backgroundColor: "#d1fae5",
    borderBottomColor: "#a7f3d0",
  },
  text: {
    fontSize: 13,
    color: "#92400e",
    fontWeight: "500",
    flex: 1,
  },
  reconnectedText: {
    color: "#065f46",
  },
});
