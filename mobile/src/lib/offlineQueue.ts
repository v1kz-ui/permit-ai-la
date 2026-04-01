/**
 * Offline mutation queue.
 * Stores failed API writes when offline and replays them on reconnect.
 */
import AsyncStorage from "@react-native-async-storage/async-storage";
import NetInfo from "@react-native-community/netinfo";

interface QueuedRequest {
  id: string;
  method: string;
  path: string;
  body: any;
  timestamp: number;
  retries: number;
}

const QUEUE_KEY = "offline:queue";
const MAX_RETRIES = 3;

export const offlineQueue = {
  async enqueue(method: string, path: string, body: any): Promise<void> {
    const queue = await offlineQueue.getQueue();
    const item: QueuedRequest = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      method,
      path,
      body,
      timestamp: Date.now(),
      retries: 0,
    };
    queue.push(item);
    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
  },

  async getQueue(): Promise<QueuedRequest[]> {
    const raw = await AsyncStorage.getItem(QUEUE_KEY);
    return raw ? JSON.parse(raw) : [];
  },

  async flush(apiBase: string): Promise<{ succeeded: number; failed: number }> {
    const queue = await offlineQueue.getQueue();
    const remaining: QueuedRequest[] = [];
    let succeeded = 0;
    let failed = 0;

    for (const item of queue) {
      try {
        const response = await fetch(`${apiBase}${item.path}`, {
          method: item.method,
          headers: { "Content-Type": "application/json" },
          body: item.body ? JSON.stringify(item.body) : undefined,
        });
        if (response.ok) {
          succeeded++;
        } else if (item.retries < MAX_RETRIES) {
          remaining.push({ ...item, retries: item.retries + 1 });
        } else {
          failed++;
        }
      } catch {
        if (item.retries < MAX_RETRIES) {
          remaining.push({ ...item, retries: item.retries + 1 });
        } else {
          failed++;
        }
      }
    }

    await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(remaining));
    return { succeeded, failed };
  },

  async clear(): Promise<void> {
    await AsyncStorage.removeItem(QUEUE_KEY);
  },
};
