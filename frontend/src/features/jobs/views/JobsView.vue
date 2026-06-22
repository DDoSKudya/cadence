<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import {
  ArrowPathIcon,
  ArrowUpTrayIcon,
  CheckCircleIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ClipboardDocumentIcon,
  ClockIcon,
  ExclamationCircleIcon,
  FunnelIcon,
  InboxStackIcon,
  QueueListIcon,
  XCircleIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";

import {
  cancelJob,
  fetchJob,
  fetchJobs,
  retryJob,
  type BackgroundJob,
  type JobFilters,
} from "@/features/jobs/api";
import { pluralRu } from "@/lib/plural";
import { formatDateTime } from "@/lib/datetime";

const POLL_INTERVAL_MS = 5000;
const PAGE_SIZE = 20;

const jobs = ref<BackgroundJob[]>([]);
const totalCount = ref(0);
const page = ref(1);
const listKey = ref(0);
const selectedJob = ref<BackgroundJob | null>(null);
const loading = ref(true);
const pageLoading = ref(false);
const acting = ref(false);
const filtersOpen = ref(false);
const dataTab = ref<"payload" | "result">("result");
const copiedId = ref(false);
const error = ref("");
const notice = ref("");

const filters = ref<JobFilters>({
  job_type: "",
  status: "",
});

let pollTimer: ReturnType<typeof setInterval> | null = null;
let refreshSeq = 0;

const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / PAGE_SIZE)));

const pageRangeLabel = computed(() => {
  if (totalCount.value === 0) {
    return "";
  }
  const start = (page.value - 1) * PAGE_SIZE + 1;
  const end = Math.min(page.value * PAGE_SIZE, totalCount.value);
  return `${start}–${end} из ${totalCount.value}`;
});

const metaLine = computed(() => {
  if (loading.value) {
    return "загрузка журнала…";
  }
  const parts: string[] = [];
  if (totalCount.value === 0) {
    parts.push("нет записей");
  } else if (totalPages.value > 1) {
    parts.push(pageRangeLabel.value);
    parts.push(`стр. ${page.value}/${totalPages.value}`);
  } else {
    parts.push(pluralRu(jobs.value.length, "запись", "записи", "записей"));
  }
  parts.push("обновляется автоматически");
  return parts.join(" · ");
});

const sidebarCountLabel = computed(() => {
  if (totalCount.value === 0) {
    return "";
  }
  if (totalPages.value > 1) {
    return pageRangeLabel.value;
  }
  return pluralRu(jobs.value.length, "запись", "записи", "записей");
});

const filtersActive = computed(
  () => Boolean(filters.value.job_type || filters.value.status),
);

function jobSnapshot(job: BackgroundJob): string {
  return `${job.updated_at}:${job.status}:${job.attempts}:${job.last_error}`;
}

function jobsChanged(previous: BackgroundJob[], next: BackgroundJob[]): boolean {
  const prev = Array.isArray(previous) ? previous : [];
  const nxt = Array.isArray(next) ? next : [];
  if (prev.length !== nxt.length) {
    return true;
  }
  if (nxt.length === 0) {
    return prev.length > 0;
  }
  const nextById = new Map(nxt.map((job) => [job.id, jobSnapshot(job)]));
  return prev.some((job) => nextById.get(job.id) !== jobSnapshot(job));
}

async function syncSelectedJob(
  results: BackgroundJob[],
  options: { autoSelect?: boolean; pickFirst?: boolean } = {},
) {
  if (options.pickFirst) {
    if (results.length === 0) {
      selectedJob.value = null;
      return;
    }
    try {
      selectedJob.value = await fetchJob(results[0].id);
    } catch {
      selectedJob.value = results[0];
    }
    return;
  }

  const autoSelect = options.autoSelect ?? true;

  if (selectedJob.value) {
    const onPage = results.find((job) => job.id === selectedJob.value?.id);
    if (onPage) {
      if (jobSnapshot(onPage) !== jobSnapshot(selectedJob.value)) {
        selectedJob.value = onPage;
      }
      return;
    }

    try {
      const detail = await fetchJob(selectedJob.value.id);
      if (jobSnapshot(detail) !== jobSnapshot(selectedJob.value)) {
        selectedJob.value = detail;
      }
    } catch {
      selectedJob.value = results[0] ?? null;
    }
    return;
  }

  if (autoSelect && results.length > 0) {
    selectedJob.value = results[0];
  }
}

