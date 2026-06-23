import type { AppLocale } from "@/features/settings/project-api";

export const APP_LOCALES: AppLocale[] = ["en", "ru"];

export function localeLabelKey(locale: AppLocale): "settings.languageEnglish" | "settings.languageRussian" {
  return locale === "ru" ? "settings.languageRussian" : "settings.languageEnglish";
}
