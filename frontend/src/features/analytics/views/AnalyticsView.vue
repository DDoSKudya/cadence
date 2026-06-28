<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import type { EChartsOption } from "echarts";
import {
  ArrowDownTrayIcon,
  ArrowTrendingUpIcon,
  BellAlertIcon,
  ChartBarIcon,
  CheckBadgeIcon,
  CheckCircleIcon,
  ClockIcon,
  FunnelIcon,
  GlobeAltIcon,
  QueueListIcon,
  TagIcon,
  ViewColumnsIcon,
} from "@heroicons/vue/24/outline";

import {
  breakdownChartOption,
  coverageBarsOption,
  distributionOption,
  notificationsOption,
  staleTasksOption,
  telegramActionsOption,
  weeklyColumnOption,
  weeklyTrendOption,
} from "@/features/analytics/chart-options";
import AnalyticsChart from "@/features/analytics/components/AnalyticsChart.vue";
import {
  fetchAnalyticsSummary,
  fetchArchiveAnalytics,
  fetchBreakdown,
  fetchCycleTime,
  fetchNotificationMetrics,
  fetchTaskFlow,
  fetchWeeklyTrend,
} from "@/features/analytics/api";
import AnalyticsFiltersPanel from "@/features/analytics/components/AnalyticsFiltersPanel.vue";
import ExportDialog from "@/features/analytics/components/ExportDialog.vue";
import {
  columnBreakdownLabel,
  sourceLabel,
  telegramActionLabel,
} from "@/features/analytics/labels";
import { CHART_COLORS } from "@/features/analytics/register-echarts";
import type {
  AnalyticsFilters,
  AnalyticsSummary,
  ArchiveAnalytics,
  BreakdownItem,
  CycleTimeData,
  ExportSnapshot,
  NotificationMetrics,
  TaskFlowData,
  WeeklyTrendItem,
} from "@/features/analytics/types";
import { fetchTags } from "@/features/board/api";
import type { Tag } from "@/features/board/types";
import { weekLabel } from "@/lib/week";

const WEEKS_COUNT = 8;
const POLL_INTERVAL_MS = 5000;
const { t } = useI18n();

let pollTimer: ReturnType<typeof setInterval> | null = null;

const loading = ref(true);
const error = ref("");
const exportOpen = ref(false);
const filtersOpen = ref(false);
const activeTab = ref<"overview" | "flow" | "archive" | "notify">("overview");

const draftFilters = ref<AnalyticsFilters>({
  week: "",
  from: "",
  to: "",
  tag: "",
  source: "",
});

const appliedFilters = ref<AnalyticsFilters>({ ...draftFilters.value });

const tags = ref<Tag[]>([]);
const summary = ref<AnalyticsSummary | null>(null);
const weeklyTrend = ref<WeeklyTrendItem[]>([]);
const columnBreakdown = ref<BreakdownItem[]>([]);
const tagBreakdown = ref<BreakdownItem[]>([]);
const sourceBreakdown = ref<BreakdownItem[]>([]);
const cycleTime = ref<CycleTimeData | null>(null);
const notifications = ref<NotificationMetrics | null>(null);
const taskFlow = ref<TaskFlowData | null>(null);
const archiveStats = ref<ArchiveAnalytics | null>(null);

const exportSnapshot = computed<ExportSnapshot>(() => ({
  schemeName: summary.value?.scheme?.name,
  summary: summary.value,
  weeklyTrend: trendItems.value,
  columnBreakdown: columnBreakdown.value,
  tagBreakdown: tagBreakdown.value,
  notifications: notifications.value,
  archiveStats: archiveStats.value,
}));

const filtersActive = computed(
  () =>
    Boolean(appliedFilters.value.week?.trim()) ||
    Boolean(appliedFilters.value.from) ||
    Boolean(appliedFilters.value.to) ||
    Boolean(appliedFilters.value.tag) ||
    Boolean(appliedFilters.value.source),
);

const headerMeta = computed(() => {
  if (loading.value) {
    return t("analytics.loadingMeta");
  }
  if (!summary.value) {
    return t("analytics.noDataMeta");
  }
  const parts = [
    t("analytics.activeTasks", summary.value.active_tasks),
    t("analytics.createdMeta", { count: summary.value.tasks_created }),
    t("analytics.closedMeta", { count: summary.value.tasks_closed }),
  ];
  if (summary.value.scheme?.name) {
    parts.push(summary.value.scheme.name);
  }
  if (filtersActive.value) {
    parts.push(t("analytics.filtersApplied"));
  }
  parts.push(t("analytics.autoRefresh"));
  return parts.join(" · ");
});

