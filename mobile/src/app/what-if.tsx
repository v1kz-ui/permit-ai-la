import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  TextInput,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { api } from "../services/api";

const PATHWAY_COLORS: Record<string, string> = {
  standard: "#3b82f6",
  expedited: "#f59e0b",
  emergency: "#ef4444",
  eo1: "#8b5cf6",
  eo8: "#10b981",
};

interface ScenarioResult {
  pathway?: string;
  estimated_days?: number;
  constraints?: string[];
  recommendation?: string;
}

interface Scenario {
  label: string;
  description: string;
  sqft: number;
  result: ScenarioResult | null;
  loading: boolean;
  error: string | null;
}

function clamp(val: number, min: number, max: number) {
  return Math.min(max, Math.max(min, val));
}

function StepperInput({
  value,
  onChange,
  min = 100,
  max = 10000,
  step = 50,
}: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
}) {
  const [text, setText] = useState(String(value));

  const handleDecrement = () => {
    const next = clamp(value - step, min, max);
    onChange(next);
    setText(String(next));
  };

  const handleIncrement = () => {
    const next = clamp(value + step, min, max);
    onChange(next);
    setText(String(next));
  };

  const handleTextChange = (t: string) => {
    setText(t);
    const parsed = parseInt(t, 10);
    if (!isNaN(parsed)) {
      onChange(clamp(parsed, min, max));
    }
  };

  return (
    <View style={stepperStyles.row}>
      <TouchableOpacity style={stepperStyles.btn} onPress={handleDecrement}>
        <Text style={stepperStyles.btnText}>-</Text>
      </TouchableOpacity>
      <TextInput
        style={stepperStyles.input}
        value={text}
        onChangeText={handleTextChange}
        keyboardType="numeric"
      />
      <Text style={stepperStyles.unit}>sqft</Text>
      <TouchableOpacity style={stepperStyles.btn} onPress={handleIncrement}>
        <Text style={stepperStyles.btnText}>+</Text>
      </TouchableOpacity>
    </View>
  );
}

const stepperStyles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", gap: 8 },
  btn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "#1e3a5f",
    alignItems: "center",
    justifyContent: "center",
  },
  btnText: { color: "#fff", fontSize: 20, fontWeight: "bold", lineHeight: 22 },
  input: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 16,
    minWidth: 80,
    textAlign: "center",
    backgroundColor: "#fff",
  },
  unit: { fontSize: 14, color: "#6b7280" },
});

