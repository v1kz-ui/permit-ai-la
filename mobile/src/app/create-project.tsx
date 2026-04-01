import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { useRouter } from "expo-router";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { api } from "../services/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface ParcelFlags {
  coastal: boolean;
  hillside: boolean;
  fire_zone: boolean;
  historic: boolean;
}

interface PathwayResult {
  pathway: string;
  estimated_days: number;
  key_constraints: string[];
  what_if_hints?: string[];
}

// ─── Constants ────────────────────────────────────────────────────────────────

const PATHWAY_COLORS: Record<string, string> = {
  EO1: "#16a34a",
  EO8: "#f59e0b",
  Standard: "#3b82f6",
};

const PATHWAY_LABELS: Record<string, string> = {
  EO1: "Executive Order 1 (Expedited)",
  EO8: "Executive Order 8 (Standard+)",
  Standard: "Standard Permit",
};

// ─── Step Indicator ───────────────────────────────────────────────────────────

function StepIndicator({ current, total }: { current: number; total: number }) {
  return (
    <View style={styles.stepRow}>
      {Array.from({ length: total }).map((_, i) => (
        <React.Fragment key={i}>
          <View
            style={[
              styles.stepDot,
              i < current
                ? styles.stepDotDone
                : i === current
                ? styles.stepDotActive
                : styles.stepDotIdle,
            ]}
          >
            {i < current ? (
              <MaterialCommunityIcons name="check" size={12} color="#fff" />
            ) : (
              <Text style={[styles.stepDotText, i === current && { color: "#fff" }]}>
                {i + 1}
              </Text>
            )}
          </View>
          {i < total - 1 && (
            <View style={[styles.stepLine, i < current && styles.stepLineDone]} />
          )}
        </React.Fragment>
      ))}
    </View>
  );
}

// ─── Overlay Chip ─────────────────────────────────────────────────────────────

function OverlayChip({ label, active }: { label: string; active: boolean }) {
  return (
    <View style={[styles.overlayChip, active ? styles.overlayChipActive : styles.overlayChipInactive]}>
      <Text style={[styles.overlayChipText, active ? styles.overlayChipTextActive : styles.overlayChipTextInactive]}>
        {label}
      </Text>
    </View>
  );
}

// ─── Main Screen ──────────────────────────────────────────────────────────────