const trendItems = computed(() => {
  const items = weeklyTrend.value;
  const withData = items.filter(
    (item) => item.created > 0 || item.closed > 0 || item.carried_over > 0,
  );
  if (withData.length > 0) {
    return withData.slice(-WEEKS_COUNT);
  }
  return items.slice(-WEEKS_COUNT);
});

const summaryCards = computed(() => {
  if (!summary.value) {
    return [];
  }
  const data = summary.value;
  return [
    {
      key: "created",
      label: t("analytics.created"),
      value: data.tasks_created,
      tone: "primary",
    },
    {
      key: "closed",
      label: t("analytics.closed"),
      value: data.tasks_closed,
      tone: "accent",
    },
    {
      key: "active",
      label: t("analytics.active"),
      value: data.active_tasks,
      tone: "slate",
    },
    {
      key: "overdue",
      label: t("analytics.overdue"),
      value: data.overdue_tasks,
      tone: "warn",
    },
    {
      key: "stale",
      label: t("analytics.stale"),
      value: data.stale_tasks,
      tone: "warn",
    },
    {
      key: "evidence",
      label: t("analytics.withProof"),
      value: percent(data.evidence_rate),
      tone: "success",
    },
  ];
});

const tabs = [
  { id: "overview" as const, label: "analytics.overview", icon: ChartBarIcon },
  { id: "flow" as const, label: "analytics.flow", icon: ArrowTrendingUpIcon },
  { id: "archive" as const, label: "analytics.archive", icon: CheckCircleIcon },
  { id: "notify" as const, label: "analytics.notifications", icon: BellAlertIcon },
];

const trendChartOption = computed<EChartsOption>(() =>
  weeklyTrendOption(trendItems.value, weekDisplay),
);

const columnChartOption = computed<EChartsOption>(() =>
  breakdownChartOption(
    columnBreakdown.value.map((item) => ({
      ...item,
      key: columnBreakdownLabel(item),
    })),
    CHART_COLORS.indigo,
  ),
);

const tagChartOption = computed<EChartsOption>(() =>
  breakdownChartOption(tagBreakdown.value, CHART_COLORS.violet),
);

const sourceChartOption = computed<EChartsOption>(() =>
  breakdownChartOption(
    sourceBreakdown.value.map((item) => ({
      ...item,
      key: sourceLabel(item.key),
    })),
    CHART_COLORS.slate,
  ),
);

const staleChartOption = computed<EChartsOption>(() =>
  staleTasksOption(summary.value?.stale_items ?? []),
);

const cycleChartOption = computed<EChartsOption>(() =>
  distributionOption(cycleTime.value?.distribution ?? []),
);

const notifyChartOption = computed<EChartsOption>(() => {
  if (!notifications.value) {
    return {};
  }
  return notificationsOption(notifications.value);
});

const telegramChartOption = computed<EChartsOption>(() => {
  if (!notifications.value) {
    return {};
  }
  return telegramActionsOption(notifications.value.telegram_actions ?? []);
});

const telegramActionCards = computed(() => notifications.value?.telegram_actions ?? []);

const archiveWeekChartOption = computed<EChartsOption>(() => {
  const items = archiveStats.value?.closed_by_week ?? [];
  return weeklyColumnOption(
    items.map((item) => ({ key: weekDisplay(item.week), count: item.count })),
    CHART_COLORS.slate,
  );
});

const archiveTagChartOption = computed<EChartsOption>(() => {
  const items = archiveStats.value?.closed_by_tag ?? [];
  return breakdownChartOption(
    items.map((item) => ({ key: item.tag, count: item.count })),
    CHART_COLORS.primary,
  );
});

const archiveCoverageChartOption = computed<EChartsOption>(() => {
  if (!archiveStats.value) {
    return {};
  }
  return coverageBarsOption(
    archiveStats.value.evidence_coverage,
    archiveStats.value.completion_notes_coverage,
  );
});

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function weekDisplay(value: string): string {
  if (!value || value === "—") {
    return value || "—";
  }
  try {
    return weekLabel(value);
  } catch {
    return value;
  }
}

function resetDraftFilters() {
  draftFilters.value = {
    week: "",
    from: "",
    to: "",
    tag: "",
    source: "",
  };
}

async function applyFilters() {
  appliedFilters.value = { ...draftFilters.value };
  filtersOpen.value = false;
  await loadDashboard({ initial: true });
}

