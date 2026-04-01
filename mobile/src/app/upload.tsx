import React, { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  Image,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Alert,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import * as DocumentPicker from "expo-document-picker";
import { api } from "../services/api";

const DOC_TYPES = [
  { value: "plans", label: "Plans" },
  { value: "permit_application", label: "Permit Application" },
  { value: "insurance", label: "Insurance" },
  { value: "photos", label: "Photos" },
  { value: "other", label: "Other" },
];

export default function UploadScreen() {
  const { projectId } = useLocalSearchParams<{ projectId: string }>();
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<any>(null);
  const [docType, setDocType] = useState("plans");
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const pickImage = async () => {
    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
    });
    if (!result.canceled && result.assets.length > 0) {
      setSelectedFile(result.assets[0]);
    }
  };

  const pickDocument = async () => {
    const result = await DocumentPicker.getDocumentAsync({
      type: "*/*",
      copyToCacheDirectory: true,
    });
    if (!result.canceled && result.assets && result.assets.length > 0) {
      setSelectedFile(result.assets[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !projectId) return;

    setUploading(true);
    setProgress(0);

    try {
      // Simulate progress since fetch doesn't support progress natively
      const progressInterval = setInterval(() => {
        setProgress((prev) => Math.min(prev + 0.1, 0.9));
      }, 200);

      await api.documents.upload(projectId, selectedFile, docType);

      clearInterval(progressInterval);
      setProgress(1);

      Alert.alert("Success", "Document uploaded successfully.", [
        { text: "OK", onPress: () => router.back() },
      ]);
    } catch (err: any) {
      Alert.alert("Upload Failed", err.message || "Please try again.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.topBar}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#1e3a5f" />
          <Text style={styles.backText}>Back</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.header}>
        <Text style={styles.title}>Upload Document</Text>
      </View>

      {/* Capture / Pick buttons */}
      <View style={styles.pickRow}>
        <TouchableOpacity style={styles.pickBtn} onPress={pickImage}>
          <MaterialCommunityIcons name="camera" size={32} color="#1e3a5f" />
          <Text style={styles.pickLabel}>Take Photo</Text>
        </TouchableOpacity>
        <TouchableOpacity style={styles.pickBtn} onPress={pickDocument}>
          <MaterialCommunityIcons name="file-upload" size={32} color="#1e3a5f" />
          <Text style={styles.pickLabel}>Choose File</Text>
        </TouchableOpacity>
      </View>

      {/* Preview */}
      {selectedFile && (
        <View style={styles.previewCard}>
          {selectedFile.uri && selectedFile.mimeType?.startsWith("image") ? (
            <Image
              source={{ uri: selectedFile.uri }}
              style={styles.previewImage}
              resizeMode="cover"
            />
          ) : selectedFile.uri && selectedFile.uri.match(/\.(jpg|jpeg|png|gif|webp)$/i) ? (
            <Image
              source={{ uri: selectedFile.uri }}
              style={styles.previewImage}
              resizeMode="cover"
            />
          ) : (
            <View style={styles.filePlaceholder}>
              <MaterialCommunityIcons name="file-document" size={48} color="#6b7280" />
              <Text style={styles.fileName}>
                {selectedFile.name || "Selected file"}
              </Text>
            </View>
          )}
        </View>
      )}

      {/* Document type selector */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Document Type</Text>
        <View style={styles.chipRow}>
          {DOC_TYPES.map((dt) => (
            <TouchableOpacity
              key={dt.value}
              style={[
                styles.chip,
                docType === dt.value && styles.chipActive,
              ]}
              onPress={() => setDocType(dt.value)}
            >
              <Text
                style={[
                  styles.chipText,
                  docType === dt.value && styles.chipTextActive,
                ]}
              >
                {dt.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Upload button */}
      {uploading && (
        <View style={styles.progressContainer}>
          <View style={styles.progressBar}>
            <View
              style={[styles.progressFill, { width: `${progress * 100}%` }]}
            />
          </View>
          <Text style={styles.progressText}>
            {Math.round(progress * 100)}%
          </Text>
        </View>
      )}

      <TouchableOpacity
        style={[
          styles.uploadBtn,
          (!selectedFile || uploading) && styles.uploadBtnDisabled,
        ]}
        onPress={handleUpload}
        disabled={!selectedFile || uploading}
      >
        {uploading ? (
          <ActivityIndicator color="#ffffff" />
        ) : (
          <>
            <MaterialCommunityIcons name="cloud-upload" size={20} color="#ffffff" />
            <Text style={styles.uploadBtnText}>Upload</Text>
          </>
        )}
      </TouchableOpacity>

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
  topBar: { paddingTop: 56, paddingHorizontal: 16 },
  backBtn: { flexDirection: "row", alignItems: "center" },
  backText: { fontSize: 16, color: "#1e3a5f", marginLeft: 4, fontWeight: "500" },
  header: { padding: 20, paddingTop: 12 },
  title: { fontSize: 24, fontWeight: "bold", color: "#1e3a5f" },
  pickRow: {
    flexDirection: "row",
    paddingHorizontal: 20,
    gap: 16,
    marginBottom: 20,
  },
  pickBtn: {
    flex: 1,
    backgroundColor: "#ffffff",
    borderRadius: 12,
    padding: 24,
    alignItems: "center",
    borderWidth: 2,
    borderColor: "#e5e7eb",
    borderStyle: "dashed",
  },
  pickLabel: { fontSize: 14, color: "#374151", marginTop: 8, fontWeight: "500" },
  previewCard: {
    marginHorizontal: 20,
    marginBottom: 20,
    borderRadius: 12,
    overflow: "hidden",
    backgroundColor: "#ffffff",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  previewImage: { width: "100%", height: 200 },
  filePlaceholder: {
    padding: 24,
    alignItems: "center",
  },
  fileName: { fontSize: 14, color: "#6b7280", marginTop: 8 },
  section: { paddingHorizontal: 20, marginBottom: 20 },
  sectionTitle: {
    fontSize: 14,
    fontWeight: "600",
    color: "#6b7280",
    textTransform: "uppercase",
    marginBottom: 10,
  },
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: "#f3f4f6",
    borderWidth: 1,
    borderColor: "#e5e7eb",
  },
  chipActive: { backgroundColor: "#1e3a5f", borderColor: "#1e3a5f" },
  chipText: { fontSize: 14, color: "#374151" },
  chipTextActive: { color: "#ffffff" },
  progressContainer: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    marginBottom: 16,
  },
  progressBar: {
    flex: 1,
    height: 8,
    backgroundColor: "#e5e7eb",
    borderRadius: 4,
    overflow: "hidden",
  },
  progressFill: { height: "100%", backgroundColor: "#1e3a5f", borderRadius: 4 },
  progressText: { marginLeft: 12, fontSize: 14, color: "#374151", fontWeight: "600" },
  uploadBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#1e3a5f",
    marginHorizontal: 20,
    padding: 16,
    borderRadius: 12,
  },
  uploadBtnDisabled: { opacity: 0.5 },
  uploadBtnText: { color: "#ffffff", fontSize: 16, fontWeight: "600", marginLeft: 8 },
});