export default function CreateProjectScreen() {
  const router = useRouter();
  const [step, setStep] = useState(0);

  // Form state
  const [address, setAddress] = useState("");
  const [originalSqft, setOriginalSqft] = useState("");
  const [proposedSqft, setProposedSqft] = useState("");
  const [stories, setStories] = useState<1 | 2 | 3>(1);

  // Async state
  const [parcelLoading, setParcelLoading] = useState(false);
  const [parcelFlags, setParcelFlags] = useState<ParcelFlags | null>(null);
  const [pathwayLoading, setPathwayLoading] = useState(false);
  const [pathway, setPathway] = useState<PathwayResult | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Parcel lookup with debounce ───────────────────────────────────────────

  const lookupParcel = useCallback(async (addr: string) => {
    if (addr.trim().length < 6) {
      setParcelFlags(null);
      return;
    }
    setParcelLoading(true);
    try {
      const result = await api.parcels.get(addr.trim());
      if (result) {
        setParcelFlags({
          coastal: !!result.coastal_zone,
          hillside: !!result.hillside,
          fire_zone: !!result.fire_severity_zone,
          historic: !!result.historic_district,
        });
      }
    } catch {
      // Parcel lookup is best-effort; don't block the user
      setParcelFlags(null);
    } finally {
      setParcelLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => lookupParcel(address), 600);
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, [address, lookupParcel]);

  // ── Step 1 → Step 2 transition ────────────────────────────────────────────

  const goToPathway = async () => {
    if (!address.trim()) {
      Alert.alert("Missing Address", "Please enter the project address.");
      return;
    }
    setStep(1);
    setPathwayLoading(true);
    try {
      const result = await api.pathfinder.quickAnalysis({
        address: address.trim(),
        original_sqft: Number(originalSqft) || 0,
        proposed_sqft: Number(proposedSqft) || 0,
        stories,
      });
      setPathway(result);
    } catch (err: any) {
      Alert.alert("Analysis Failed", err.message || "Could not analyse pathway.");
    } finally {
      setPathwayLoading(false);
    }
  };

  // ── Submission ────────────────────────────────────────────────────────────

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const project = await api.projects.create({
        address: address.trim(),
        original_sqft: Number(originalSqft) || undefined,
        proposed_sqft: Number(proposedSqft) || undefined,
        stories,
      });
      router.replace(`/project/${project.id}`);
    } catch (err: any) {
      setSubmitting(false);
      Alert.alert("Submission Failed", err.message || "Could not create project. Please try again.");
    }
  };

  // ── Render helpers ────────────────────────────────────────────────────────

  const pathwayColor = pathway ? (PATHWAY_COLORS[pathway.pathway] ?? "#6b7280") : "#6b7280";

  const renderStep0 = () => (
    <ScrollView contentContainerStyle={styles.stepContent} keyboardShouldPersistTaps="handled">
      <Text style={styles.stepHeading}>Where is the property?</Text>
      <Text style={styles.stepSubheading}>Enter the full street address of the rebuild site.</Text>

      <View style={styles.addressBox}>
        <MaterialCommunityIcons name="map-marker" size={22} color="#1e3a5f" style={styles.addressIcon} />
        <TextInput
          style={styles.addressInput}
          placeholder="e.g. 123 Altadena Dr, Pasadena, CA"
          placeholderTextColor="#9ca3af"
          value={address}
          onChangeText={setAddress}
          autoCorrect={false}
          autoCapitalize="words"
          returnKeyType="done"
          multiline={false}
        />
        {parcelLoading && <ActivityIndicator size="small" color="#1e3a5f" style={{ marginLeft: 8 }} />}
      </View>

      {/* Parcel overlay chips */}
      {parcelFlags && (
        <View style={styles.chipsRow}>
          <OverlayChip label="🌊 Coastal" active={parcelFlags.coastal} />
          <OverlayChip label="⛰️ Hillside" active={parcelFlags.hillside} />
          <OverlayChip label="🔥 Fire Zone" active={parcelFlags.fire_zone} />
          <OverlayChip label="🏛️ Historic" active={parcelFlags.historic} />
        </View>
      )}

      <Text style={styles.fieldLabel}>Original Square Footage</Text>
      <TextInput
        style={styles.numericInput}
        placeholder="e.g. 1800"
        placeholderTextColor="#9ca3af"
        keyboardType="numeric"
        value={originalSqft}
        onChangeText={setOriginalSqft}
        returnKeyType="next"
      />

      <Text style={styles.fieldLabel}>Proposed Square Footage</Text>
      <TextInput
        style={styles.numericInput}
        placeholder="e.g. 2200"
        placeholderTextColor="#9ca3af"
        keyboardType="numeric"
        value={proposedSqft}
        onChangeText={setProposedSqft}
        returnKeyType="done"
      />

      <Text style={styles.fieldLabel}>Number of Stories</Text>
      <View style={styles.storiesRow}>
        {([1, 2, 3] as const).map((n) => (
          <TouchableOpacity
            key={n}
            style={[styles.storiesBtn, stories === n && styles.storiesBtnActive]}
            onPress={() => setStories(n)}
            activeOpacity={0.7}
          >
            <Text style={[styles.storiesBtnText, stories === n && styles.storiesBtnTextActive]}>
              {n}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </ScrollView>
  );

  const renderStep1 = () => (
    <ScrollView contentContainerStyle={styles.stepContent}>
      <Text style={styles.stepHeading}>Pathway Preview</Text>
      <Text style={styles.stepSubheading}>Based on your project details, here is the recommended permit pathway.</Text>

      {pathwayLoading ? (
        <View style={styles.loadingBox}>
          <ActivityIndicator size="large" color="#1e3a5f" />
          <Text style={styles.loadingText}>Analysing permit pathway…</Text>
        </View>
      ) : pathway ? (
        <>
          {/* Pathway card */}
          <View style={[styles.pathwayCard, { borderLeftColor: pathwayColor }]}>
            <View style={[styles.pathwayBadge, { backgroundColor: pathwayColor }]}>
              <Text style={styles.pathwayBadgeText}>{pathway.pathway}</Text>
            </View>
            <Text style={styles.pathwayLabel}>
              {PATHWAY_LABELS[pathway.pathway] ?? pathway.pathway}
            </Text>
            <Text style={styles.daysLabel}>{pathway.estimated_days}</Text>
            <Text style={styles.daysUnit}>estimated days</Text>
          </View>

          {/* Key constraints */}
          {pathway.key_constraints?.length > 0 && (
            <View style={styles.constraintsBox}>
              <Text style={styles.constraintsTitle}>Key Constraints</Text>
              <View style={styles.chipsRow}>
                {pathway.key_constraints.map((c, i) => (
                  <View key={i} style={styles.constraintChip}>
                    <Text style={styles.constraintChipText}>{c}</Text>
                  </View>
                ))}
              </View>
            </View>
          )}

          {/* What-if hints */}
          {pathway.what_if_hints?.length > 0 && (
            <View style={styles.whatIfBox}>
              <Text style={styles.whatIfTitle}>What changes would help?</Text>
              {pathway.what_if_hints.map((hint, i) => (
                <View key={i} style={styles.whatIfRow}>
                  <MaterialCommunityIcons name="lightbulb-outline" size={16} color="#f59e0b" />
                  <Text style={styles.whatIfText}>{hint}</Text>
                </View>
              ))}
            </View>
          )}
        </>
      ) : (
        <View style={styles.loadingBox}>
          <Text style={styles.loadingText}>No pathway data available.</Text>
        </View>
      )}
    </ScrollView>
  );

  const renderStep2 = () => (
    <ScrollView contentContainerStyle={styles.stepContent}>
      <Text style={styles.stepHeading}>Confirm & Submit</Text>
      <Text style={styles.stepSubheading}>Review your project details before creating.</Text>

      <View style={styles.summaryCard}>
        <SummaryRow label="Address" value={address} />
        <SummaryRow label="Original sqft" value={originalSqft || "—"} />
        <SummaryRow label="Proposed sqft" value={proposedSqft || "—"} />
        <SummaryRow label="Stories" value={String(stories)} />
        {pathway && (
          <SummaryRow
            label="Pathway"
            value={pathway.pathway}
            valueColor={pathwayColor}
          />
        )}
      </View>
    </ScrollView>
  );

  // ── Navigation ────────────────────────────────────────────────────────────

  const canGoNext = step === 0 ? address.trim().length > 0 : true;

  const handleNext = () => {
    if (step === 0) {
      goToPathway();
    } else if (step === 1) {
      setStep(2);
    }
  };

  const handleBack = () => {
    if (step > 0) setStep(step - 1);
  };

  // ─────────────────────────────────────────────────────────────────────────

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      {/* Step indicator */}
      <View style={styles.stepIndicatorWrapper}>
        <StepIndicator current={step} total={3} />
        <Text style={styles.stepLabel}>
          {["Step 1: Address", "Step 2: Pathway", "Step 3: Confirm"][step]}
        </Text>
      </View>

      {/* Step content */}
      <View style={styles.contentWrapper}>
        {step === 0 && renderStep0()}
        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
      </View>

      {/* Navigation buttons */}
      <View style={styles.navRow}>
        {step > 0 ? (
          <TouchableOpacity style={styles.backBtn} onPress={handleBack} activeOpacity={0.7}>
            <MaterialCommunityIcons name="arrow-left" size={18} color="#1e3a5f" />
            <Text style={styles.backBtnText}>Back</Text>
          </TouchableOpacity>
        ) : (
          <View style={styles.navSpacer} />
        )}

        {step < 2 ? (
          <TouchableOpacity
            style={[styles.nextBtn, !canGoNext && styles.nextBtnDisabled]}
            onPress={handleNext}
            disabled={!canGoNext}
            activeOpacity={0.8}
          >
            <Text style={styles.nextBtnText}>Next</Text>
            <MaterialCommunityIcons name="arrow-right" size={18} color="#fff" />
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={[styles.nextBtn, submitting && styles.nextBtnDisabled]}
            onPress={handleSubmit}
            disabled={submitting}
            activeOpacity={0.8}
          >
            {submitting ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <>
                <Text style={styles.nextBtnText}>Create Project</Text>
                <MaterialCommunityIcons name="check" size={18} color="#fff" />
              </>
            )}
          </TouchableOpacity>
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

// ─── Summary Row helper ───────────────────────────────────────────────────────

function SummaryRow({
  label,
  value,
  valueColor,
}: {
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <View style={styles.summaryRow}>
      <Text style={styles.summaryLabel}>{label}</Text>
      <Text style={[styles.summaryValue, valueColor ? { color: valueColor, fontWeight: "700" } : undefined]}>
        {value}
      </Text>
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },

  // Step indicator
  stepIndicatorWrapper: {
    backgroundColor: "#ffffff",
    paddingHorizontal: 24,
    paddingTop: 20,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#e5e7eb",
    alignItems: "center",
  },
  stepRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
  },
  stepDot: {
    width: 28,
    height: 28,
    borderRadius: 14,
    justifyContent: "center",
    alignItems: "center",
  },
  stepDotActive: { backgroundColor: "#1e3a5f" },
  stepDotDone: { backgroundColor: "#16a34a" },
  stepDotIdle: { backgroundColor: "#e5e7eb" },
  stepDotText: { fontSize: 12, fontWeight: "700", color: "#9ca3af" },
  stepLine: { flex: 1, height: 2, backgroundColor: "#e5e7eb", marginHorizontal: 4 },
  stepLineDone: { backgroundColor: "#16a34a" },
  stepLabel: { fontSize: 13, color: "#6b7280", fontWeight: "500" },

  // Content
  contentWrapper: { flex: 1 },
  stepContent: { padding: 24, paddingBottom: 40 },
  stepHeading: { fontSize: 22, fontWeight: "bold", color: "#1e3a5f", marginBottom: 6 },
  stepSubheading: { fontSize: 15, color: "#6b7280", marginBottom: 24, lineHeight: 22 },

  // Address input
  addressBox: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#ffffff",
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: "#d1d5db",
    paddingHorizontal: 14,
    paddingVertical: 14,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 2,
  },
  addressIcon: { marginRight: 10 },
  addressInput: {
    flex: 1,
    fontSize: 16,
    color: "#1f2937",
  },

  // Overlay chips
  chipsRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 20 },
  overlayChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
  },
  overlayChipActive: { backgroundColor: "#fef3c7", borderColor: "#f59e0b" },
  overlayChipInactive: { backgroundColor: "#f3f4f6", borderColor: "#e5e7eb" },
  overlayChipText: { fontSize: 13, fontWeight: "600" },
  overlayChipTextActive: { color: "#92400e" },
  overlayChipTextInactive: { color: "#9ca3af" },

  // Numeric inputs
  fieldLabel: { fontSize: 14, fontWeight: "600", color: "#374151", marginBottom: 6 },
  numericInput: {
    backgroundColor: "#ffffff",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#d1d5db",
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    color: "#1f2937",
    marginBottom: 16,
  },

  // Stories picker
  storiesRow: { flexDirection: "row", gap: 12, marginBottom: 8 },
  storiesBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: "#d1d5db",
    alignItems: "center",
    backgroundColor: "#ffffff",
  },
  storiesBtnActive: { backgroundColor: "#1e3a5f", borderColor: "#1e3a5f" },
  storiesBtnText: { fontSize: 18, fontWeight: "700", color: "#374151" },
  storiesBtnTextActive: { color: "#ffffff" },

  // Loading box
  loadingBox: { alignItems: "center", paddingVertical: 48 },
  loadingText: { marginTop: 16, fontSize: 15, color: "#6b7280" },

  // Pathway card
  pathwayCard: {
    backgroundColor: "#ffffff",
    borderRadius: 16,
    padding: 24,
    borderLeftWidth: 6,
    marginBottom: 20,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 6,
    elevation: 3,
    alignItems: "center",
  },
  pathwayBadge: {
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 20,
    marginBottom: 10,
  },
  pathwayBadgeText: { color: "#ffffff", fontWeight: "700", fontSize: 14 },
  pathwayLabel: { fontSize: 16, color: "#374151", fontWeight: "600", marginBottom: 16, textAlign: "center" },
  daysLabel: { fontSize: 56, fontWeight: "900", color: "#1e3a5f" },
  daysUnit: { fontSize: 14, color: "#6b7280", marginTop: 2 },

  // Constraints
  constraintsBox: { marginBottom: 20 },
  constraintsTitle: { fontSize: 14, fontWeight: "600", color: "#6b7280", textTransform: "uppercase", marginBottom: 10 },
  constraintChip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: "#eff6ff",
    borderWidth: 1,
    borderColor: "#bfdbfe",
  },
  constraintChipText: { fontSize: 13, color: "#1d4ed8", fontWeight: "500" },

  // What-if
  whatIfBox: {
    backgroundColor: "#fffbeb",
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: "#fde68a",
  },
  whatIfTitle: { fontSize: 14, fontWeight: "700", color: "#92400e", marginBottom: 10 },
  whatIfRow: { flexDirection: "row", alignItems: "flex-start", gap: 8, marginBottom: 6 },
  whatIfText: { flex: 1, fontSize: 14, color: "#78350f", lineHeight: 20 },

  // Summary card
  summaryCard: {
    backgroundColor: "#ffffff",
    borderRadius: 16,
    padding: 20,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.07,
    shadowRadius: 4,
    elevation: 2,
  },
  summaryRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#f3f4f6",
  },
  summaryLabel: { fontSize: 14, color: "#6b7280", fontWeight: "500", flex: 1 },
  summaryValue: { fontSize: 15, color: "#1f2937", fontWeight: "600", flex: 2, textAlign: "right" },

  // Nav buttons
  navRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 24,
    paddingVertical: 16,
    backgroundColor: "#ffffff",
    borderTopWidth: 1,
    borderTopColor: "#e5e7eb",
  },
  navSpacer: { flex: 1 },
  backBtn: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: "#1e3a5f",
    gap: 6,
  },
  backBtnText: { fontSize: 15, fontWeight: "600", color: "#1e3a5f" },
  nextBtn: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 10,
    backgroundColor: "#1e3a5f",
    gap: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 3,
  },
  nextBtnDisabled: { opacity: 0.5 },
  nextBtnText: { fontSize: 15, fontWeight: "700", color: "#ffffff" },
});