async function clearFilters() {
  resetDraftFilters();
  appliedFilters.value = { ...draftFilters.value };
  filtersOpen.value = false;
  await loadDashboard({ initial: true });
}

async function loadDashboard(options: { initial?: boolean } = {}) {
  if (options.initial) {
    loading.value = true;
  }
  if (!options.initial) {
    error.value = "";
  }
  try {
    const filters = { ...appliedFilters.value };
    const [
      summaryData,
      trendData,
      columnsData,
      tagsData,
      sourcesData,
      cycleData,
      notificationData,
      flowData,
      archiveData,
      tagList,
    ] = await Promise.all([
      fetchAnalyticsSummary(filters),
      fetchWeeklyTrend(filters, WEEKS_COUNT),
      fetchBreakdown(filters, "column"),
      fetchBreakdown(filters, "tag"),
      fetchBreakdown(filters, "source"),
      fetchCycleTime(filters),
      fetchNotificationMetrics(filters),
      fetchTaskFlow(filters),
      fetchArchiveAnalytics(filters),
      fetchTags(),
    ]);
    summary.value = summaryData;
    weeklyTrend.value = trendData.items;
    columnBreakdown.value = columnsData.items;
    tagBreakdown.value = tagsData.items;
    sourceBreakdown.value = sourcesData.items;
    cycleTime.value = cycleData;
    notifications.value = notificationData;
    taskFlow.value = flowData;
    archiveStats.value = archiveData;
    tags.value = tagList;
  } catch (err) {
    if (options.initial) {
      error.value = err instanceof Error ? err.message : t("errors.loadSummary");
    }
  } finally {
    if (options.initial) {
      loading.value = false;
    }
  }
}

function toggleFilters() {
  if (filtersOpen.value) {
    filtersOpen.value = false;
    return;
  }
  exportOpen.value = false;
  draftFilters.value = { ...appliedFilters.value };
  filtersOpen.value = true;
}

function toggleExport() {
  if (exportOpen.value) {
    exportOpen.value = false;
    return;
  }
  filtersOpen.value = false;
  exportOpen.value = true;
}

