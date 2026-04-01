/**
 * i18n configuration for PermitAI mobile app.
 * Supports: English, Spanish, Korean, Chinese (Simplified), Filipino (Tagalog)
 */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import * as Localization from "expo-localization";

import en from "./en.json";
import es from "./es.json";
import ko from "./ko.json";
import zh from "./zh.json";
import tl from "./tl.json";

const resources = {
  en: { translation: en },
  es: { translation: es },
  ko: { translation: ko },
  zh: { translation: zh },
  tl: { translation: tl },
};

// Map device locale to our supported languages
function getDeviceLanguage(): string {
  const locales = Localization.getLocales();
  if (!locales || locales.length === 0) return "en";

  const deviceLang = locales[0].languageCode;
  if (deviceLang && deviceLang in resources) {
    return deviceLang;
  }

  // Map common locale codes
  const mapping: Record<string, string> = {
    "zh-Hans": "zh",
    "zh-Hant": "zh",
    fil: "tl",
    tl: "tl",
  };

  const tag = locales[0].languageTag;
  for (const [key, val] of Object.entries(mapping)) {
    if (tag?.startsWith(key)) return val;
  }

  return "en";
}

i18n.use(initReactI18next).init({
  resources,
  lng: getDeviceLanguage(),
  fallbackLng: "en",
  interpolation: {
    escapeValue: false,
  },
  react: {
    useSuspense: false,
  },
});

export default i18n;
export const supportedLanguages = [
  { code: "en", label: "English" },
  { code: "es", label: "Español" },
  { code: "ko", label: "한국어" },
  { code: "zh", label: "中文" },
  { code: "tl", label: "Filipino" },
] as const;
