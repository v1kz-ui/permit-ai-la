import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { api } from "../../services/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

const WELCOME_MESSAGE: Message = {
  id: "welcome",
  role: "assistant",
  content:
    "Hi! I'm your permit assistant. Ask me anything about your fire rebuild permit process.",
};

const DISCLAIMER_MESSAGE: Message = {
  id: "disclaimer",
  role: "assistant",
  content:
    "I provide guidance based on LA permit regulations, but my responses may not reflect the very latest changes. Always verify important decisions with the relevant city department. I'm not a substitute for legal advice.",
};

export default function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE, DISCLAIMER_MESSAGE]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [projectId, setProjectId] = useState<string | null>(null);
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    api.projects.list().then((projects) => {
      if (projects.length > 0) {
        setProjectId(projects[0].id);
      }
    }).catch(() => {});
  }, []);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || sending || !projectId) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: text,
    };

    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput("");
    setSending(true);

    try {
      const history = updatedMessages
        .filter((m) => m.id !== "welcome")
        .map((m) => ({ role: m.role, content: m.content }));

      const response = await api.chat.send(projectId, text, history);

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.reply || response.message || "Sorry, I couldn't process that.",
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, something went wrong. Please try again.",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setSending(false);
    }
  }, [input, sending, projectId, messages]);

  const renderMessage = ({ item }: { item: Message }) => {
    const isUser = item.role === "user";
    return (
      <View
        style={[
          styles.bubble,
          isUser ? styles.userBubble : styles.assistantBubble,
        ]}
        accessibilityRole="text"
        accessibilityLabel={`${isUser ? "You said" : "Assistant replied"}: ${item.content}`}
      >
        <Text
          style={[
            styles.bubbleText,
            isUser ? styles.userText : styles.assistantText,
          ]}
        >
          {item.content}
        </Text>
      </View>
    );
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={0}
    >
      <View style={styles.header}>
        <Text style={styles.title}>Permit Assistant</Text>
      </View>

      <FlatList
        ref={flatListRef}
        data={messages}
        keyExtractor={(item) => item.id}
        renderItem={renderMessage}
        contentContainerStyle={styles.messageList}
        onContentSizeChange={() =>
          flatListRef.current?.scrollToEnd({ animated: true })
        }
      />

      {sending && (
        <View style={styles.typingRow}>
          <ActivityIndicator size="small" color="#1e3a5f" />
          <Text style={styles.typingText}>Typing...</Text>
        </View>
      )}

      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder="Ask about your permit..."
          placeholderTextColor="#9ca3af"
          multiline
          editable={!sending}
          accessibilityLabel="Type your question about permits"
          accessibilityHint="Type a question and press send to get an answer"
        />
        <TouchableOpacity
          style={[styles.sendBtn, (!input.trim() || sending) && styles.sendBtnDisabled]}
          onPress={sendMessage}
          disabled={!input.trim() || sending}
          accessibilityRole="button"
          accessibilityLabel={sending ? "Sending message" : "Send message"}
          accessibilityState={{ disabled: !input.trim() || sending }}
        >
          <MaterialCommunityIcons name="send" size={22} color="#ffffff" />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f9fafb" },
  header: { padding: 20, paddingTop: 60, backgroundColor: "#ffffff", borderBottomWidth: 1, borderBottomColor: "#e5e7eb" },
  title: { fontSize: 20, fontWeight: "bold", color: "#1e3a5f" },
  messageList: { padding: 16, paddingBottom: 8 },
  bubble: {
    maxWidth: "80%",
    padding: 12,
    borderRadius: 16,
    marginBottom: 8,
  },
  userBubble: {
    alignSelf: "flex-end",
    backgroundColor: "#1e3a5f",
    borderBottomRightRadius: 4,
  },
  assistantBubble: {
    alignSelf: "flex-start",
    backgroundColor: "#e5e7eb",
    borderBottomLeftRadius: 4,
  },
  bubbleText: { fontSize: 15, lineHeight: 21 },
  userText: { color: "#ffffff" },
  assistantText: { color: "#374151" },
  typingRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingBottom: 4,
  },
  typingText: { marginLeft: 8, color: "#6b7280", fontSize: 13 },
  inputRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    padding: 12,
    backgroundColor: "#ffffff",
    borderTopWidth: 1,
    borderTopColor: "#e5e7eb",
  },
  input: {
    flex: 1,
    backgroundColor: "#f3f4f6",
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 15,
    maxHeight: 100,
    color: "#374151",
  },
  sendBtn: {
    backgroundColor: "#1e3a5f",
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: "center",
    alignItems: "center",
    marginLeft: 8,
  },
  sendBtnDisabled: { opacity: 0.5 },
});
