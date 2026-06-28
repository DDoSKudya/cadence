<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  ArchiveBoxIcon,
  ArrowDownTrayIcon,
  ArrowUpTrayIcon,
  BellAlertIcon,
  CalendarDaysIcon,
  Cog6ToothIcon,
  DocumentTextIcon,
  TagIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";

import {
  createAnalyticsExport,
  downloadAnalyticsExport,
  fetchAnalyticsExport,
  fetchExportPreview,
} from "@/features/analytics/api";
import ExportPreview from "@/features/analytics/components/ExportPreview.vue";
import type {
  AnalyticsFilters,
  ExportFormat,
  ExportPreviewSheetsMap,
  ExportSnapshot,
  ExportType,
} from "@/features/analytics/types";
import { useActionFeedback } from "@/composables/useActionFeedback";
import { getI18nLocale } from "@/i18n";

const props = defineProps<{
  filters: AnalyticsFilters;
  snapshot: ExportSnapshot;
}>();

const open = defineModel<boolean>("open", { default: false });
const { t } = useI18n();
const feedback = useActionFeedback();

interface ReportOption {
  value: ExportType;
  labelKey: string;
  descriptionKey: string;
  icon: typeof DocumentTextIcon;
  accent: string;
}

const reportOptions: ReportOption[] = [
  {
    value: "tasks",
    labelKey: "analytics.reportTasks",
    descriptionKey: "analytics.exportDesc.tasks",
    icon: DocumentTextIcon,
    accent: "export-report-accent-primary",
  },
  {
    value: "archive",
    labelKey: "analytics.reportArchive",
    descriptionKey: "analytics.exportDesc.archive",
    icon: ArchiveBoxIcon,
    accent: "export-report-accent-slate",
  },
  {
    value: "weekly_summary",
    labelKey: "analytics.reportWeeklySummary",
    descriptionKey: "analytics.exportDesc.weekly_summary",
    icon: CalendarDaysIcon,
    accent: "export-report-accent-accent",
  },
  {
    value: "tag_summary",
    labelKey: "analytics.reportTagSummary",
    descriptionKey: "analytics.exportDesc.tag_summary",
    icon: TagIcon,
    accent: "export-report-accent-violet",
  },
  {
    value: "notification_report",
    labelKey: "analytics.reportNotifications",
    descriptionKey: "analytics.exportDesc.notification_report",
    icon: BellAlertIcon,
    accent: "export-report-accent-warn",
  },
  {
    value: "jobs_report",
    labelKey: "analytics.reportJobs",
    descriptionKey: "analytics.exportDesc.jobs_report",
    icon: Cog6ToothIcon,
    accent: "export-report-accent-indigo",
  },
  {
    value: "imports_report",
    labelKey: "analytics.reportImports",
    descriptionKey: "analytics.exportDesc.imports_report",
    icon: ArrowUpTrayIcon,
    accent: "export-report-accent-teal",
  },
];

const exportType = ref<ExportType>("weekly_summary");
const fileFormat = ref<ExportFormat>("xlsx");
const submitting = ref(false);
const polling = ref(false);
const error = ref("");
const exportId = ref<number | null>(null);
const exportStatus = ref("");
const downloading = ref(false);
const previewSheets = ref<ExportPreviewSheetsMap>({});
const previewLoading = ref(false);
let pollGeneration = 0;
let previewGeneration = 0;

const selectedReport = computed(
  () => reportOptions.find((option) => option.value === exportType.value) ?? reportOptions[0],
);

const canDownload = computed(() => exportStatus.value === "succeeded" && exportId.value !== null);

const isBusy = computed(() => submitting.value || polling.value || downloading.value);

function resetExportJob() {
  pollGeneration += 1;
  error.value = "";
  exportId.value = null;
  exportStatus.value = "";
  submitting.value = false;
  polling.value = false;
  downloading.value = false;
}

watch(open, (isOpen) => {
  if (!isOpen) {
    resetExportJob();
  }
});

watch(fileFormat, () => {
  resetExportJob();
});

async function loadPreview() {
  if (!open.value) {
    return;
  }
  const generation = ++previewGeneration;
  previewLoading.value = true;
  try {
    const response = await fetchExportPreview(exportType.value, props.filters);
    if (generation !== previewGeneration) {
      return;
    }
    previewSheets.value = Object.fromEntries(
      response.sheets.map((sheet) => [
        sheet.id,
        {
          rows: sheet.rows,
          total: sheet.total,
          ...(sheet.kpis ? { kpis: sheet.kpis } : {}),
        },
      ]),
    );
  } catch {
    if (generation === previewGeneration) {
      previewSheets.value = {};
      feedback.error(t("errors.loadExportPreview"));
    }
  } finally {
    if (generation === previewGeneration) {
      previewLoading.value = false;
    }
  }
}

watch(
  [open, exportType, () => props.filters],
  () => {
    if (open.value) {
      void loadPreview();
    }
  },
  { deep: true },
);

function close() {
  open.value = false;
}

function selectReport(type: ExportType) {
  if (type !== exportType.value) {
    resetExportJob();
    previewGeneration += 1;
  }
  exportType.value = type;
}