export default function WhatIfScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{
    address?: string;
    original_sqft?: string;
    proposed_sqft?: string;
  }>();

  const [address, setAddress] = useState(params.address || "");
  const [originalSqft, setOriginalSqft] = useState(
    parseInt(params.original_sqft || "1000", 10)
  );
  const [proposedSqft, setProposedSqft] = useState(
    parseInt(params.proposed_sqft || "1200", 10)
  );

  const eo1Max = Math.round(originalSqft * 1.1);
  const eo8Max = Math.round(originalSqft * 1.5);

  const [scenarios, setScenarios] = useState<Scenario[]>([
    {
      label: "Current Plan",
      description: "As entered",
      sqft: proposedSqft,
      result: null,
      loading: false,
      error: null,
    },
    {
      label: "EO1 Max",
      description: "10% increase",
      sqft: eo1Max,
      result: null,
      loading: false,
      error: null,
    },
    {
      label: "EO8 Max",
      description: "50% increase",
      sqft: eo8Max,
      result: null,
      loading: false,
      error: null,
    },
  ]);

  const [globalLoading, setGlobalLoading] = useState(false);
  const [recommendation, setRecommendation] = useState<string | null>(null);

  const handleCalculate = useCallback(async () => {
    if (!address.trim()) return;

    const currentEo1 = Math.round(originalSqft * 1.1);
    const currentEo8 = Math.round(originalSqft * 1.5);

    const updatedScenarios: Scenario[] = [
      {
        label: "Current Plan",
        description: "As entered",
        sqft: proposedSqft,
        result: null,
        loading: true,
        error: null,
      },
      {
        label: "EO1 Max",
        description: "10% increase",
        sqft: currentEo1,
        result: null,
        loading: true,
        error: null,
      },
      {
        label: "EO8 Max",
        description: "50% increase",
        sqft: currentEo8,
        result: null,
        loading: true,
        error: null,
      },
    ];

    setScenarios(updatedScenarios);
    setGlobalLoading(true);
    setRecommendation(null);

    const sqfts = [proposedSqft, currentEo1, currentEo8];
    const results = await Promise.allSettled(
      sqfts.map((sqft) =>
        api.pathfinder.whatIf({
          address: address.trim(),
          original_sqft: originalSqft,
          proposed_sqft: sqft,
        })
      )
    );

    const finalScenarios = updatedScenarios.map((s, i) => {
      const res = results[i];
      if (res.status === "fulfilled") {
        return { ...s, result: res.value, loading: false };
      } else {
        return { ...s, error: "Failed to calculate", loading: false };
      }
    });

    setScenarios(finalScenarios);
    setGlobalLoading(false);

    // Pick recommendation from first successful result
    const firstOk = finalScenarios.find((s) => s.result?.recommendation);
    if (firstOk?.result?.recommendation) {
      setRecommendation(firstOk.result.recommendation);
    }
  }, [address, originalSqft, proposedSqft]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Header */}
      <View style={styles.topBar}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#1e3a5f" />
          <Text style={styles.backText}>Back</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.titleRow}>
        <Text style={styles.title}>What-if Scenarios</Text>
        <Text style={styles.subtitle}>
          Compare approval pathways for different project sizes
        </Text>
      </View>

      {/* Input fields */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Project Parameters</Text>

        <Text style={styles.label}>Address</Text>
        <TextInput
          style={styles.textInput}
          value={address}
          onChangeText={setAddress}
          placeholder="e.g. 123 Main St, Los Angeles, CA"
          placeholderTextColor="#9ca3af"
        />

        <Text style={[styles.label, { marginTop: 16 }]}>Original Sq Ft</Text>
        <StepperInput
          value={originalSqft}
          onChange={setOriginalSqft}
          min={100}
          max={10000}
          step={50}
        />

        <Text style={[styles.label, { marginTop: 16 }]}>Proposed Sq Ft</Text>
        <StepperInput
          value={proposedSqft}
          onChange={setProposedSqft}
          min={100}
          max={10000}
          step={50}
        />

        <View style={styles.infoRow}>
          <Text style={styles.infoText}>
            EO1 Max (10%): {Math.round(originalSqft * 1.1).toLocaleString()} sqft
          </Text>
          <Text style={styles.infoText}>
            EO8 Max (50%): {Math.round(originalSqft * 1.5).toLocaleString()} sqft
          </Text>
        </View>
      </View>

      {/* Calculate button */}
      <TouchableOpacity
        style={[styles.calcBtn, globalLoading && styles.calcBtnDisabled]}
        onPress={handleCalculate}
        disabled={globalLoading || !address.trim()}
      >
        {globalLoading ? (
          <ActivityIndicator color="#ffffff" />
        ) : (
          <>
            <MaterialCommunityIcons name="calculator" size={20} color="#ffffff" />
            <Text style={styles.calcBtnText}>Calculate</Text>
          </>
        )}
      </TouchableOpacity>

      {/* Scenario cards */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scenarioScroll}
      >
        {scenarios.map((scenario, i) => {
          const pathwayColor =
            PATHWAY_COLORS[scenario.result?.pathway || ""] || "#6b7280";
          return (
            <View key={i} style={styles.scenarioCard}>
              <Text style={styles.scenarioLabel}>{scenario.label}</Text>
              <Text style={styles.scenarioDesc}>{scenario.description}</Text>
              <Text style={styles.scenarioSqft}>
                {scenario.sqft.toLocaleString()} sqft
              </Text>

              {scenario.loading && (
                <ActivityIndicator
                  size="small"
                  color="#1e3a5f"
                  style={{ marginTop: 16 }}
                />
              )}

              {scenario.error && !scenario.loading && (
                <Text style={styles.scenarioError}>{scenario.error}</Text>
              )}

              {scenario.result && !scenario.loading && (
                <>
                  {scenario.result.pathway && (
                    <View
                      style={[
                        styles.pathwayBadge,
                        { backgroundColor: pathwayColor },
                      ]}
                    >
                      <Text style={styles.pathwayBadgeText}>
                        {scenario.result.pathway}
                      </Text>
                    </View>
                  )}
                  {scenario.result.estimated_days != null && (
                    <Text style={styles.estimatedDays}>
                      {scenario.result.estimated_days}
                    </Text>
                  )}
                  {scenario.result.estimated_days != null && (
                    <Text style={styles.estimatedDaysLabel}>days est.</Text>
                  )}
                  {scenario.result.constraints &&
                    scenario.result.constraints.length > 0 && (
                      <View style={styles.constraintsList}>
                        {scenario.result.constraints
                          .slice(0, 3)
                          .map((c, ci) => (
                            <View key={ci} style={styles.constraintItem}>
                              <View style={styles.constraintDot} />
                              <Text style={styles.constraintText}>{c}</Text>
                            </View>
                          ))}
                      </View>
                    )}
                </>
              )}
            </View>
          );
        })}
      </ScrollView>

      {/* Recommendation */}
      {recommendation && (
        <View style={styles.recommendationBox}>
          <View style={styles.recommendationHeader}>
            <MaterialCommunityIcons
              name="lightbulb-on"
              size={20}
              color="#10b981"
            />
            <Text style={styles.recommendationTitle}>Recommendation</Text>
          </View>
          <Text style={styles.recommendationText}>{recommendation}</Text>
        </View>
      )}

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
  content: { paddingBottom: 40 },
  topBar: { paddingTop: 56, paddingHorizontal: 16, paddingBottom: 4 },
  backBtn: { flexDirection: "row", alignItems: "center" },
  backText: { fontSize: 16, color: "#1e3a5f", marginLeft: 4, fontWeight: "500" },
  titleRow: { paddingHorizontal: 20, paddingVertical: 12 },
  title: { fontSize: 26, fontWeight: "bold", color: "#1e3a5f" },
  subtitle: { fontSize: 14, color: "#6b7280", marginTop: 4 },

  card: {
    backgroundColor: "#ffffff",
    marginHorizontal: 20,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 3,
  },
  cardTitle: { fontSize: 16, fontWeight: "700", color: "#374151", marginBottom: 12 },
  label: { fontSize: 13, fontWeight: "600", color: "#374151", marginBottom: 6 },
  textInput: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    color: "#111827",
    backgroundColor: "#f9fafb",
  },
  infoRow: {
    marginTop: 14,
    gap: 4,
    backgroundColor: "#f0fdf4",
    padding: 10,
    borderRadius: 8,
  },
  infoText: { fontSize: 13, color: "#059669" },

  calcBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#1e3a5f",
    marginHorizontal: 20,
    padding: 16,
    borderRadius: 12,
    marginBottom: 20,
    gap: 8,
  },
  calcBtnDisabled: { opacity: 0.6 },
  calcBtnText: { color: "#ffffff", fontSize: 16, fontWeight: "700" },

  // Scenario cards
  scenarioScroll: { paddingHorizontal: 20, paddingBottom: 8, gap: 12 },
  scenarioCard: {
    width: 200,
    backgroundColor: "#ffffff",
    borderRadius: 16,
    padding: 16,
    marginRight: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 6,
    elevation: 4,
    minHeight: 200,
  },
  scenarioLabel: { fontSize: 15, fontWeight: "700", color: "#1e3a5f" },
  scenarioDesc: { fontSize: 12, color: "#6b7280", marginTop: 2 },
  scenarioSqft: {
    fontSize: 14,
    fontWeight: "600",
    color: "#374151",
    marginTop: 6,
    marginBottom: 10,
  },
  pathwayBadge: {
    alignSelf: "flex-start",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 10,
    marginBottom: 8,
  },
  pathwayBadgeText: { color: "#ffffff", fontSize: 12, fontWeight: "600", textTransform: "capitalize" },
  estimatedDays: {
    fontSize: 40,
    fontWeight: "bold",
    color: "#1e3a5f",
    lineHeight: 44,
  },
  estimatedDaysLabel: { fontSize: 12, color: "#6b7280", marginBottom: 10 },
  constraintsList: { gap: 4 },
  constraintItem: { flexDirection: "row", alignItems: "flex-start", gap: 6 },
  constraintDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "#f59e0b",
    marginTop: 5,
  },
  constraintText: { fontSize: 11, color: "#374151", flex: 1, lineHeight: 16 },
  scenarioError: { fontSize: 13, color: "#ef4444", marginTop: 12 },

  // Recommendation
  recommendationBox: {
    marginHorizontal: 20,
    marginTop: 20,
    backgroundColor: "#f0fdf4",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#10b981",
    padding: 16,
  },
  recommendationHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 8,
  },
  recommendationTitle: { fontSize: 15, fontWeight: "700", color: "#10b981" },
  recommendationText: { fontSize: 14, color: "#374151", lineHeight: 20 },
});
