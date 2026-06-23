import { defineStore } from "pinia";
import { computed, ref } from "vue";

import {
  type AppLocale,
  fetchProjectSettings,
  normalizeAppLocale,
  saveProjectLanguage,
} from "@/features/settings/project-api";
import { DEFAULT_LOCALE, setI18nLocale } from "@/i18n";

export const useLocaleStore = defineStore("locale", () => {
  const locale = ref<AppLocale>(DEFAULT_LOCALE);
  const loaded = ref(false);
  const saving = ref(false);
  const error = ref("");

  const isEnglish = computed(() => locale.value === "en");

  function applyLocale(nextLocale: AppLocale) {
    locale.value = normalizeAppLocale(nextLocale);
    setI18nLocale(locale.value);
  }

  async function load() {
    error.value = "";
    try {
      const settings = await fetchProjectSettings();
      applyLocale(settings.language);
    } catch (loadError) {
      applyLocale(DEFAULT_LOCALE);
      error.value = loadError instanceof Error ? loadError.message : "";
    } finally {
      loaded.value = true;
    }
  }

  async function setLocale(nextLocale: AppLocale) {
    const normalized = normalizeAppLocale(nextLocale);
    const previous = locale.value;

    applyLocale(normalized);
    saving.value = true;
    error.value = "";

    try {
      const settings = await saveProjectLanguage(normalized);
      applyLocale(settings.language);
    } catch (saveError) {
      applyLocale(previous);
      error.value = saveError instanceof Error ? saveError.message : "";
      throw saveError;
    } finally {
      saving.value = false;
    }
  }

  applyLocale(DEFAULT_LOCALE);

  return {
    locale,
    loaded,
    saving,
    error,
    isEnglish,
    applyLocale,
    load,
    setLocale,
  };
});
