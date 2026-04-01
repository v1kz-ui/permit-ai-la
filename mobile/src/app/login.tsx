import React, { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  StatusBar,
} from "react-native";
import { useRouter } from "expo-router";
import { MaterialCommunityIcons } from "@expo/vector-icons";

export default function LoginScreen() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleSignIn = async () => {
    setLoading(true);
    // Mock login — replace with real Angeleno ID OAuth flow
    setTimeout(() => {
      setLoading(false);
      router.replace("/(tabs)");
    }, 1200);
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />

      {/* Logo / Branding area */}
      <View style={styles.logoArea}>
        <View style={styles.logoCircle}>
          <MaterialCommunityIcons name="city-variant" size={56} color="#ffffff" />
        </View>
        <Text style={styles.cityLabel}>CITY OF LOS ANGELES</Text>
      </View>

      {/* Title block */}
      <View style={styles.titleBlock}>
        <Text style={styles.appTitle}>PermitAI LA</Text>
        <Text style={styles.appSubtitle}>Fire Rebuild Permit Tracker</Text>
        <Text style={styles.tagline}>
          Helping Angelenos navigate the rebuild permit process after the 2025 fires.
        </Text>
      </View>

      {/* Sign-in button */}
      <View style={styles.actionBlock}>
        <TouchableOpacity
          style={[styles.signInBtn, loading && styles.signInBtnLoading]}
          onPress={handleSignIn}
          disabled={loading}
          activeOpacity={0.85}
        >
          {loading ? (
            <ActivityIndicator size="small" color="#1e3a5f" />
          ) : (
            <>
              <MaterialCommunityIcons name="shield-account" size={22} color="#1e3a5f" />
              <Text style={styles.signInBtnText}>Sign in with Angeleno ID</Text>
            </>
          )}
        </TouchableOpacity>

        <Text style={styles.disclaimer}>
          Your information is protected by the City of Los Angeles privacy policy.
        </Text>
      </View>

      {/* Footer */}
      <Text style={styles.footer}>Powered by PermitAI  v1.0.0</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#1e3a5f",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 32,
    paddingTop: 80,
    paddingBottom: 48,
  },

  // Logo
  logoArea: { alignItems: "center" },
  logoCircle: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: "rgba(255,255,255,0.15)",
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 14,
    borderWidth: 2,
    borderColor: "rgba(255,255,255,0.3)",
  },
  cityLabel: {
    color: "rgba(255,255,255,0.6)",
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 2,
  },

  // Title
  titleBlock: { alignItems: "center" },
  appTitle: {
    fontSize: 42,
    fontWeight: "900",
    color: "#ffffff",
    letterSpacing: -1,
  },
  appSubtitle: {
    fontSize: 17,
    color: "#f59e0b",
    fontWeight: "600",
    marginTop: 6,
    marginBottom: 20,
  },
  tagline: {
    fontSize: 15,
    color: "rgba(255,255,255,0.65)",
    textAlign: "center",
    lineHeight: 22,
    maxWidth: 280,
  },

  // Action
  actionBlock: { width: "100%", alignItems: "center" },
  signInBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#ffffff",
    borderRadius: 14,
    paddingVertical: 16,
    paddingHorizontal: 28,
    width: "100%",
    gap: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 6,
  },
  signInBtnLoading: { opacity: 0.75 },
  signInBtnText: {
    fontSize: 17,
    fontWeight: "700",
    color: "#1e3a5f",
  },
  disclaimer: {
    marginTop: 16,
    fontSize: 12,
    color: "rgba(255,255,255,0.45)",
    textAlign: "center",
    lineHeight: 18,
  },

  // Footer
  footer: {
    fontSize: 12,
    color: "rgba(255,255,255,0.3)",
    letterSpacing: 0.5,
  },
});
