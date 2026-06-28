<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  ArchiveBoxIcon,
  CalendarDaysIcon,
  CheckBadgeIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  TagIcon,
} from "@heroicons/vue/24/outline";

import {
  actorLabel,
  columnStatusLabel,
  eventTone,
  eventTypeLabel,
  sourceLabel,
  systemTypeDotStyle,
} from "@/features/archive/labels";
import {
  fetchArchiveTask,
  fetchArchiveTasks,
} from "@/features/archive/api";
import type { ArchiveFilters, ArchiveTaskDetail, ArchiveTaskSummary } from "@/features/archive/types";
import { fetchTags } from "@/features/board/api";
import type { Tag } from "@/features/board/types";
import { priorityLabel } from "@/features/board/labels";
import { formatDateTime, formatDateTimeLong } from "@/lib/datetime";
import { formatWeekKey } from "@/lib/week";

const PAGE_SIZE = 20;
const POLL_INTERVAL_MS = 5000;
const { t } = useI18n();

let pollTimer: ReturnType<typeof setInterval> | null = null;
const listKey = ref(0);

const tasks = ref<ArchiveTaskSummary[]>([]);
const totalCount = ref(0);
const page = ref(1);
const selectedId = ref<number | null>(null);
const selectedTask = ref<ArchiveTaskDetail | null>(null);
const tags = ref<Tag[]>([]);
const loading = ref(true);
const pageLoading = ref(false);
const detailLoading = ref(false);
const filtersOpen = ref(false);
const error = ref("");

const filters = ref<ArchiveFilters>({
  search: "",
  week: "",
  tag: "",
  source: "",
  closed_from: "",
  closed_to: "",
});

const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / PAGE_SIZE)));

const filtersActive = computed(
  () =>
    Boolean(filters.value.search?.trim()) ||
    Boolean(filters.value.week?.trim()) ||
    Boolean(filters.value.tag) ||
    Boolean(filters.value.source) ||
    Boolean(filters.value.closed_from) ||
    Boolean(filters.value.closed_to),
);

const headerMeta = computed(() => {
  if (loading.value) {
    return t("archive.loadingMeta");
  }
  const parts: string[] = [];
  if (totalCount.value === 0) {
    parts.push(t("archive.noClosedTasks"));
  } else {
    parts.push(t("archive.meta", totalCount.value));
  }
  parts.push(t("archive.autoRefresh"));
  return parts.join(" · ");
});

const sourceOptions = [
  { value: "", label: "common.all" },
  { value: "ui", label: "UI" },
  { value: "api", label: "API" },
  { value: "json_import", label: "JSON import" },
  { value: "telegram", label: "Telegram" },
];

