import { createI18n } from "vue-i18n";

import { en } from "@/i18n/locales/en";
import { ru } from "@/i18n/locales/ru";
import type { AppLocale } from "@/features/settings/project-api";

export const DEFAULT_LOCALE: AppLocale = "en";
export const SUPPORTED_LOCALES: AppLocale[] = ["en", "ru"];

export const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: DEFAULT_LOCALE,
  fallbackLocale: DEFAULT_LOCALE,
  messages: {
    en,
    ru,
  },
  pluralRules: {
    ru(choice: number, choicesLength: number) {
      if (choicesLength < 3) {
        return choice === 1 ? 0 : 1;
      }

      const value = Math.abs(choice);
      const mod10 = value % 10;
      const mod100 = value % 100;

      if (mod10 === 1 && mod100 !== 11) {
        return 0;
      }
      if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
        return 1;
      }
      return 2;
    },
  },
});

export function t(
  key: string,
  pluralOrParams?: number | Record<string, unknown>,
  named?: Record<string, unknown>,
): string {
  if (typeof pluralOrParams === "number") {
    if (named) {
      return i18n.global.t(key, pluralOrParams, named);
    }
    return i18n.global.t(key, pluralOrParams);
  }
  return i18n.global.t(key, pluralOrParams ?? {});
}

export function setI18nLocale(locale: AppLocale) {
  i18n.global.locale.value = locale;
  document.documentElement.lang = locale;
}
