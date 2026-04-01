/**
 * Offline cache using AsyncStorage.
 * Caches API responses with TTL so the app works without internet.
 */
import AsyncStorage from "@react-native-async-storage/async-storage";

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttl: number; // milliseconds
}

const DEFAULT_TTL = 5 * 60 * 1000; // 5 minutes

export const offlineCache = {
  async set<T>(key: string, data: T, ttl = DEFAULT_TTL): Promise<void> {
    const entry: CacheEntry<T> = { data, timestamp: Date.now(), ttl };
    await AsyncStorage.setItem(`cache:${key}`, JSON.stringify(entry));
  },

  async get<T>(key: string): Promise<T | null> {
    const raw = await AsyncStorage.getItem(`cache:${key}`);
    if (!raw) return null;
    const entry: CacheEntry<T> = JSON.parse(raw);
    if (Date.now() - entry.timestamp > entry.ttl) {
      await AsyncStorage.removeItem(`cache:${key}`);
      return null;
    }
    return entry.data;
  },

  async invalidate(key: string): Promise<void> {
    await AsyncStorage.removeItem(`cache:${key}`);
  },

  async clear(): Promise<void> {
    const keys = await AsyncStorage.getAllKeys();
    const cacheKeys = keys.filter((k) => k.startsWith("cache:"));
    await AsyncStorage.multiRemove(cacheKeys);
  },
};