async function loadList(options: { initial?: boolean; pageChange?: boolean } = {}) {
  if (options.initial) {
    loading.value = true;
  } else if (options.pageChange) {
    pageLoading.value = true;
  }
  error.value = "";
  try {
    const data = await fetchArchiveTasks({
      ...filters.value,
      page: page.value,
      page_size: PAGE_SIZE,
    });
    tasks.value = data.results;
    totalCount.value = data.count;
    if (selectedId.value && !data.results.some((item) => item.id === selectedId.value)) {
      selectedId.value = data.results[0]?.id ?? null;
    }
    if (!selectedId.value && data.results.length > 0) {
      selectedId.value = data.results[0]!.id;
    }
    if (options.initial || options.pageChange) {
      listKey.value += 1;
    }
  } catch (loadError) {
    if (options.initial || options.pageChange) {
      error.value =
        loadError instanceof Error ? loadError.message : t("archive.loadFailed");
      tasks.value = [];
      totalCount.value = 0;
      selectedId.value = null;
      selectedTask.value = null;
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

async function loadDetail(taskId: number, options: { initial?: boolean } = {}) {
  if (options.initial) {
    detailLoading.value = true;
    error.value = "";
  }
  try {
    selectedTask.value = await fetchArchiveTask(taskId);
  } catch (loadError) {
    if (options.initial) {
      selectedTask.value = null;
      error.value =
        loadError instanceof Error ? loadError.message : t("board.loadFailed");
    }
  } finally {
    if (options.initial) {
      detailLoading.value = false;
    }
  }
}

async function refreshArchive(options: { initial?: boolean; pageChange?: boolean } = {}) {
  const previousId = selectedId.value;
  await loadList(options);
  if (!selectedId.value) {
    selectedTask.value = null;
    return;
  }
  if (selectedId.value === previousId) {
    await loadDetail(selectedId.value, { initial: options.initial });
  }
}

function selectTask(taskId: number) {
  selectedId.value = taskId;
}

async function applyFilters() {
  page.value = 1;
  await refreshArchive({ initial: true });
}

function clearFilters() {
  filters.value = {
    search: "",
    week: "",
    tag: "",
    source: "",
    closed_from: "",
    closed_to: "",
  };
  void applyFilters();
}

async function changePage(nextPage: number) {
  if (nextPage < 1 || nextPage > totalPages.value) {
    return;
  }
  page.value = nextPage;
  await refreshArchive({ pageChange: true });
}

watch(selectedId, (taskId) => {
  if (taskId) {
    void loadDetail(taskId, { initial: !selectedTask.value });
    return;
  }
  selectedTask.value = null;
});

onMounted(async () => {
  try {
    tags.value = await fetchTags();
  } catch {
    tags.value = [];
  }
  await refreshArchive({ initial: true });
  pollTimer = setInterval(() => {
    if (document.visibilityState === "visible") {
      void refreshArchive();
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
  <div class="archive-page">
    <div class="archive-shell">
      <header class="archive-toolbar">
        <div class="archive-toolbar-brand">
          <span class="archive-toolbar-icon" aria-hidden="true">
            <ArchiveBoxIcon />
          </span>
          <div>
            <h1 class="archive-toolbar-title">{{ $t("archive.title") }}</h1>
            <p class="archive-toolbar-meta">{{ headerMeta }}</p>
          </div>
        </div>
      </header>

      <Transition name="archive-alert-slide">
        <p v-if="error" key="error" class="alert-error archive-alert">{{ error }}</p>
      </Transition>

      <div class="archive-body">
        <Transition mode="out-in" name="archive-body-swap">
          <div v-if="loading" key="loading" class="archive-detail-state">
            <span class="loading-spinner" />
            <p>{{ $t("archive.loadingArchive") }}</p>
          </div>

          <div v-else key="content" class="archive-layout">
            <aside class="archive-panel archive-panel-list">
              <div class="archive-list-head">
                <label class="archive-search">
                  <MagnifyingGlassIcon class="archive-search-icon" />
                  <input
                    v-model="filters.search"
                    class="archive-search-input"
                    type="search"
                    :placeholder="$t('archive.searchByTitle')"
                    @keydown.enter.prevent="applyFilters"
                  />
                </label>
                <button
                  class="archive-filter-toggle"
                  :class="{ 'archive-filter-toggle-active': filtersOpen || filtersActive }"
                  type="button"
                  :title="$t('common.filters')"
                  @click="filtersOpen = !filtersOpen"
                >
                  <FunnelIcon class="icon-sm" />
                  <span v-if="filtersActive" class="archive-filter-dot" />
                </button>
              </div>

              <Transition name="archive-filters-slide">
                <form
                  v-if="filtersOpen"
                  class="archive-filters"
                  @submit.prevent="applyFilters"
                >
                  <label class="archive-filter-field">
                    <span>{{ $t("common.week") }}</span>
                    <input v-model="filters.week" class="field px-3 py-2" type="text" :placeholder="$t('analytics.weekPlaceholder')" />
                  </label>
                  <label class="archive-filter-field">
                    <span>{{ $t("common.tag") }}</span>
                    <select v-model="filters.tag" class="field px-3 py-2">
                      <option value="">{{ $t("common.all") }}</option>
                      <option v-for="tag in tags" :key="tag.id" :value="tag.slug">{{ tag.name }}</option>
                    </select>
                  </label>
                  <label class="archive-filter-field">
                    <span>{{ $t("common.source") }}</span>
                    <select v-model="filters.source" class="field px-3 py-2">
                      <option
                        v-for="option in sourceOptions"
                        :key="option.value || 'all'"
                        :value="option.value"
                      >
                        {{ option.value ? option.label : $t(option.label) }}
                      </option>
                    </select>
                  </label>
                  <div class="archive-filter-dates">
                    <label class="archive-filter-field">
                      <span>{{ $t("archive.closedFrom") }}</span>
                      <input v-model="filters.closed_from" class="field px-3 py-2" type="date" />
                    </label>
                    <label class="archive-filter-field">
                      <span>{{ $t("archive.closedTo") }}</span>
                      <input v-model="filters.closed_to" class="field px-3 py-2" type="date" />
                    </label>
                  </div>
                  <div class="archive-filter-actions">
                    <button class="archive-btn archive-btn-ghost" type="button" @click="clearFilters">
                      {{ $t("common.reset") }}
                    </button>
                    <button class="archive-btn archive-btn-primary" type="submit">{{ $t("common.apply") }}</button>
                  </div>
                </form>
              </Transition>

              <div class="archive-list-wrap" :class="{ 'archive-list-wrap-loading': pageLoading }">
                <Transition mode="out-in" name="archive-page-swap">
                  <ul v-if="tasks.length" :key="listKey" class="archive-task-list">
                    <li
                      v-for="(item, index) in tasks"
                      :key="item.id"
                      class="archive-task-item"
                      :style="{ '--archive-item-delay': `${index * 30}ms` }"
                    >
                      <button
                        class="archive-task-card"
                        :class="{ 'archive-task-card-active': item.id === selectedId }"
                        type="button"
                        @click="selectTask(item.id)"
                      >
                        <span
                          class="archive-task-dot"
                          :style="systemTypeDotStyle(item.column_system_type)"
                        />
                        <span class="archive-task-card-body">
                          <span class="archive-task-card-title">{{ item.title }}</span>
                          <span class="archive-task-card-meta">
                            <CalendarDaysIcon class="archive-inline-icon" />
                            {{ formatDateTime(item.closed_at) }}
                            <span v-if="item.week" class="archive-week-pill">
                              {{ formatWeekKey({ isoYear: item.week.iso_year, isoWeek: item.week.iso_week }) }}
                            </span>
                          </span>
                        </span>
                        <CheckBadgeIcon class="archive-task-check" />
                      </button>
                    </li>
                  </ul>

                  <div v-else key="empty" class="archive-empty">
                    <ArchiveBoxIcon class="archive-empty-icon" />
                    <p>{{ filtersActive ? $t("archive.emptyFiltered") : $t("archive.empty") }}</p>
                  </div>
                </Transition>

                <div v-if="pageLoading" class="archive-list-overlay" aria-hidden="true">
                  <span class="loading-spinner" />
                </div>
              </div>

              <div v-if="totalPages > 1" class="archive-pagination">
                <button
                  class="archive-page-btn"
                  type="button"
                  :disabled="page <= 1 || pageLoading"
                  @click="changePage(page - 1)"
                >
                  <ChevronLeftIcon class="icon-sm" />
                </button>
                <span>{{ page }} / {{ totalPages }}</span>
                <button
                  class="archive-page-btn"
                  type="button"
                  :disabled="page >= totalPages || pageLoading"
                  @click="changePage(page + 1)"
                >
                  <ChevronRightIcon class="icon-sm" />
                </button>
              </div>
            </aside>

            <section class="archive-panel archive-panel-detail">
              <Transition mode="out-in" name="archive-detail-swap">
                <div v-if="detailLoading" key="loading" class="archive-detail-state">
                  <span class="loading-spinner" />
                  <p>{{ $t("archive.loadingTask") }}</p>
                </div>

                <div v-else-if="selectedTask" :key="selectedTask.id" class="archive-detail-panel">
                  <div class="archive-hero">
                    <div class="archive-hero-main">
                      <p class="archive-hero-eyebrow">
                        <CheckBadgeIcon class="archive-inline-icon" />
                        {{ $t("archive.closedAt", { value: formatDateTimeLong(selectedTask.closed_at) }) }}
                      </p>
                      <h2 class="archive-hero-title">{{ selectedTask.title }}</h2>
                      <div class="archive-chip-row">
                        <span class="archive-chip archive-chip-status">
                          {{ columnStatusLabel(selectedTask.column_system_type, selectedTask.column_name) }}
                        </span>
                        <span class="archive-chip">{{ priorityLabel(selectedTask.priority) }}</span>
                        <span class="archive-chip">{{ sourceLabel(selectedTask.source) }}</span>
                        <span v-if="selectedTask.week" class="archive-chip archive-chip-week">
                          {{ formatWeekKey({ isoYear: selectedTask.week.iso_year, isoWeek: selectedTask.week.iso_week }) }}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div class="archive-detail-scroll">
                    <TransitionGroup name="archive-block" tag="div" class="archive-detail-blocks">
                      <div
                        v-if="selectedTask.description?.trim()"
                        key="description"
                        class="archive-info-card archive-detail-block"
                      >
                        <p class="archive-info-label">{{ $t("common.description") }}</p>
                        <p class="archive-info-text">{{ selectedTask.description }}</p>
                      </div>

                      <div
                        v-if="selectedTask.completion_note"
                        key="summary"
                        class="archive-info-grid archive-detail-block"
                      >
                        <div class="archive-info-card">
                          <p class="archive-info-label">{{ $t("archive.outcome") }}</p>
                          <p class="archive-info-text">{{ selectedTask.completion_note }}</p>
                        </div>
                      </div>

                      <div
                        v-if="selectedTask.tags.length"
                        key="tags"
                        class="archive-info-card archive-detail-block"
                      >
                        <p class="archive-info-label">
                          <TagIcon class="archive-inline-icon" />
                          {{ $t("common.tags") }}
                        </p>
                        <div class="archive-tag-row">
                          <span
                            v-for="tag in selectedTask.tags"
                            :key="tag.id"
                            class="archive-tag"
                            :style="{ '--tag-color': tag.color || '#64748b' }"
                          >
                            {{ tag.name }}
                          </span>
                        </div>
                      </div>

                      <div key="history" class="archive-history-card archive-detail-block">
                        <div class="archive-history-head">
                          <p class="archive-info-label">{{ $t("archive.events") }}</p>
                          <span class="archive-history-count">
                            {{ selectedTask.events.length }}
                          </span>
                        </div>

                        <div v-if="selectedTask.events.length" class="archive-history-table-wrap">
                          <table class="archive-history-table">
                            <colgroup>
                              <col class="archive-history-col-event" />
                              <col class="archive-history-col-source" />
                              <col class="archive-history-col-time" />
                            </colgroup>
                            <thead>
                              <tr>
                                <th class="archive-history-th-event">{{ $t("archive.event") }}</th>
                                <th class="archive-history-th-source">{{ $t("common.source") }}</th>
                                <th class="archive-history-th-time">{{ $t("archive.time") }}</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr v-for="event in selectedTask.events" :key="event.id">
                                <td class="archive-history-td-event">
                                  <span
                                    class="archive-event-badge"
                                    :class="`archive-event-badge-${eventTone(event.event_type)}`"
                                  >
                                    {{ eventTypeLabel(event.event_type) }}
                                  </span>
                                </td>
                                <td class="archive-history-td-source">
                                  {{ actorLabel(event.actor_type) }}
                                </td>
                                <td class="archive-history-td-time">
                                  {{ formatDateTime(event.created_at) }}
                                </td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                        <p v-else class="archive-history-empty">{{ $t("archive.noEvents") }}</p>
                      </div>
                    </TransitionGroup>
                  </div>
                </div>

                <div v-else key="placeholder" class="archive-detail-state archive-detail-placeholder">
                  <MagnifyingGlassIcon class="archive-empty-icon" />
                  <p>{{ $t("archive.selectTask") }}</p>
                  <span class="archive-detail-placeholder-hint">{{ $t("archive.selectTaskHint") }}</span>
                </div>
              </Transition>
            </section>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>
