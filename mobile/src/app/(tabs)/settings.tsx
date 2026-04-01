import React, { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Switch,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { useTranslation } from "react-i18next";
import { api } from "../../services/api";

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "es", label: "Español" },
  { code: "ko", label: "Korean" },
  { code: "zh", label: "Chinese" },
  { code: "fil", label: "Filipino" },
];

const APP_VERSION = "1.0.0";

const STORAGE_KEYS = {
  language: "settings:language",
  push: "settings:push",
  sms: "settings:sms",
  email: "settings:email",
};

export default function SettingsScreen() {
  const router = useRouter();
  const { i18n } = useTranslation();

  const [language, setLanguageState] = useState("en");
  const [pushEnabled, setPushState] = useState(true);
  const [smsEnabled, setSmsState] = useState(false);
  const [emailEnabled, setEmailState] = useState(true);

  const [user, setUser] = useState<{ name?: string; email?: string } | null>(null);
  const [userLoading, setUserLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // ── Load persisted settings on mount ────────────────────────────────────

  useEffect(() => {
    const loadAll = async () => {
      try {
        const [lang, push, sms, email] = await AsyncStorage.multiGet([
          STORAGE_KEYS.language,
          STORAGE_KEYS.push,
          STORAGE_KEYS.sms,
          STORAGE_KEYS.email,
        ]);
        if (lang[1] !== null) setLanguageState(lang[1]);
        if (push[1] !== null) setPushState(push[1] === "true");
        if (sms[1] !== null) setSmsState(sms[1] === "true");
        if (email[1] !== null) setEmailState(email[1] === "true");
      } catch {
        // Ignore storage errors; fall back to defaults
      }
    };
    loadAll();
  }, []);

  // ── Load user profile on mount ───────────────────────────────────────────

  useEffect(() => {
    api.user
      .me()
      .then((u) => setUser(u))
      .catch(() => setUser(null))
      .finally(() => setUserLoading(false));
  }, []);

  // ── Persist + sync helper ────────────────────────────────────────────────

  const persistAndSync = useCallback(
    async (
      lang: string,
      push: boolean,
      sms: boolean,
      email: boolean
    ) => {
      try {
        await AsyncStorage.multiSet([
          [STORAGE_KEYS.language, lang],
          [STORAGE_KEYS.push, String(push)],
          [STORAGE_KEYS.sms, String(sms)],
          [STORAGE_KEYS.email, String(email)],
        ]);
      } catch {
        // Storage failure is non-fatal
      }
      setSaving(true);
      try {
        await api.user.updatePreferences({
          language: lang,
          notification_push: push,
          notification_sms: sms,
          notification_email: email,
        });
      } catch {
        // API failure is non-fatal for the UI
      } finally {
        setSaving(false);
      }
    },
    []
  );

  // ── Toggle handlers ──────────────────────────────────────────────────────

  const setLanguage = (lang: string) => {
    setLanguageState(lang);
    i18n.changeLanguage(lang);
    persistAndSync(lang, pushEnabled, smsEnabled, emailEnabled);
  };

  const setPush = (val: boolean) => {
    setPushState(val);
    persistAndSync(language, val, smsEnabled, emailEnabled);
  };

  const setSms = (val: boolean) => {
    setSmsState(val);
    persistAndSync(language, pushEnabled, val, emailEnabled);
  };

  const setEmail = (val: boolean) => {
    setEmailState(val);
    persistAndSync(language, pushEnabled, smsEnabled, val);
  };

  // ── Logout ───────────────────────────────────────────────────────────────

  const doLogout = async () => {
    await AsyncStorage.multiRemove([
      STORAGE_KEYS.language,
      STORAGE_KEYS.push,
      STORAGE_KEYS.sms,
      STORAGE_KEYS.email,
      "cache:projects",
      "auth:token",
    ]);
    router.replace("/login");
  };

  const handleLogout = () => {
    Alert.alert("Logout", "Are you sure you want to log out?", [
      { text: "Cancel", style: "cancel" },
      { text: "Logout", style: "destructive", onPress: doLogout },
    ]);
  };

  // ── Export data ──────────────────────────────────────────────────────────

  const handleExportData = async () => {
    try {
      await api.user.exportData();
      Alert.alert("Export Requested", "Your data export will be emailed to you.");
    } catch (err: any) {
      Alert.alert("Export Failed", err.message || "Could not request data export.");
    }
  };

  // ── Delete account ───────────────────────────────────────────────────────

  const handleDeleteAccount = () => {
    Alert.alert(
      "Delete Account",
      "Are you sure you want to permanently delete your account? This cannot be undone.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete Account",
          style: "destructive",
          onPress: () => {
            Alert.alert(
              "Final Confirmation",
              "All your data will be permanently deleted. Proceed?",
              [
                { text: "Cancel", style: "cancel" },
                {
                  text: "Yes, Delete",
                  style: "destructive",
                  onPress: async () => {
                    try {
                      await api.user.deleteAccount();
                    } catch {
                      // Proceed with logout regardless
                    }
                    await doLogout();
                  },
                },
              ]
            );
          },
        },
      ]
    );
  };

  // ─────────────────────────────────────────────────────────────────────────

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Settings</Text>
        {saving && (
          <ActivityIndicator size="small" color="#f59e0b" style={styles.savingIndicator} />
        )}
      </View>

      {/* User Profile */}
      <View style={styles.section}>
        {userLoading ? (
          <ActivityIndicator size="small" color="#1e3a5f" />
        ) : user ? (
          <View style={styles.profileRow}>
            <View style={styles.avatarCircle}>
              <MaterialCommunityIcons name="account" size={28} color="#1e3a5f" />
            </View>
            <View style={styles.profileInfo}>
              {user.name ? (
                <Text style={styles.profileName}>{user.name}</Text>
              ) : null}
              {user.email ? (
                <Text style={styles.profileEmail}>{user.email}</Text>
              ) : null}
            </View>
          </View>
        ) : (
          <Text style={styles.profileEmail}>Not signed in</Text>
        )}
      </View>

      {/* Language */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Language</Text>
        <View style={styles.languageRow}>
          {LANGUAGES.map((lang) => (
            <TouchableOpacity
              key={lang.code}
              style={[
                styles.langChip,
                language === lang.code && styles.langChipActive,
              ]}
              onPress={() => setLanguage(lang.code)}
              accessibilityRole="radio"
              accessibilityState={{ selected: language === lang.code }}
              accessibilityLabel={`Language: ${lang.label}${language === lang.code ? ", currently selected" : ""}`}
            >
              <Text
                style={[
                  styles.langChipText,
                  language === lang.code && styles.langChipTextActive,
                ]}
              >
                {lang.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Notifications */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Notifications</Text>
        <View style={styles.row}>
          <Text style={styles.rowLabel}>Push Notifications</Text>
          <Switch
            value={pushEnabled}
            onValueChange={setPush}
            trackColor={{ false: "#d1d5db", true: "#1e3a5f" }}
            thumbColor="#ffffff"
            accessibilityRole="switch"
            accessibilityLabel="Push notifications"
            accessibilityState={{ checked: pushEnabled }}
          />
        </View>
        <View style={styles.row}>
          <Text style={styles.rowLabel}>SMS Notifications</Text>
          <Switch
            value={smsEnabled}
            onValueChange={setSms}
            trackColor={{ false: "#d1d5db", true: "#1e3a5f" }}
            thumbColor="#ffffff"
            accessibilityRole="switch"
            accessibilityLabel="SMS notifications"
            accessibilityState={{ checked: smsEnabled }}
          />
        </View>
        <View style={[styles.row, styles.rowLast]}>
          <Text style={styles.rowLabel}>Email Notifications</Text>
          <Switch
            value={emailEnabled}
            onValueChange={setEmail}
            trackColor={{ false: "#d1d5db", true: "#1e3a5f" }}
            thumbColor="#ffffff"
            accessibilityRole="switch"
            accessibilityLabel="Email notifications"
            accessibilityState={{ checked: emailEnabled }}
          />
        </View>
      </View>

      {/* Account */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Account</Text>
        <TouchableOpacity style={styles.row} onPress={handleExportData} activeOpacity={0.7}>
          <MaterialCommunityIcons name="export" size={20} color="#374151" style={styles.rowIcon} />
          <Text style={styles.rowLabel}>Export My Data</Text>
          <MaterialCommunityIcons name="chevron-right" size={20} color="#9ca3af" />
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.row, styles.rowLast, styles.deleteRow]}
          onPress={handleDeleteAccount}
          activeOpacity={0.7}
        >
          <MaterialCommunityIcons name="delete-outline" size={20} color="#ef4444" style={styles.rowIcon} />
          <Text style={styles.deleteRowLabel}>Delete Account</Text>
          <MaterialCommunityIcons name="chevron-right" size={20} color="#fca5a5" />
        </TouchableOpacity>
      </View>

      {/* About */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About</Text>
        <View style={[styles.row, styles.rowLast]}>
          <Text style={styles.rowLabel}>App Version</Text>
          <Text style={styles.rowValue}>{APP_VERSION}</Text>
        </View>
      </View>

      {/* Logout */}
      <TouchableOpacity
        style={styles.logoutBtn}
        onPress={handleLogout}
        activeOpacity={0.7}
        accessibilityRole="button"
        accessibilityLabel="Sign out of your account"
      >
        <MaterialCommunityIcons name="logout" size={20} color="#ef4444" />
        <Text style={styles.logoutText}>Logout</Text>
      </TouchableOpacity>

      <View style={{ height: 48 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
  header: {
    padding: 20,
    paddingTop: 60,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  title: { fontSize: 28, fontWeight: "bold", color: "#1e3a5f" },
  savingIndicator: { marginLeft: 8 },

  // Profile card
  profileRow: { flexDirection: "row", alignItems: "center" },
  avatarCircle: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: "#eff6ff",
    justifyContent: "center",
    alignItems: "center",
    marginRight: 14,
    borderWidth: 1,
    borderColor: "#bfdbfe",
  },
  profileInfo: { flex: 1 },
  profileName: { fontSize: 17, fontWeight: "700", color: "#1f2937", marginBottom: 2 },
  profileEmail: { fontSize: 14, color: "#6b7280" },

  // Section
  section: {
    backgroundColor: "#ffffff",
    marginHorizontal: 20,
    marginBottom: 16,
    borderRadius: 12,
    padding: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: "700",
    color: "#6b7280",
    textTransform: "uppercase",
    letterSpacing: 0.8,
    marginBottom: 12,
  },

  // Language
  languageRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  langChip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: "#f3f4f6",
    borderWidth: 1,
    borderColor: "#e5e7eb",
  },
  langChipActive: { backgroundColor: "#1e3a5f", borderColor: "#1e3a5f" },
  langChipText: { fontSize: 14, color: "#374151" },
  langChipTextActive: { color: "#ffffff" },

  // Row
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#f3f4f6",
  },
  rowLast: { borderBottomWidth: 0 },
  rowIcon: { marginRight: 10 },
  rowLabel: { flex: 1, fontSize: 16, color: "#374151" },
  rowValue: { fontSize: 16, color: "#6b7280" },

  // Delete row
  deleteRow: {},
  deleteRowLabel: { flex: 1, fontSize: 16, color: "#ef4444", fontWeight: "500" },

  // Logout
  logoutBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    marginHorizontal: 20,
    padding: 16,
    backgroundColor: "#ffffff",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#fecaca",
  },
  logoutText: {
    fontSize: 16,
    color: "#ef4444",
    fontWeight: "600",
    marginLeft: 8,
  },
});
