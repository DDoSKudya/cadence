import { ref } from "vue";
import { useI18n } from "vue-i18n";

import {
  cloneNotificationSettings,
  fetchNotificationSettings,
  saveNotificationSettings,
  type NotificationSettingsForm,
  type NotificationSettingsUpdate,
} from "@/features/settings/project-api";
import type { AppLocale } from "@/features/settings/project-api";
import { useLocaleStore } from "@/stores/locale";
import { useToastStore } from "@/stores/toast";
import { useActionFeedback } from "@/composables/useActionFeedback";

export function useProjectSettings() {
  const { t } = useI18n();
  const localeStore = useLocaleStore();
  const toast = useToastStore();
  const feedback = useActionFeedback();

  const loading = ref(true);
  const loadFailed = ref(false);
  const saving = ref(false);
  const error = ref("");
  const form = ref<NotificationSettingsForm | null>(null);
  const savedForm = ref<NotificationSettingsForm | null>(null);

  async function loadSettings() {
    loading.value = true;
    loadFailed.value = false;
    error.value = "";
    try {
      const data = await fetchNotificationSettings();
      form.value = data;
      savedForm.value = cloneNotificationSettings(data);
      localeStore.applyLocale(data.language);
    } catch (loadError) {
      loadFailed.value = true;
      form.value = null;
      savedForm.value = null;
      error.value =
        loadError instanceof Error ? loadError.message : t("errors.loadSettings");
    } finally {
      loading.value = false;
    }
  }

  function flashNotice(message = t("toast.settingsSaved")) {
    toast.success(message);
  }

  async function patchSettings(updates: NotificationSettingsUpdate, options?: { notice?: string }) {
    if (!form.value) {
      return false;
    }

    saving.value = true;
    error.value = "";
    try {
      const updated = await saveNotificationSettings(updates);
      form.value = updated;
      savedForm.value = cloneNotificationSettings(updated);
      if (updates.language) {
        localeStore.applyLocale(updated.language);
      }
      flashNotice(options?.notice);
      return true;
    } catch (saveError) {
      feedback.fromError(saveError, "errors.saveSettings");
      return false;
    } finally {
      saving.value = false;
    }
  }

  async function saveLanguage(language: AppLocale) {
    saving.value = true;
    error.value = "";
    try {
      await localeStore.setLocale(language);
      if (form.value) {
        form.value.language = language;
        savedForm.value = cloneNotificationSettings(form.value);
      }
      flashNotice(t("settings.languageSaved"));
      return true;
    } catch (saveError) {
      feedback.fromError(saveError, "settings.languageSaveFailed");
      return false;
    } finally {
      saving.value = false;
    }
  }

  return {
    loading,
    loadFailed,
    saving,
    error,
    form,
    savedForm,
    loadSettings,
    patchSettings,
    saveLanguage,
    flashNotice,
  };
}
