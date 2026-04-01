import React, { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import AsyncStorage from "@react-native-async-storage/async-storage";

const { width } = Dimensions.get("window");

const SLIDES = [
  {
    icon: "heart-outline" as const,
    title: "We're here to\nhelp you rebuild",
    body: "We know this is a difficult time. PermitAI LA is designed to guide you through the permit process — step by step, at your pace.",
    color: "#1e3a5f",
    bg: "#eef2f8",
  },
  {
    icon: "map-marker-path" as const,
    title: "Track your permit\nfrom start to finish",
    body: "See exactly where your application stands across every city department. No more guessing or waiting on hold.",
    color: "#10b981",
    bg: "#ecfdf5",
  },
  {
    icon: "robot-outline" as const,
    title: "Get answers\ninstantly",
    body: "Our AI assistant can answer your questions about requirements, timelines, and next steps — in English, Spanish, Korean, Chinese, or Filipino.",
    color: "#6366f1",
    bg: "#eef2ff",
  },
];

interface Props {
  onComplete: () => void;
}

export const ONBOARDING_KEY = "onboarding_complete_v1";

export default function OnboardingFlow({ onComplete }: Props) {
  const [step, setStep] = useState(0);

  const handleFinish = async () => {
    await AsyncStorage.setItem(ONBOARDING_KEY, "true");
    onComplete();
  };

  const slide = SLIDES[step];
  const isLast = step === SLIDES.length - 1;

  return (
    <View style={styles.container}>
      {/* Skip link */}
      {!isLast && (
        <TouchableOpacity
          onPress={handleFinish}
          style={styles.skipBtn}
          accessibilityRole="button"
          accessibilityLabel="Skip introduction and go to app"
        >
          <Text style={styles.skipText}>Skip</Text>
        </TouchableOpacity>
      )}

      {/* Slide content */}
      <View style={styles.content}>
        <View style={[styles.iconCircle, { backgroundColor: slide.bg }]}>
          <MaterialCommunityIcons name={slide.icon} size={52} color={slide.color} />
        </View>
        <Text style={styles.title}>{slide.title}</Text>
        <Text style={styles.body}>{slide.body}</Text>
      </View>

      {/* Dots */}
      <View style={styles.dots}>
        {SLIDES.map((_, i) => (
          <View
            key={i}
            style={[styles.dot, i === step && styles.dotActive]}
            accessibilityLabel={`Slide ${i + 1} of ${SLIDES.length}${i === step ? ", current" : ""}`}
          />
        ))}
      </View>

      {/* CTA button */}
      <View style={styles.footer}>
        <TouchableOpacity
          style={[styles.primaryBtn, { backgroundColor: slide.color }]}
          onPress={isLast ? handleFinish : () => setStep(step + 1)}
          activeOpacity={0.85}
          accessibilityRole="button"
          accessibilityLabel={isLast ? "Get started with PermitAI LA" : "Continue to next slide"}
        >
          <Text style={styles.primaryBtnText}>
            {isLast ? "Get Started" : "Continue"}
          </Text>
          <MaterialCommunityIcons
            name={isLast ? "arrow-right-circle" : "arrow-right"}
            size={20}
            color="#ffffff"
          />
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#ffffff",
    justifyContent: "space-between",
    paddingTop: 60,
    paddingBottom: 48,
  },
  skipBtn: {
    alignSelf: "flex-end",
    paddingHorizontal: 20,
    paddingVertical: 8,
  },
  skipText: {
    fontSize: 15,
    color: "#9ca3af",
    fontWeight: "500",
  },
  content: {
    alignItems: "center",
    paddingHorizontal: 36,
    flex: 1,
    justifyContent: "center",
  },
  iconCircle: {
    width: 100,
    height: 100,
    borderRadius: 50,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 32,
  },
  title: {
    fontSize: 26,
    fontWeight: "700",
    color: "#1e3a5f",
    textAlign: "center",
    marginBottom: 16,
    lineHeight: 34,
  },
  body: {
    fontSize: 16,
    color: "#6b7280",
    textAlign: "center",
    lineHeight: 26,
  },
  dots: {
    flexDirection: "row",
    justifyContent: "center",
    gap: 8,
    marginBottom: 24,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#d1d5db",
  },
  dotActive: {
    backgroundColor: "#1e3a5f",
    width: 24,
  },
  footer: {
    paddingHorizontal: 32,
  },
  primaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 16,
    borderRadius: 14,
    gap: 8,
  },
  primaryBtnText: {
    color: "#ffffff",
    fontSize: 17,
    fontWeight: "700",
  },
});
