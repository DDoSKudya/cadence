<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { ArrowLeftIcon, ChevronRightIcon } from "@heroicons/vue/24/outline";
import {
  BoltIcon,
  ClipboardDocumentListIcon,
  CpuChipIcon,
  HeartIcon,
  InboxStackIcon,
} from "@heroicons/vue/24/outline";

import ServiceLogEntryDetail from "@/features/settings/components/ServiceLogEntryDetail.vue";
import { jobTypeLabel } from "@/features/jobs/job-display";
import type { ServiceHealth, ServiceLogEntry } from "@/features/settings/platform-api";
import {
  formatServiceLogFullTime,
  formatServiceLogMetaLine,
  parseWorkerJobLogMessage,
  resolveServiceLogTimestamp,
  serviceLogLevelClass,
  stripServiceLogFilePrefix,
} from "@/features/settings/service-log-display";
import { useServiceLogs } from "@/features/settings/useServiceLogs";

const props = defineProps<{
  service: ServiceHealth;
  serviceLabel: string;
}>();

const emit = defineEmits<{
  close: [];
}>();

const { t } = useI18n();
const serviceId = computed(() => props.service.id);
const { entries, hasFile, loading, error } = useServiceLogs(serviceId);
const logViewport = ref<HTMLElement | null>(null);
const stickToTop = ref(true);
const selectedEntry = ref<{ entry: ServiceLogEntry; index: number } | null>(null);

function isNearTop(element: HTMLElement, threshold = 48): boolean {
  return element.scrollTop <= threshold;
}

function onViewportScroll() {
  const viewport = logViewport.value;
  if (!viewport) {
    return;
  }
  stickToTop.value = isNearTop(viewport);
}

const hint = computed(() => {
  const key = hasFile.value
    ? `settings.project.logs.hints.${props.service.id}`
    : `settings.project.logs.hintsNoFile.${props.service.id}`;
  return t(key);
});

function statusLabel(status: ServiceHealth["status"]) {
  return t(`settings.project.status.${status}`);
}

function sourceLabel(source: ServiceLogEntry["source"]) {
  return t(`settings.project.logs.sources.${source}`);
}

function entryTitle(entry: ServiceLogEntry) {
  if (entry.job_id || entry.source === "jobs") {
    const parsed = parseWorkerJobLogMessage(entry.message);
    if (parsed) {
      return jobTypeLabel(parsed.jobType);
    }
  }

  const text = entryText(entry);
  if (text.length > 72) {
    return `${text.slice(0, 69)}…`;
  }
  return text;
}

function entryMetaLine(entry: ServiceLogEntry) {
  return formatServiceLogMetaLine(entry, sourceLabel(entry.source));
}

function entryMetaTitle(entry: ServiceLogEntry) {
  return formatServiceLogFullTime(resolveServiceLogTimestamp(entry));
}

function entryStatusClass(entry: ServiceLogEntry) {
  if (entry.source === "jobs" || entry.job_id) {
    const parsed = parseWorkerJobLogMessage(entry.message);
    if (parsed) {
      return parsed.status;
    }
  }
  return serviceLogLevelClass(entry.level);
}

function entryText(entry: ServiceLogEntry) {
  if (entry.source === "file") {
    return stripServiceLogFilePrefix(entry.message);
  }
  return entry.message;
}

function entryIcon(entry: ServiceLogEntry) {
  if (entry.source === "jobs" || entry.job_id) {
    return InboxStackIcon;
  }
  if (entry.source === "health") {
    return HeartIcon;
  }
  if (entry.source === "file") {
    return ClipboardDocumentListIcon;
  }
  if (entry.source === "process" && props.service.id === "worker") {
    return CpuChipIcon;
  }
  return BoltIcon;
}

function openEntry(entry: ServiceLogEntry, index: number) {
  selectedEntry.value = { entry, index };
}

function closeEntry() {
  selectedEntry.value = null;
}

async function scrollToTop() {
  await nextTick();
  const viewport = logViewport.value;
  if (!viewport || !stickToTop.value) {
    return;
  }
  viewport.scrollTop = 0;
}

watch(
  () => props.service.id,
  () => {
    selectedEntry.value = null;
    stickToTop.value = true;
    void scrollToTop();
  },
);

watch(entries, () => {
  void scrollToTop();
}, { flush: "post" });
</script>

<template>
  <Transition mode="out-in" name="project-monitor-swap">
    <ServiceLogEntryDetail
      v-if="selectedEntry"
      key="log-detail"
      :entry="selectedEntry.entry"
      @close="closeEntry"
    />

    <section v-else key="log-list" class="project-service-logs">
      <header class="project-service-logs-header">
        <button type="button" class="project-service-logs-back" @click="emit('close')">
          <span class="project-service-logs-back-icon" aria-hidden="true">
            <ArrowLeftIcon />
          </span>
          <span class="project-service-logs-back-label">{{ t("settings.project.logs.back") }}</span>
        </button>

        <div class="project-service-logs-title-wrap">
          <h3 class="project-service-logs-title">{{ serviceLabel }}</h3>
          <span
            class="project-monitor-service-badge"
            :class="`project-monitor-service-badge-${service.status}`"
          >
            {{ statusLabel(service.status) }}
          </span>
          <span v-if="entries.length > 0" class="project-service-logs-total">
            {{ t("settings.project.logs.entryCount", entries.length) }}
          </span>
        </div>

        <p v-if="hint" class="project-service-logs-hint">{{ hint }}</p>
      </header>

      <div v-if="loading" class="project-monitor-loading project-service-logs-loading">
        <span class="loading-spinner" aria-hidden="true" />
        <span>{{ t("common.loading") }}</span>
      </div>

      <p v-else-if="error" class="project-monitor-error">{{ error }}</p>

      <p v-else-if="entries.length === 0" class="project-service-logs-empty">
        {{ t("settings.project.logs.empty") }}
      </p>

      <div
        v-else
        ref="logViewport"
        class="project-service-log-list-wrap"
        role="log"
        aria-live="polite"
        @scroll="onViewportScroll"
      >
        <div class="project-service-log-list">
          <article
            v-for="(entry, index) in entries"
            :key="`${entry.logged_at}-${entry.source}-${entry.job_id ?? ''}-${index}`"
            class="project-service-log-item"
            :class="[
              `project-service-log-item-${entryStatusClass(entry)}`,
              { 'project-service-log-item-expandable': entry.job_id || entry.message.length > 80 },
            ]"
            role="button"
            tabindex="0"
            :aria-label="t('settings.project.logs.openEntry')"
            @click="openEntry(entry, index)"
            @keydown.enter.prevent="openEntry(entry, index)"
            @keydown.space.prevent="openEntry(entry, index)"
          >
            <span
              class="project-service-log-icon"
              :class="`project-service-log-icon-${entryStatusClass(entry)}`"
            >
              <component :is="entryIcon(entry)" class="icon-sm" />
            </span>

            <div class="project-service-log-main">
              <div class="project-service-log-top">
                <span class="project-service-log-title">{{ entryTitle(entry) }}</span>
                <span
                  class="project-service-logs-level"
                  :class="`project-service-logs-level-${serviceLogLevelClass(entry.level)}`"
                >
                  {{ entry.level }}
                </span>
              </div>
              <p
                class="project-service-log-meta"
                :title="entryMetaTitle(entry)"
              >
                {{ entryMetaLine(entry) }}
              </p>
            </div>

            <span class="project-service-log-chevron" aria-hidden="true">
              <ChevronRightIcon class="icon-sm" />
            </span>
          </article>
        </div>
      </div>
    </section>
  </Transition>
</template>
