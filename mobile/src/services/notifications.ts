/**
 * Push notification registration + handling for Expo.
 */
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";
import { router } from "expo-router";

// Configure how notifications behave when app is foregrounded
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

/**
 * Register for push notifications and return the Expo push token.
 * The token should be sent to the backend via PUT /users/me with firebase_token.
 */
export async function registerForPushNotifications(): Promise<string | null> {
  const { status: existingStatus } = await Notifications.getPermissionsAsync();
  let finalStatus = existingStatus;

  if (existingStatus !== "granted") {
    const { status } = await Notifications.requestPermissionsAsync();
    finalStatus = status;
  }

  if (finalStatus !== "granted") {
    console.warn("Push notification permission not granted");
    return null;
  }

  // Android notification channel
  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("permits", {
      name: "Permit Updates",
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: "#1e3a5f",
    });
  }

  const tokenData = await Notifications.getExpoPushTokenAsync();
  return tokenData.data;
}

/**
 * Set up deep link handling from notification taps.
 * Maps notification payloads to app screens.
 */
export function setupNotificationListeners(): () => void {
  // Handle notification taps (app in background/killed)
  const responseSubscription =
    Notifications.addNotificationResponseReceivedListener((response) => {
      const data = response.notification.request.content.data;

      if (data?.project_id) {
        router.push(`/project/${data.project_id}`);
      } else if (data?.screen) {
        router.push(data.screen as string);
      }
    });

  // Handle notifications received while app is open
  const receivedSubscription =
    Notifications.addNotificationReceivedListener((notification) => {
      console.log("Notification received in foreground:", notification);
    });

  // Return cleanup function
  return () => {
    responseSubscription.remove();
    receivedSubscription.remove();
  };
}

/**
 * Get the current badge count.
 */
export async function getBadgeCount(): Promise<number> {
  return Notifications.getBadgeCountAsync();
}

/**
 * Clear badge count.
 */
export async function clearBadge(): Promise<void> {
  await Notifications.setBadgeCountAsync(0);
}
