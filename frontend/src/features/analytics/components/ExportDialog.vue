<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import { ArrowDownTrayIcon, XMarkIcon } from "@heroicons/vue/24/outline";

import {
  createAnalyticsExport,
  downloadAnalyticsExport,
  fetchAnalyticsExport,
} from "@/features/analytics/api";
import type { AnalyticsFilters, ExportFormat, ExportType } from "@/features/analytics/types";
import { useActionFeedback } from "@/composables/useActionFeedback";

const props = defineProps<{
  filters: AnalyticsFilters;
}>();

const open = defineModel<boolean>("open", { default: false });
const { t } = useI18n();
const feedback = useActionFeedback();

const exportType = ref<ExportType>("tasks");
const fileFormat = ref<ExportFormat>("csv");
const submitting = ref(false);
const polling = ref(false);
const error = ref("");
const exportId = ref<number | null>(null);
const exportStatus = ref("");

const exportOptions: { value: ExportType; label: string }[] = [
  { value: "tasks", label: "analytics.reportTasks" },
  { value: "archive", label: "analytics.reportArchive" },
  { value: "weekly_summary", label: "analytics.reportWeeklySummary" },
  { value: "tag_summary", label: "analytics.reportTagSummary" },
  { value: "notification_report", label: "analytics.reportNotifications" },
  { value: "jobs_report", label: "analytics.reportJobs" },
  { value: "imports_report", label: "analytics.reportImports" },
];

const downloading = ref(false);

const canDownload = computed(() => exportStatus.value === "succeeded" && exportId.value !== null);

function resetState() {
  error.value = "";
  exportId.value = null;
  exportStatus.value = "";
  submitting.value = false;
  polling.value = false;
  downloading.value = false;
}

function close() {
  open.value = false;
  resetState();
}

async function pollExport(id: number) {
  polling.value = true;
  for (let attempt = 0; attempt < 30; attempt += 1) {
    const job = await fetchAnalyticsExport(id);
    exportStatus.value = job.status;
    if (job.status === "succeeded" || job.status === "failed") {
      if (job.status === "failed") {
        error.value = job.error_message || t("analytics.exportJobFailed");
        feedback.error(error.value);
      }
      polling.value = false;
      return;
    }
    await new Promise((resolve) => window.setTimeout(resolve, 1000));
  }
  polling.value = false;
  error.value = t("analytics.exportTimeout");
  feedback.error(error.value);
}

async function submit() {
  submitting.value = true;
  error.value = "";
  try {
    const filters: Record<string, unknown> = {};
    if (props.filters.week) {
      filters.week = props.filters.week;
    }
    if (props.filters.from) {
      filters.from = props.filters.from;
    }
    if (props.filters.to) {
      filters.to = props.filters.to;
    }
    if (props.filters.tag) {
      filters.tags = [props.filters.tag];
    }
    if (props.filters.source) {
      filters.source = props.filters.source;
    }

    const format = exportType.value === "weekly_summary" ? "xlsx" : fileFormat.value;

    const job = await createAnalyticsExport({
      export_type: exportType.value,
      file_format: format,
      filters,
    });
    exportId.value = job.id;
    exportStatus.value = job.status;
    await pollExport(job.id);
    if (exportStatus.value === "succeeded") {
      feedback.successKey("toast.exportReady");
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : t("analytics.exportFailed");
    feedback.fromError(err, "analytics.exportFailed");
  } finally {
    submitting.value = false;
  }
}

async function download() {
  if (!exportId.value) {
    return;
  }
  downloading.value = true;
  error.value = "";
  try {
    await downloadAnalyticsExport(exportId.value);
    feedback.successKey("toast.exportDownloaded");
  } catch (err) {
    error.value = err instanceof Error ? err.message : t("analytics.downloadFailed");
    feedback.fromError(err, "analytics.downloadFailed");
  } finally {
    downloading.value = false;
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="slide-panel">
      <div v-if="open" class="drawer-backdrop" @click.self="close">
        <aside
          class="drawer-panel drawer-panel-narrow"
          role="dialog"
          aria-labelledby="analytics-export-title"
          aria-modal="true"
        >
          <header class="drawer-header">
            <div>
              <p class="drawer-eyebrow">{{ $t("analytics.exportEyebrow") }}</p>
              <h2 id="analytics-export-title" class="drawer-title">{{ $t("analytics.exportTitle") }}</h2>
            </div>
            <button class="icon-btn" type="button" @click="close">
              <XMarkIcon class="icon-sm" />
            </button>
          </header>

          <div class="drawer-body">
            <form class="task-form" @submit.prevent="canDownload ? download() : submit()">
              <label class="form-field">
                <span class="form-label">{{ $t("analytics.reportType") }}</span>
                <select v-model="exportType" class="field px-3 py-2">
                  <option v-for="option in exportOptions" :key="option.value" :value="option.value">
                    {{ $t(option.label) }}
                  </option>
                </select>
              </label>

              <label v-if="exportType !== 'weekly_summary'" class="form-field">
                <span class="form-label">{{ $t("analytics.fileFormat") }}</span>
                <select v-model="fileFormat" class="field px-3 py-2">
                  <option value="csv">CSV</option>
                  <option value="xlsx">XLSX</option>
                </select>
              </label>
              <p v-else class="text-sm text-(--color-text-secondary)">
                {{ $t("analytics.weeklySummaryHint") }}
              </p>

              <p v-if="error" class="alert-error">{{ error }}</p>
              <p v-else-if="polling" class="text-sm text-(--color-text-secondary)">
                {{ $t("analytics.generating") }}
              </p>
              <p v-else-if="exportStatus === 'succeeded'" class="text-sm text-[#067647]">
                {{ $t("analytics.fileReady") }}
              </p>
            </form>
          </div>

          <footer class="drawer-footer">
            <button
              v-if="canDownload"
              class="btn-primary"
              type="button"
              :disabled="downloading"
              @click="download"
            >
              <ArrowDownTrayIcon class="icon-sm" />
              {{ downloading ? $t("analytics.downloading") : $t("analytics.download") }}
            </button>
            <button
              v-else
              class="btn-primary"
              type="button"
              :disabled="submitting || polling"
              @click="submit"
            >
              {{ submitting || polling ? $t("analytics.preparing") : $t("analytics.createExport") }}
            </button>
          </footer>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>
