/**
 * Hook to monitor network connectivity.
 * Returns isOnline boolean and triggers queue flush on reconnect.
 */
import { useEffect, useRef, useState } from "react";
import NetInfo from "@react-native-community/netinfo";
import { offlineQueue } from "./offlineQueue";

const API_BASE = process.env.EXPO_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState(true);
  const [justReconnected, setJustReconnected] = useState(false);
  const wasOffline = useRef(false);

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener((state) => {
      const online = state.isConnected === true && state.isInternetReachable !== false;
      setIsOnline(online);

      if (online && wasOffline.current) {
        // Coming back online — flush the queue and show reconnect banner
        setJustReconnected(true);
        setTimeout(() => setJustReconnected(false), 3000);
        offlineQueue.flush(API_BASE).then(({ succeeded, failed }) => {
          if (succeeded > 0 || failed > 0) {
            console.log(`[OfflineQueue] Flushed: ${succeeded} succeeded, ${failed} failed`);
          }
        });
      }
      wasOffline.current = !online;
    });

    return unsubscribe;
  }, []);

  return { isOnline, justReconnected };
}