function applyListResponse(
  response: Awaited<ReturnType<typeof fetchJobs>>,
  requestPage: number,
  bumpKey = false,
) {
  const results = Array.isArray(response.results) ? response.results : [];

  jobs.value = results;
  totalCount.value = response.count;
  page.value = response.page ?? requestPage;
  if (bumpKey) {
    listKey.value += 1;
  }

  return results;
}

async function refreshJobs(
  options: { initial?: boolean; pageChange?: boolean; targetPage?: number } = {},
) {
  const seq = ++refreshSeq;
  const requestPage = options.targetPage ?? page.value;

  if (options.initial) {
    loading.value = true;
  } else if (options.pageChange) {
    pageLoading.value = true;
  }
  error.value = "";

  try {
    const response = await fetchJobs({
      job_type: filters.value.job_type || undefined,
      status: filters.value.status || undefined,
      page: requestPage,
      page_size: PAGE_SIZE,
    });
    if (seq !== refreshSeq) {
      return;
    }

    const results = Array.isArray(response.results) ? response.results : [];

    if (results.length === 0 && response.count > 0 && requestPage > 1) {
      const lastPage = Math.max(1, Math.ceil(response.count / PAGE_SIZE));
      if (lastPage !== requestPage) {
        await refreshJobs({ ...options, targetPage: lastPage });
        return;
      }
    }

    const pageChanged = page.value !== (response.page ?? requestPage);
    const dataChanged = jobsChanged(jobs.value, results);
    const changed = options.initial || options.pageChange || dataChanged || totalCount.value !== response.count || pageChanged;

    applyListResponse(response, requestPage, options.initial || options.pageChange || dataChanged);

    if (changed) {
      if (options.pageChange || options.initial) {
        await syncSelectedJob(results, { pickFirst: true });
      } else {
        await syncSelectedJob(results);
      }
    }
  } catch (loadError) {
    if (options.initial || options.pageChange) {
      error.value =
        loadError instanceof Error ? loadError.message : "Не удалось загрузить фоновые задачи";
    }
  } finally {
    if (options.initial) {
      loading.value = false;
    }
    if (options.pageChange) {
      pageLoading.value = false;
    }
  }
}

function goToPage(nextPage: number) {
  if (nextPage < 1 || nextPage > totalPages.value || nextPage === page.value || pageLoading.value) {
    return;
  }
  void refreshJobs({ pageChange: true, targetPage: nextPage });
}

async function selectJob(job: BackgroundJob) {
  error.value = "";
  try {
    selectedJob.value = await fetchJob(job.id);
    const index = jobs.value.findIndex((item) => item.id === job.id);
    if (index >= 0) {
      jobs.value[index] = selectedJob.value;
    }
  } catch (loadError) {
    error.value =
      loadError instanceof Error ? loadError.message : "Не удалось загрузить детали задачи";
  }
}

async function retrySelected() {
  if (!selectedJob.value) {
    return;
  }

  acting.value = true;
  error.value = "";
  notice.value = "";
  try {
    selectedJob.value = await retryJob(selectedJob.value.id);
    notice.value = "Задача повторена";
    await refreshJobs();
  } catch (retryError) {
    error.value =
      retryError instanceof Error ? retryError.message : "Не удалось повторить задачу";
  } finally {
    acting.value = false;
  }
}

async function cancelSelected() {
  if (!selectedJob.value) {
    return;
  }

  acting.value = true;
  error.value = "";
  notice.value = "";
  try {
    selectedJob.value = await cancelJob(selectedJob.value.id);
    notice.value = "Задача отменена";
    await refreshJobs();
  } catch (cancelError) {
    error.value =
      cancelError instanceof Error ? cancelError.message : "Не удалось отменить задачу";
  } finally {
    acting.value = false;
  }
}

function clearFilters() {
  filters.value.job_type = "";
  filters.value.status = "";
}

