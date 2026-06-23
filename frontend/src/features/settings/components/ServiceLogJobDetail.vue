<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { ArrowPathIcon } from "@heroicons/vue/24/outline";

import {
  cancelJob,
  fetchJob,
  retryJob,
  type BackgroundJob,
} from "@/features/jobs/api";
import {
  formatJobJson,
  hasJson,
  jobDurationLabel,
  jobResultInsights,
  jobRunStepState,
  jobStatusLabel,
  jobTypeLabel,
} from "@/features/jobs/job-display";
import { formatDateTime } from "@/lib/datetime";
import { useToastStore } from "@/stores/toast";

const props = defineProps<{
  jobId: number;
}>();

const { t } = useI18n();
const toast = useToastStore();

const job = ref<BackgroundJob | null>(null);
const loading = ref(true);
const acting = ref(false);
const error = ref("");
const dataTab = ref<"payload" | "result">("result");

async function loadJob() {
  loading.value = true;
  error.value = "";
  try {
    job.value = await fetchJob(props.jobId);
    dataTab.value = hasJson(job.value.result) ? "result" : "payload";
  } catch (loadError) {
    job.value = null;
    error.value =
      loadError instanceof Error ? loadError.message : t("jobs.loadDetailFailed");
  } finally {
    loading.value = false;
  }
}

async function retryJobAction() {
  if (!job.value || acting.value) {
    return;
  }
  acting.value = true;
  try {
    job.value = await retryJob(job.value.id);
    toast.success(t("jobs.retried"));
  } catch (retryError) {
    error.value =
      retryError instanceof Error ? retryError.message : t("errors.retryJob");
  } finally {
    acting.value = false;
  }
}

async function cancelJobAction() {
  if (!job.value || acting.value) {
    return;
  }
  acting.value = true;
  try {
    job.value = await cancelJob(job.value.id);
    toast.success(t("jobs.cancelled"));
  } catch (cancelError) {
    error.value =
      cancelError instanceof Error ? cancelError.message : t("errors.cancelJob");
  } finally {
    acting.value = false;
  }
}

onMounted(() => {
  void loadJob();
});
</script>

<template>
  <div class="project-service-log-detail-body">
    <div v-if="loading" class="project-monitor-loading">
      <span class="loading-spinner" aria-hidden="true" />
      <span>{{ t("common.loading") }}</span>
    </div>

    <p v-else-if="error" class="project-monitor-error">{{ error }}</p>

    <div v-else-if="job" class="jobs-detail jobs-detail-embedded">
      <header class="jobs-detail-hero">
        <div class="jobs-detail-hero-text">
          <p class="jobs-detail-eyebrow">#{{ job.id }} · {{ job.job_type }}</p>
          <div class="jobs-detail-title-row">
            <h2 class="jobs-detail-title">{{ jobTypeLabel(job.job_type) }}</h2>
            <span class="jobs-status" :class="`jobs-status-${job.status}`">
              {{ jobStatusLabel(job.status) }}
            </span>
          </div>
        </div>
      </header>

      <div class="jobs-detail-body">
        <div class="jobs-run-track">
          <div class="jobs-run-step" :class="`jobs-run-step-${jobRunStepState(job, 'created')}`">
            <span class="jobs-run-label">{{ t("jobs.createdAt") }}</span>
            <span class="jobs-run-time">{{ formatDateTime(job.created_at) }}</span>
          </div>
          <div class="jobs-run-step" :class="`jobs-run-step-${jobRunStepState(job, 'started')}`">
            <span class="jobs-run-label">{{ t("jobs.startedAt") }}</span>
            <span class="jobs-run-time">{{ formatDateTime(job.started_at) }}</span>
          </div>
          <div class="jobs-run-step" :class="`jobs-run-step-${jobRunStepState(job, 'finished')}`">
            <span class="jobs-run-label">{{ t("jobs.finishedAt") }}</span>
            <span class="jobs-run-time">{{ formatDateTime(job.finished_at) }}</span>
          </div>
        </div>

        <div class="jobs-summary-row">
          <div v-if="jobDurationLabel(job)" class="jobs-summary-pill jobs-summary-pill-accent">
            {{ jobDurationLabel(job) }}
          </div>
          <div class="jobs-summary-pill">
            {{ t("jobs.attemptsLabel", { current: job.attempts, max: job.max_attempts }) }}
          </div>
        </div>

        <div v-if="jobResultInsights(job).length" class="jobs-insights">
          <div v-for="insight in jobResultInsights(job)" :key="insight.label" class="jobs-insight-card">
            <span class="jobs-insight-value">{{ insight.value }}</span>
            <span class="jobs-insight-label">{{ insight.label }}</span>
          </div>
        </div>

        <p v-if="job.last_error" class="jobs-detail-error">{{ job.last_error }}</p>

        <div class="jobs-data-section">
          <div class="jobs-data-tabs">
            <button
              class="jobs-data-tab"
              :class="{ 'jobs-data-tab-active': dataTab === 'result' }"
              type="button"
              @click="dataTab = 'result'"
            >
              {{ t("jobs.result") }}
              <span v-if="hasJson(job.result)" class="jobs-data-tab-dot" />
            </button>
            <button
              class="jobs-data-tab"
              :class="{ 'jobs-data-tab-active': dataTab === 'payload' }"
              type="button"
              @click="dataTab = 'payload'"
            >
              {{ t("jobs.payload") }}
              <span v-if="hasJson(job.payload)" class="jobs-data-tab-dot" />
            </button>
          </div>

          <div class="jobs-code-panel">
            <pre
              v-if="dataTab === 'result' && hasJson(job.result)"
              class="jobs-code-view"
            >{{ formatJobJson(job.result) }}</pre>
            <pre
              v-else-if="dataTab === 'payload' && hasJson(job.payload)"
              class="jobs-code-view"
            >{{ formatJobJson(job.payload) }}</pre>
            <div v-else class="jobs-code-empty">
              <span class="jobs-code-empty-icon">{ }</span>
              <p>{{ dataTab === "result" ? t("jobs.resultEmpty") : t("jobs.payloadEmpty") }}</p>
            </div>
          </div>
        </div>
      </div>

      <footer
        v-if="job.status === 'failed' || job.status === 'pending'"
        class="jobs-detail-footer"
      >
        <button
          v-if="job.status === 'failed'"
          class="btn-primary px-4 py-2 text-sm disabled:opacity-60"
          type="button"
          :disabled="acting"
          @click="retryJobAction"
        >
          <ArrowPathIcon class="icon-sm" />
          {{ t("jobs.retry") }}
        </button>
        <button
          v-if="job.status === 'pending'"
          class="btn-ghost px-4 py-2 text-sm disabled:opacity-60"
          type="button"
          :disabled="acting"
          @click="cancelJobAction"
        >
          {{ t("jobs.cancel") }}
        </button>
      </footer>
    </div>
  </div>
</template>
