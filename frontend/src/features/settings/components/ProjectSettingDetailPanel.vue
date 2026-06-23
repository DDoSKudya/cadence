<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { ArrowLeftIcon } from "@heroicons/vue/24/outline";

import LocaleFlagIcon from "@/features/settings/components/LocaleFlagIcon.vue";
import { TIMEZONE_OPTIONS } from "@/features/settings/constants";
import { APP_LOCALES, localeLabelKey } from "@/features/settings/locale-display";
import type { ProjectSettingPanelId } from "@/features/settings/project-groups";
import type { AppLocale } from "@/features/settings/project-api";
import type { useProjectSettings } from "@/features/settings/useProjectSettings";

const props = defineProps<{
  panel: ProjectSettingPanelId;
  titleKey: string;
  hint: string;
  settings: ReturnType<typeof useProjectSettings>;
  language: AppLocale;
  timezone: string;
}>();

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n();

async function selectLanguage(language: AppLocale) {
  if (props.language === language) {
    return;
  }
  await props.settings.saveLanguage(language);
}

async function onTimezoneChange(event: Event) {
  const timezone = (event.target as HTMLSelectElement).value;
  await props.settings.patchSettings({ timezone });
}
</script>

<template>
  <section class="project-service-logs">
    <header class="project-service-logs-header">
      <button type="button" class="project-service-logs-back" @click="emit('close')">
        <span class="project-service-logs-back-icon" aria-hidden="true">
          <ArrowLeftIcon />
        </span>
        <span class="project-service-logs-back-label">{{ t("settings.project.config.back") }}</span>
      </button>

      <div class="project-service-logs-title-wrap">
        <h3 class="project-service-logs-title">{{ t(titleKey) }}</h3>
      </div>

      <p v-if="hint" class="project-service-logs-hint">{{ hint }}</p>
    </header>

    <div class="project-settings-detail-content">
      <div v-if="panel === 'language'" class="project-settings-options" role="radiogroup">
        <button
          v-for="locale in APP_LOCALES"
          :key="locale"
          type="button"
          role="radio"
          class="project-settings-option"
          :class="{ 'project-settings-option-active': language === locale }"
          :aria-checked="language === locale"
          :disabled="settings.saving.value"
          @click="selectLanguage(locale)"
        >
          <LocaleFlagIcon :locale="locale" />
          <span class="project-settings-option-copy">
            <span class="project-settings-option-title">{{ t(localeLabelKey(locale)) }}</span>
          </span>
        </button>
      </div>

      <form
        v-else-if="panel === 'timezone'"
        class="task-form project-settings-detail-form"
        @submit.prevent
      >
        <label class="form-field">
          <select
            class="field px-3 py-2"
            :disabled="settings.saving.value"
            :value="timezone"
            @change="onTimezoneChange"
          >
            <option v-for="zone in TIMEZONE_OPTIONS" :key="zone" :value="zone">
              {{ zone }}
            </option>
          </select>
          <span class="notify-field-hint">{{ t("settings.hub.items.timezone.description") }}</span>
        </label>
      </form>
    </div>
  </section>
</template>