function jobTypeLabel(value: string): string {
  const labels: Record<string, string> = {
    json_inbox_scan: "Скан inbox",
    json_import_file: "Импорт задач",
    notification_scan: "Скан напоминаний",
    telegram_send: "Telegram отправка",
    telegram_callback: "Telegram callback",
  };
  return labels[value] || value;
}

function jobTypeHint(value: string): string {
  const hints: Record<string, string> = {
    json_inbox_scan: "Celery · папка pending",
    json_import_file: "Upload · JSON-файл",
    notification_scan: "Celery · stale/overdue",
    telegram_send: "Celery · aiogram",
    telegram_callback: "Bot · inline кнопки",
  };
  return hints[value] || value;
}

function isImportJob(jobType: string): boolean {
  return jobType === "json_import_file";
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: "Ожидание",
    processing: "Обработка",
    succeeded: "Готово",
    failed: "Ошибка",
    cancelled: "Отменена",
  };
  return labels[status] || status;
}

function formatJson(value: Record<string, unknown> | null | undefined): string {
  if (!value || typeof value !== "object") {
    return "";
  }
  if (Object.keys(value).length === 0) {
    return "";
  }
  return JSON.stringify(value, null, 2);
}

function hasJson(value: Record<string, unknown> | null | undefined): boolean {
  return Boolean(value && typeof value === "object" && Object.keys(value).length > 0);
}

interface JobInsight {
  label: string;
  value: string;
}

function resultInsights(job: BackgroundJob): JobInsight[] {
  const insights: JobInsight[] = [];
  const result = job.result;
  if (!result || typeof result !== "object") {
    return insights;
  }

  if (typeof result.processed === "number") {
    insights.push({ label: "Файлов", value: String(result.processed) });
  }
  if (typeof result.tasks_created === "number") {
    insights.push({ label: "Задач", value: String(result.tasks_created) });
  }
  if (result.skipped_duplicate === true) {
    insights.push({ label: "Дубликат", value: "пропущен" });
  }

  return insights;
}

function runStepState(
  job: BackgroundJob,
  step: "created" | "started" | "finished",
): "done" | "active" | "idle" {
  const timestamp =
    step === "created" ? job.created_at : step === "started" ? job.started_at : job.finished_at;
  if (!timestamp) {
    return "idle";
  }
  if (job.status === "processing" && step === "started" && !job.finished_at) {
    return "active";
  }
  if (job.status === "pending" && step === "created" && !job.started_at) {
    return "active";
  }
  return "done";
}

async function copyCeleryId(value: string) {
  try {
    await navigator.clipboard.writeText(value);
    copiedId.value = true;
    window.setTimeout(() => {
      copiedId.value = false;
    }, 1500);
  } catch {
    copiedId.value = false;
  }
}

function truncateId(value: string | null | undefined): string {
  if (!value) {
    return "";
  }
  if (value.length <= 28) {
    return value;
  }
  return `${value.slice(0, 12)}…${value.slice(-10)}`;
}

function durationLabel(job: BackgroundJob): string | null {
  if (!job.started_at || !job.finished_at) {
    return null;
  }
  const ms = new Date(job.finished_at).getTime() - new Date(job.started_at).getTime();
  if (ms < 1000) {
    return "< 1 сек";
  }
  if (ms < 60_000) {
    return `${Math.round(ms / 1000)} сек`;
  }
  return `${Math.round(ms / 60_000)} мин`;
}

watch(
  () => [filters.value.status, filters.value.job_type],
  () => {
    void refreshJobs({ targetPage: 1, pageChange: true });
  },
);

watch(selectedJob, (job) => {
  if (!job) {
    return;
  }
  dataTab.value = hasJson(job.result) ? "result" : "payload";
});

onMounted(() => {
  void refreshJobs({ initial: true });
  pollTimer = setInterval(() => {
    if (document.visibilityState === "visible") {
      void refreshJobs();
    }
  }, POLL_INTERVAL_MS);
});

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer);
  }
});
</script>

