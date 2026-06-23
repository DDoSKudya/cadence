<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { ArrowLeftIcon } from "@heroicons/vue/24/outline";

import type { ServiceLogEntry } from "@/features/settings/platform-api";
import ServiceLogJobDetail from "@/features/settings/components/ServiceLogJobDetail.vue";
import {
  formatServiceLogFullTime,
  resolveServiceLogTimestamp,
  serviceLogLevelClass,
} from "@/features/settings/service-log-display";

const props = defineProps<{
  entry: ServiceLogEntry;
}>();

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n();

function sourceLabel(source: ServiceLogEntry["source"]) {
  return t(`settings.project.logs.sources.${source}`);
}

const summary = computed(() => {
  const text = props.entry.message.trim();
  const separator = text.indexOf(": ");
  if (separator >= 0 && separator < 80) {
    return text.slice(separator + 2);
  }
  return text.length > 160 ? `${text.slice(0, 157)}…` : text;
});

const fullMessage = computed(() => props.entry.message.trim());
</script>

<template>
  <section class="project-service-logs project-service-log-detail">
    <header class="project-service-logs-header">
      <button type="button" class="project-service-logs-back" @click="emit('close')">
        <span class="project-service-logs-back-icon" aria-hidden="true">
          <ArrowLeftIcon />
        </span>
        <span class="project-service-logs-back-label">{{ t("settings.project.logs.detail.back") }}</span>
      </button>

      <div class="project-service-logs-title-wrap">
        <h3 class="project-service-logs-title">{{ t("settings.project.logs.detail.title") }}</h3>
        <span
          class="project-service-logs-level"
          :class="`project-service-logs-level-${serviceLogLevelClass(entry.level)}`"
        >
          {{ entry.level }}
        </span>
        <span
          class="project-service-logs-source"
          :class="`project-service-logs-source-${entry.source}`"
        >
          {{ sourceLabel(entry.source) }}
        </span>
      </div>

      <p class="project-service-logs-hint">
        {{ formatServiceLogFullTime(resolveServiceLogTimestamp(entry)) }} · {{ summary }}
      </p>
    </header>

    <ServiceLogJobDetail v-if="entry.job_id" :job-id="entry.job_id" />

    <div v-else class="project-service-log-detail-body">
      <div class="jobs-data-section">
        <p class="jobs-filter-label">{{ t("settings.project.logs.detail.message") }}</p>
        <div class="jobs-code-panel">
          <pre class="jobs-code-view">{{ fullMessage }}</pre>
        </div>
      </div>
    </div>
  </section>
</template>
