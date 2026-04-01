import React, { useEffect } from "react";
import { View } from "react-native";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import "../i18n";
import OfflineBanner from "../components/OfflineBanner";
import {
  registerForPushNotifications,
  setupNotificationListeners,
} from "../services/notifications";
import { api } from "../services/api";

export default function RootLayout() {
  useEffect(() => {
    // Register for push notifications
    registerForPushNotifications().then(async (token) => {
      if (token) {
        try {
          await api.user.updatePushToken(token);
        } catch { /* silent */ }
      }
    });

    // Set up notification deep link handlers
    const cleanup = setupNotificationListeners();
    return cleanup;
  }, []);

  return (
    <View style={{ flex: 1 }}>
      <StatusBar style="dark" />
      <OfflineBanner />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: "#1e3a5f" },
          headerTintColor: "#ffffff",
          headerTitleStyle: { fontWeight: "bold" },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen
          name="project/[id]"
          options={{ title: "Project Details" }}
        />
        <Stack.Screen
          name="upload"
          options={{ title: "Upload Document", presentation: "modal" }}
        />
        <Stack.Screen
          name="create-project"
          options={{ title: "New Project", presentation: "modal" }}
        />
        <Stack.Screen
          name="what-if"
          options={{ title: "What-if Scenarios" }}
        />
      </Stack>
    </View>
  );
}