<template>
  <div class="settings-page jobs-page">
    <div class="board-shell jobs-shell">
      <header class="board-toolbar shrink-0">
        <div class="board-toolbar-info">
          <h1 class="page-title">Фоновые задачи</h1>
          <p class="page-meta">{{ metaLine }}</p>
        </div>
      </header>

      <p v-if="error" class="alert-error mx-4 mt-3 shrink-0">{{ error }}</p>
      <p v-else-if="notice" class="alert-notice mx-4 mt-3 shrink-0">{{ notice }}</p>

      <div class="jobs-body">
        <Transition mode="out-in" name="jobs-body-swap">
          <div v-if="loading" key="loading" class="jobs-state">
            <div class="loading-state">
              <span class="loading-spinner" aria-hidden="true" />
              <p class="text-sm text-[var(--color-text-secondary)]">Загрузка задач…</p>
            </div>
          </div>

          <div v-else-if="totalCount === 0" key="empty" class="jobs-state">
            <div class="jobs-empty">
              <span class="jobs-empty-icon">
                <QueueListIcon class="size-7" />
              </span>
              <p class="jobs-empty-title">
                {{ filtersActive ? "Нет задач по фильтру" : "Фоновых задач пока нет" }}
              </p>
              <p class="jobs-empty-text">
                {{
                  filtersActive
                    ? "Попробуйте другие фильтры или сбросьте их"
                    : "Записи появятся после импорта JSON или автоматического сканирования inbox"
                }}
              </p>
              <button
                v-if="filtersActive"
                class="btn-ghost mt-2 px-3 py-1.5 text-sm"
                type="button"
                @click="clearFilters"
              >
                Сбросить фильтры
              </button>
            </div>
          </div>

          <div v-else key="split" class="jobs-split">
          <aside class="jobs-sidebar">
            <div class="jobs-sidebar-toolbar">
              <p class="jobs-sidebar-label">
                Журнал
                <span v-if="sidebarCountLabel" class="jobs-sidebar-count">{{ sidebarCountLabel }}</span>
              </p>
              <button
                class="icon-btn"
                :class="{ 'icon-btn-active': filtersOpen || filtersActive }"
                type="button"
                title="Фильтры"
                @click="filtersOpen = !filtersOpen"
              >
                <FunnelIcon class="icon-sm" />
                <span v-if="filtersActive" class="jobs-filter-badge" aria-hidden="true" />
              </button>
            </div>

            <Transition name="jobs-filters-slide">
              <div v-if="filtersOpen" class="jobs-filters-panel">
                <label class="jobs-filter-field">
                  <span class="jobs-filter-label">Статус</span>
                  <select v-model="filters.status" class="field jobs-filter-select">
                    <option value="">Все</option>
                    <option value="succeeded">Готово</option>
                    <option value="failed">Ошибки</option>
                    <option value="processing">В работе</option>
                    <option value="pending">Ожидание</option>
                    <option value="cancelled">Отмена</option>
                  </select>
                </label>
                <label class="jobs-filter-field">
                  <span class="jobs-filter-label">Тип</span>
                  <select v-model="filters.job_type" class="field jobs-filter-select">
                    <option value="">Все типы</option>
                    <option value="json_inbox_scan">Inbox</option>
                    <option value="json_import_file">Import</option>
                  </select>
                </label>
                <button
                  v-if="filtersActive"
                  class="btn-ghost w-full px-3 py-2 text-sm"
                  type="button"
                  @click="clearFilters"
                >
                  <XMarkIcon class="icon-sm" />
                  Сбросить фильтры
                </button>
              </div>
            </Transition>

            <div class="jobs-list-wrap" :class="{ 'jobs-list-wrap-loading': pageLoading }">
              <Transition mode="out-in" name="jobs-page-swap">
                <div :key="listKey" class="jobs-list">
                  <article
                    v-for="(job, index) in jobs"
                    :key="job.id"
                    class="jobs-list-item"
                    :style="{ '--jobs-item-delay': `${index * 35}ms` }"
                    :class="{
                      'jobs-list-item-active': selectedJob?.id === job.id,
                      'jobs-list-item-processing': job.status === 'processing',
                    }"
                    role="button"
                    tabindex="0"
                    @click="selectJob(job)"
                    @keydown.enter.prevent="selectJob(job)"
                  >
                    <span class="jobs-list-icon" :class="`jobs-list-icon-${job.status}`">
                      <ArrowUpTrayIcon v-if="isImportJob(job.job_type)" class="icon-sm" />
                      <InboxStackIcon v-else class="icon-sm" />
                    </span>
                    <div class="jobs-list-main">
                      <div class="jobs-list-top">
                        <span class="jobs-list-title">{{ jobTypeLabel(job.job_type) }}</span>
                        <span class="jobs-status" :class="`jobs-status-${job.status}`">
                          {{ statusLabel(job.status) }}
                        </span>
                      </div>
                      <p class="jobs-list-meta">
                        {{ formatDateTime(job.created_at) }}
                        <span v-if="job.attempts > 0"> · {{ job.attempts }}/{{ job.max_attempts }}</span>
                      </p>
                    </div>
                  </article>
                </div>
              </Transition>
              <div v-if="pageLoading" class="jobs-list-overlay" aria-hidden="true">
                <span class="loading-spinner" />
              </div>
            </div>

            <nav v-if="totalPages > 1" class="jobs-pagination" aria-label="Страницы журнала">
              <button
                class="jobs-pagination-btn"
                type="button"
                title="Предыдущая страница"
                :disabled="page <= 1 || pageLoading"
                @click="goToPage(page - 1)"
              >
                <ChevronLeftIcon class="icon-sm" />
              </button>
              <div class="jobs-pagination-info">
                <span class="jobs-pagination-page">{{ page }} / {{ totalPages }}</span>
                <span class="jobs-pagination-range">{{ pageRangeLabel }}</span>
              </div>
              <button
                class="jobs-pagination-btn"
                type="button"
                title="Следующая страница"
                :disabled="page >= totalPages || pageLoading"
                @click="goToPage(page + 1)"
              >
                <ChevronRightIcon class="icon-sm" />
              </button>
            </nav>
          </aside>

          <section class="jobs-workspace">
            <Transition mode="out-in" name="settings-workspace">
              <div v-if="!selectedJob" key="placeholder" class="jobs-placeholder">
                <span class="jobs-placeholder-icon">
                  <QueueListIcon class="size-8" />
                </span>
                <p class="jobs-placeholder-title">Выберите задачу</p>
                <p class="jobs-placeholder-text">Payload, result и ошибки отобразятся здесь</p>
              </div>

              <div v-else :key="selectedJob.id" class="jobs-detail">
              <header class="jobs-detail-hero">
                <span class="jobs-detail-hero-icon" :class="`jobs-detail-hero-icon-${selectedJob.status}`">
                  <CheckCircleIcon v-if="selectedJob.status === 'succeeded'" class="size-6" />
                  <ExclamationCircleIcon v-else-if="selectedJob.status === 'failed'" class="size-6" />
                  <ClockIcon v-else-if="selectedJob.status === 'processing'" class="size-6" />
                  <XCircleIcon v-else-if="selectedJob.status === 'cancelled'" class="size-6" />
                  <QueueListIcon v-else class="size-6" />
                </span>
                <div class="jobs-detail-hero-text">
                  <p class="jobs-detail-eyebrow">#{{ selectedJob.id }} · {{ jobTypeHint(selectedJob.job_type) }}</p>
                  <div class="jobs-detail-title-row">
                    <h2 class="jobs-detail-title">{{ jobTypeLabel(selectedJob.job_type) }}</h2>
                    <span class="jobs-status" :class="`jobs-status-${selectedJob.status}`">
                      {{ statusLabel(selectedJob.status) }}
                    </span>
                  </div>
                </div>
              </header>

              <div class="jobs-detail-body">
                <div class="jobs-run-track">
                  <div
                    class="jobs-run-step"
                    :class="`jobs-run-step-${runStepState(selectedJob, 'created')}`"
                  >
                    <span class="jobs-run-label">Создана</span>
                    <span class="jobs-run-time">{{ formatDateTime(selectedJob.created_at) }}</span>
                  </div>
                  <div
                    class="jobs-run-step"
                    :class="`jobs-run-step-${runStepState(selectedJob, 'started')}`"
                  >
                    <span class="jobs-run-label">Старт</span>
                    <span class="jobs-run-time">{{ formatDateTime(selectedJob.started_at) }}</span>
                  </div>
                  <div
                    class="jobs-run-step"
                    :class="`jobs-run-step-${runStepState(selectedJob, 'finished')}`"
                  >
                    <span class="jobs-run-label">Финиш</span>
                    <span class="jobs-run-time">{{ formatDateTime(selectedJob.finished_at) }}</span>
                  </div>
                </div>

                <div class="jobs-summary-row">
                  <div v-if="durationLabel(selectedJob)" class="jobs-summary-pill jobs-summary-pill-accent">
                    <ClockIcon class="icon-sm" />
                    {{ durationLabel(selectedJob) }}
                  </div>
                  <div class="jobs-summary-pill">
                    {{ selectedJob.attempts }} / {{ selectedJob.max_attempts }} попыток
                  </div>
                  <button
                    v-if="selectedJob.celery_task_id"
                    class="jobs-summary-id"
                    type="button"
                    :title="selectedJob.celery_task_id"
                    @click="copyCeleryId(selectedJob.celery_task_id)"
                  >
                    <ClipboardDocumentIcon class="icon-sm" />
                    <span>{{ copiedId ? "Скопировано" : truncateId(selectedJob.celery_task_id) }}</span>
                  </button>
                </div>

                <TransitionGroup
                  v-if="resultInsights(selectedJob).length > 0"
                  name="jobs-insight"
                  tag="div"
                  class="jobs-insights"
                >
                  <div
                    v-for="(insight, index) in resultInsights(selectedJob)"
                    :key="insight.label"
                    class="jobs-insight-card"
                    :style="{ '--jobs-insight-delay': `${index * 60}ms` }"
                  >
                    <span class="jobs-insight-value">{{ insight.value }}</span>
                    <span class="jobs-insight-label">{{ insight.label }}</span>
                  </div>
                </TransitionGroup>

                <Transition name="jobs-alert-slide">
                  <p v-if="selectedJob.last_error" key="error" class="jobs-detail-error">
                    {{ selectedJob.last_error }}
                  </p>
                </Transition>

                <div class="jobs-data-section">
                  <div class="jobs-data-tabs">
                    <button
                      class="jobs-data-tab"
                      :class="{ 'jobs-data-tab-active': dataTab === 'result' }"
                      type="button"
                      @click="dataTab = 'result'"
                    >
                      Result
                      <span v-if="hasJson(selectedJob.result)" class="jobs-data-tab-dot" />
                    </button>
                    <button
                      class="jobs-data-tab"
                      :class="{ 'jobs-data-tab-active': dataTab === 'payload' }"
                      type="button"
                      @click="dataTab = 'payload'"
                    >
                      Payload
                      <span v-if="hasJson(selectedJob.payload)" class="jobs-data-tab-dot" />
                    </button>
                  </div>

                  <div class="jobs-code-panel">
                    <Transition mode="out-in" name="jobs-tab-fade">
                      <pre
                        v-if="dataTab === 'result' && hasJson(selectedJob.result)"
                        key="result-json"
                        class="jobs-code-view"
                      >{{ formatJson(selectedJob.result) }}</pre>
                      <pre
                        v-else-if="dataTab === 'payload' && hasJson(selectedJob.payload)"
                        key="payload-json"
                        class="jobs-code-view"
                      >{{ formatJson(selectedJob.payload) }}</pre>
                      <div v-else key="empty" class="jobs-code-empty">
                        <span class="jobs-code-empty-icon">{ }</span>
                        <p>{{ dataTab === "result" ? "Result пуст" : "Payload пуст" }}</p>
                      </div>
                    </Transition>
                  </div>
                </div>
              </div>

              <footer
                v-if="selectedJob.status === 'failed' || selectedJob.status === 'pending'"
                class="jobs-detail-footer"
              >
                <button
                  v-if="selectedJob.status === 'failed'"
                  class="btn-primary px-4 py-2 text-sm disabled:opacity-60"
                  type="button"
                  :disabled="acting"
                  @click="retrySelected"
                >
                  <ArrowPathIcon class="icon-sm" />
                  Повторить
                </button>
                <button
                  v-if="selectedJob.status === 'pending'"
                  class="btn-ghost px-4 py-2 text-sm disabled:opacity-60"
                  type="button"
                  :disabled="acting"
                  @click="cancelSelected"
                >
                  Отменить
                </button>
              </footer>
              </div>
            </Transition>
          </section>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>