async function pollExport(id: number) {
  const generation = pollGeneration;
  polling.value = true;
  try {
    for (let attempt = 0; attempt < 30; attempt += 1) {
      if (generation !== pollGeneration) {
        return;
      }
      const job = await fetchAnalyticsExport(id);
      if (generation !== pollGeneration) {
        return;
      }
      exportStatus.value = job.status;
      if (job.status === "succeeded" || job.status === "failed") {
        if (job.status === "failed") {
          error.value = job.error_message || t("analytics.exportJobFailed");
          feedback.error(error.value);
        }
        return;
      }
      await new Promise((resolve) => window.setTimeout(resolve, 1000));
    }
    if (generation !== pollGeneration) {
      return;
    }
    error.value = t("analytics.exportTimeout");
    feedback.error(error.value);
  } finally {
    if (generation === pollGeneration) {
      polling.value = false;
    }
  }
}

function buildFiltersPayload(): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    locale: getI18nLocale(),
  };
  if (props.filters.week) {
    payload.week = props.filters.week;
  }
  if (props.filters.from) {
    payload.from = props.filters.from;
  }
  if (props.filters.to) {
    payload.to = props.filters.to;
  }
  if (props.filters.tag) {
    payload.tags = [props.filters.tag];
  }
  if (props.filters.source) {
    payload.source = props.filters.source;
  }
  return payload;
}

async function submit() {
  if (isBusy.value) {
    return;
  }
  resetExportJob();
  submitting.value = true;
  error.value = "";
  const generation = pollGeneration;
  try {
    const job = await createAnalyticsExport({
      export_type: exportType.value,
      file_format: fileFormat.value,
      filters: buildFiltersPayload(),
    });
    if (generation !== pollGeneration) {
      return;
    }
    exportId.value = job.id;
    exportStatus.value = job.status;
    if (job.status === "pending" || job.status === "processing") {
      await pollExport(job.id);
    } else if (job.status === "failed") {
      error.value = job.error_message || t("analytics.exportJobFailed");
      feedback.error(error.value);
    }
    if (generation === pollGeneration && exportStatus.value === "succeeded") {
      feedback.successKey("toast.exportReady");
    }
  } catch (err) {
    if (generation !== pollGeneration) {
      return;
    }
    error.value = err instanceof Error ? err.message : t("analytics.exportFailed");
    feedback.fromError(err, "analytics.exportFailed");
  } finally {
    if (generation === pollGeneration) {
      submitting.value = false;
    }
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
    <Transition name="export-modal">
      <div v-if="open" class="export-modal-backdrop" @click.self="close">
        <section
          class="export-modal"
          role="dialog"
          aria-labelledby="analytics-export-title"
          aria-modal="true"
        >
          <header class="export-modal-header">
            <div>
              <p class="drawer-eyebrow">{{ $t("analytics.exportEyebrow") }}</p>
              <h2 id="analytics-export-title" class="export-modal-title">
                {{ $t("analytics.exportTitle") }}
              </h2>
              <p class="export-modal-subtitle">{{ $t("analytics.exportSubtitle") }}</p>
            </div>
            <button class="icon-btn" type="button" @click="close">
              <XMarkIcon class="icon-sm" />
            </button>
          </header>

          <div class="export-modal-body">
            <aside class="export-modal-sidebar">
              <p class="export-modal-section-label">{{ $t("analytics.reportType") }}</p>
              <div class="export-report-list">
                <button
                  v-for="option in reportOptions"
                  :key="option.value"
                  class="export-report-card"
                  :class="{
                    'export-report-card-active': exportType === option.value,
                    [option.accent]: exportType === option.value,
                  }"
                  type="button"
                  @click="selectReport(option.value)"
                >
                  <span class="export-report-card-icon">
                    <component :is="option.icon" class="icon-sm" />
                  </span>
                  <span class="export-report-card-copy">
                    <span class="export-report-card-title">{{ $t(option.labelKey) }}</span>
                    <span class="export-report-card-desc">{{ $t(option.descriptionKey) }}</span>
                  </span>
                </button>
              </div>
            </aside>

            <div class="export-modal-preview-pane">
              <p class="export-modal-section-label">{{ $t("analytics.exportPreview.title") }}</p>
              <Transition name="export-preview-swap" mode="out-in">
                <ExportPreview
                  :key="`${exportType}-${fileFormat}`"
                  :export-type="exportType"
                  :file-format="fileFormat"
                  :snapshot="snapshot"
                  :preview-sheets="previewSheets"
                />
              </Transition>
            </div>
          </div>

          <footer class="export-modal-footer">
            <div class="export-modal-status">
              <p v-if="error" class="alert-error">{{ error }}</p>
              <p v-else-if="previewLoading" class="text-sm text-(--color-text-secondary)">
                {{ $t("analytics.exportPreview.loading") }}
              </p>
              <p v-else-if="polling" class="text-sm text-(--color-text-secondary)">
                {{ $t("analytics.generating") }}
              </p>
              <p v-else-if="exportStatus === 'succeeded'" class="text-sm text-[#067647]">
                {{ $t("analytics.fileReady") }}
              </p>
              <p v-else class="text-sm text-(--color-text-secondary)">
                {{ $t(selectedReport.descriptionKey) }}
              </p>
            </div>
            <div class="export-modal-toolbar">
              <label class="export-modal-format">
                <span class="export-modal-format-label">{{ $t("analytics.fileFormat") }}</span>
                <select v-model="fileFormat" class="export-modal-format-select field">
                  <option value="xlsx">{{ $t("analytics.formatXlsx") }}</option>
                  <option value="pdf">{{ $t("analytics.formatPdf") }}</option>
                  <option value="csv">{{ $t("analytics.formatCsv") }}</option>
                </select>
              </label>
              <div class="export-modal-actions">
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
                  :disabled="isBusy"
                  @click="submit"
                >
                  {{ submitting || polling ? $t("analytics.preparing") : $t("analytics.createExport") }}
                </button>
              </div>
            </div>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>