onMounted(async () => {
  await loadDashboard({ initial: true });
  pollTimer = setInterval(() => {
    if (!filtersOpen.value && !exportOpen.value) {
      void loadDashboard();
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
  <div class="archive-page analytics-page">
    <div class="analytics-shell">
      <header class="board-toolbar shrink-0">
        <div class="board-toolbar-info">
          <h1 class="page-title">{{ $t("analytics.title") }}</h1>
          <p class="page-meta">{{ headerMeta }}</p>
        </div>
        <div class="board-toolbar-actions analytics-toolbar-actions">
          <button
            class="icon-btn"
            type="button"
            :class="{ 'icon-btn-active': filtersOpen }"
            :aria-pressed="filtersOpen"
            :title="$t('analytics.filters')"
            @click="toggleFilters"
          >
            <FunnelIcon class="icon-md" />
            <span v-if="filtersActive" class="analytics-filter-badge" aria-hidden="true" />
          </button>
          <button class="btn-primary" type="button" @click="toggleExport">
            <ArrowDownTrayIcon class="icon-sm" />
            {{ $t("analytics.export") }}
          </button>
        </div>
      </header>

      <p v-if="error" class="alert-error mx-4 mt-3 shrink-0">{{ error }}</p>

      <nav class="analytics-tabs" :aria-label="$t('analytics.title')">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="analytics-tab"
          :class="{ 'analytics-tab-active': activeTab === tab.id }"
          type="button"
          @click="activeTab = tab.id"
        >
          <component :is="tab.icon" class="icon-sm" />
          {{ $t(tab.label) }}
        </button>
      </nav>

      <div class="analytics-body">
        <div v-if="loading" class="analytics-state">
          <span class="loading-spinner" aria-hidden="true" />
          <p>{{ $t("analytics.loading") }}</p>
        </div>

        <template v-else-if="summary">
          <section v-if="activeTab === 'overview'" key="overview" class="analytics-section">
            <div class="analytics-metric-grid">
              <article
                v-for="card in summaryCards"
                :key="card.key"
                class="analytics-metric-card"
                :class="`analytics-metric-${card.tone}`"
              >
                <strong class="analytics-metric-value">{{ card.value }}</strong>
                <span class="analytics-metric-label">{{ card.label }}</span>
              </article>
            </div>

            <article class="analytics-panel analytics-panel-wide">
              <header class="analytics-panel-head">
                <ArrowTrendingUpIcon class="icon-sm" />
                <h2>{{ $t("analytics.weeklyTrend") }}</h2>
              </header>
              <AnalyticsChart
                v-if="trendItems.length > 0"
                :option="trendChartOption"
                size="lg"
              />
              <div v-else class="analytics-empty">{{ $t("analytics.noPeriodData") }}</div>
            </article>

            <div class="analytics-panels analytics-panels-triple">
              <article class="analytics-panel">
                <header class="analytics-panel-head">
                  <ViewColumnsIcon class="icon-sm" />
                  <h2>{{ $t("analytics.byColumns") }}</h2>
                </header>
                <AnalyticsChart
                  v-if="columnBreakdown.length > 0"
                  :option="columnChartOption"
                  size="donut"
                />
                <div v-else class="analytics-empty">{{ $t("analytics.noData") }}</div>
              </article>

              <article class="analytics-panel">
                <header class="analytics-panel-head">
                  <TagIcon class="icon-sm" />
                  <h2>{{ $t("analytics.byTags") }}</h2>
                </header>
                <AnalyticsChart
                  v-if="tagBreakdown.length > 0"
                  :option="tagChartOption"
                  size="donut"
                />
                <div v-else class="analytics-empty">{{ $t("analytics.noData") }}</div>
              </article>

              <article class="analytics-panel">
                <header class="analytics-panel-head">
                  <GlobeAltIcon class="icon-sm" />
                  <h2>{{ $t("analytics.bySources") }}</h2>
                </header>
                <AnalyticsChart
                  v-if="sourceBreakdown.length > 0"
                  :option="sourceChartOption"
                  size="donut"
                />
                <div v-else class="analytics-empty">{{ $t("analytics.noData") }}</div>
              </article>
            </div>

            <div class="analytics-panels">
              <article class="analytics-panel">
                <header class="analytics-panel-head">
                  <ClockIcon class="icon-sm" />
                  <h2>{{ $t("analytics.closingTime") }}</h2>
                </header>
                <p v-if="cycleTime" class="analytics-cycle-summary">
                  {{ $t("analytics.average") }} <strong>{{ cycleTime.avg_hours }} h</strong>
                  <span>· {{ $t("analytics.closedTasks", cycleTime.count) }}</span>
                </p>
                <AnalyticsChart
                  v-if="cycleTime && cycleTime.count > 0"
                  :option="cycleChartOption"
                  size="sm"
                />
                <div v-else class="analytics-empty">{{ $t("analytics.noClosedTasks") }}</div>
              </article>

              <article class="analytics-panel">
                <header class="analytics-panel-head">
                  <QueueListIcon class="icon-sm" />
                  <h2>{{ $t("analytics.staleTasks") }}</h2>
                </header>
                <AnalyticsChart
                  v-if="summary.stale_items.length > 0"
                  :option="staleChartOption"
                  size="sm"
                />
                <div v-else class="analytics-empty">
                  {{ $t("analytics.noStaleTasks") }}
                </div>
              </article>
            </div>
          </section>

          <section v-else-if="activeTab === 'flow'" key="flow" class="analytics-section">
            <div v-if="taskFlow" class="analytics-flow-stats">
              <article class="analytics-stat-pill">
                <span class="analytics-stat-value">{{ taskFlow.reopened_count }}</span>
                <span class="analytics-stat-label">{{ $t("analytics.reopened") }}</span>
              </article>
              <article class="analytics-stat-pill">
                <span class="analytics-stat-value">{{ $t("analytics.hoursShort", { count: taskFlow.avg_open_age_hours }) }}</span>
                <span class="analytics-stat-label">{{ $t("analytics.avgOpenAge") }}</span>
              </article>
              <article class="analytics-stat-pill">
                <span class="analytics-stat-value">{{ taskFlow.carry_over_count }}</span>
                <span class="analytics-stat-label">{{ $t("analytics.carryOverPrevious") }}</span>
              </article>
            </div>

            <article class="analytics-panel analytics-panel-wide">
              <header class="analytics-panel-head">
                <ArrowTrendingUpIcon class="icon-sm" />
                <h2>{{ $t("analytics.weeklyTrend") }}</h2>
              </header>
              <AnalyticsChart
                v-if="trendItems.length > 0"
                :option="trendChartOption"
                size="lg"
              />
              <div v-else class="analytics-empty">{{ $t("analytics.noPeriodData") }}</div>
            </article>
          </section>

          <section v-else-if="activeTab === 'archive'" key="archive" class="analytics-section">
            <div v-if="archiveStats" class="analytics-archive-summary">
              <article class="analytics-stat-pill">
                <span class="analytics-stat-value">{{ archiveStats.closed_total }}</span>
                <span class="analytics-stat-label">{{ $t("analytics.closedInPeriod") }}</span>
              </article>
              <article class="analytics-stat-pill">
                <span class="analytics-stat-value">
                  {{ percent(archiveStats.evidence_coverage) }}
                </span>
                <span class="analytics-stat-label">{{ $t("analytics.withEvidence") }}</span>
              </article>
              <article class="analytics-stat-pill">
                <span class="analytics-stat-value">
                  {{ percent(archiveStats.completion_notes_coverage) }}
                </span>
                <span class="analytics-stat-label">{{ $t("analytics.withNote") }}</span>
              </article>
            </div>

            <div class="analytics-panels">
              <article class="analytics-panel">
                <header class="analytics-panel-head">
                  <CheckBadgeIcon class="icon-sm" />
                  <h2>{{ $t("analytics.archiveCoverage") }}</h2>
                </header>
                <AnalyticsChart
                  v-if="archiveStats"
                  :option="archiveCoverageChartOption"
                  size="sm"
                />
              </article>

              <article class="analytics-panel">
                <h2>{{ $t("analytics.closedByWeek") }}</h2>
                <AnalyticsChart
                  v-if="archiveStats && archiveStats.closed_by_week.length > 0"
                  :option="archiveWeekChartOption"
                  size="md"
                />
                <div v-else class="analytics-empty">{{ $t("analytics.noData") }}</div>
              </article>

              <article class="analytics-panel">
                <h2>{{ $t("analytics.closedByTags") }}</h2>
                <AnalyticsChart
                  v-if="archiveStats && archiveStats.closed_by_tag.length > 0"
                  :option="archiveTagChartOption"
                  size="donut"
                />
                <div v-else class="analytics-empty">{{ $t("analytics.noData") }}</div>
              </article>
            </div>
          </section>

          <section v-else key="notify" class="analytics-section">
            <div v-if="notifications" class="analytics-notify-grid">
              <article class="analytics-notify-card">
                <span class="analytics-notify-value">{{ notifications.notifications_sent }}</span>
                <span class="analytics-notify-label">{{ $t("analytics.sent") }}</span>
              </article>
              <article class="analytics-notify-card analytics-notify-warn">
                <span class="analytics-notify-value">{{ notifications.notification_failures }}</span>
                <span class="analytics-notify-label">{{ $t("analytics.failures") }}</span>
              </article>
              <article
                v-for="action in telegramActionCards"
                :key="action.slug"
                class="analytics-notify-card"
              >
                <span class="analytics-notify-value">{{ action.count }}</span>
                <span class="analytics-notify-label">
                  {{ telegramActionLabel(action.slug) }}
                </span>
              </article>
              <article class="analytics-notify-card analytics-notify-accent">
                <span class="analytics-notify-value">
                  {{ notifications.tasks_closed_after_notification }}
                </span>
                <span class="analytics-notify-label">{{ $t("analytics.closedAfterReminder") }}</span>
              </article>
            </div>

            <div v-if="notifications" class="analytics-panels">
              <article class="analytics-panel">
                <header class="analytics-panel-head">
                  <BellAlertIcon class="icon-sm" />
                  <h2>{{ $t("analytics.reminderEfficiency") }}</h2>
                </header>
                <AnalyticsChart :option="notifyChartOption" size="donut" />
              </article>
              <article class="analytics-panel">
                <header class="analytics-panel-head">
                  <ChartBarIcon class="icon-sm" />
                  <h2>{{ $t("analytics.telegramActions") }}</h2>
                </header>
                <AnalyticsChart
                  v-if="telegramActionCards.length > 0"
                  :option="telegramChartOption"
                  size="donut"
                />
                <div v-else class="analytics-empty">{{ $t("analytics.noTelegramActions") }}</div>
              </article>
            </div>
          </section>
        </template>
      </div>
    </div>

    <AnalyticsFiltersPanel
      v-model:open="filtersOpen"
      v-model:draft-filters="draftFilters"
      :filters-active="filtersActive"
      :tags="tags"
      @apply="applyFilters"
      @clear="clearFilters"
    />
    <ExportDialog
      v-model:open="exportOpen"
      :filters="appliedFilters"
      :snapshot="exportSnapshot"
    />
  </div>
</template>
