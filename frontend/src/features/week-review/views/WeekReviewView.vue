<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import {
  ArrowPathIcon,
  CalendarDaysIcon,
  CheckCircleIcon,
  ClipboardDocumentIcon,
} from "@heroicons/vue/24/outline";

import {
  closeWeek,
  fetchWeekReview,
  saveWeekReviewNotes,
} from "@/features/week-review/api";
import type { WeekReviewResponse } from "@/features/week-review/types";
import { weekLabel } from "@/lib/week";
import { useToastStore } from "@/stores/toast";
import { useActionFeedback } from "@/composables/useActionFeedback";

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const toast = useToastStore();
const feedback = useActionFeedback();

const loading = ref(true);
const saving = ref(false);
const closing = ref(false);
const error = ref("");
const review = ref<WeekReviewResponse | null>(null);
const notes = ref("");
const savedNotes = ref("");

const weekId = computed(() => Number(route.params.id));

const isDirty = computed(() => notes.value !== savedNotes.value);

const isClosed = computed(() => Boolean(review.value?.week.closed_at));

const headerMeta = computed(() => {
  if (!review.value) {
    return "";
  }
  const week = review.value.week;
  const label = weekLabel(`${week.iso_year}-W${String(week.iso_week).padStart(2, "0")}`);
  const range = `${week.starts_on} — ${week.ends_on}`;
  return `${label} · ${range}`;
});

const statsLine = computed(() => {
  if (!review.value) {
    return "";
  }
  const { stats } = review.value;
  return [
    t("board.taskCount", stats.tasks_total),
    t("weekReview.statsClosed", stats.tasks_closed),
    t("weekReview.statsOpen", stats.tasks_open),
  ].join(" · ");
});

async function loadReview() {
  if (!Number.isFinite(weekId.value) || weekId.value <= 0) {
    error.value = t("weekReview.invalidWeek");
    review.value = null;
    loading.value = false;
    return;
  }

  loading.value = true;
  error.value = "";
  try {
    const data = await fetchWeekReview(weekId.value);
    review.value = data;
    notes.value = data.week.review_notes;
    savedNotes.value = data.week.review_notes;
  } catch (loadError) {
    review.value = null;
    error.value =
      loadError instanceof Error ? loadError.message : t("weekReview.loadFailed");
  } finally {
    loading.value = false;
  }
}

async function saveNotes() {
  if (!review.value || !isDirty.value) {
    return;
  }

  saving.value = true;
  error.value = "";
  try {
    const updatedWeek = await saveWeekReviewNotes(weekId.value, notes.value);
    savedNotes.value = notes.value;
    review.value = {
      ...review.value,
      week: { ...review.value.week, ...updatedWeek },
    };
    toast.success(t("toast.weekSaved"));
  } catch (saveError) {
    feedback.fromError(saveError, "weekReview.saveFailed");
  } finally {
    saving.value = false;
  }
}

async function closeWeekAction() {
  if (!review.value || isClosed.value) {
    return;
  }

  if (isDirty.value) {
    await saveNotes();
    if (error.value) {
      return;
    }
  }

  const openCount = review.value.stats.tasks_open;
  const confirmed = window.confirm(
    openCount > 0
      ? t("weekReview.confirmCloseWithOpen", openCount)
      : t("weekReview.confirmClose"),
  );
  if (!confirmed) {
    return;
  }

  closing.value = true;
  error.value = "";
  try {
    const result = await closeWeek(weekId.value, true);
    review.value = {
      ...review.value,
      week: result.week,
      stats: {
        ...review.value.stats,
        tasks_open: 0,
      },
      open_tasks: [],
    };
    toast.success(
      result.result.carried_over > 0
        ? t("weekReview.weekClosedCarryover", { count: result.result.carried_over })
        : t("weekReview.weekClosed"),
    );
  } catch (closeError) {
    feedback.fromError(closeError, "weekReview.closeFailed");
  } finally {
    closing.value = false;
  }
}

watch(
  () => route.params.id,
  () => {
    void loadReview();
  },
);

onMounted(loadReview);
</script>

<template>
  <div class="settings-page">
    <div class="board-shell settings-board-shell">
      <header class="board-toolbar shrink-0">
        <div class="board-toolbar-info">
          <h1 class="page-title">{{ $t("weekReview.title") }}</h1>
          <p class="page-meta">{{ headerMeta }}</p>
        </div>

        <div class="board-toolbar-actions">
          <button class="btn-ghost px-4 py-2 text-sm" type="button" @click="router.push('/board')">
            {{ $t("weekReview.backToBoard") }}
          </button>
          <button
            v-if="isDirty"
            class="btn-primary px-4 py-2 text-sm disabled:opacity-60"
            type="button"
            :disabled="saving"
            @click="saveNotes"
          >
            {{ saving ? $t("common.saving") : $t("common.save") }}
          </button>
        </div>
      </header>

      <p v-if="error" class="alert-error mx-4 mt-3 shrink-0">{{ error }}</p>

      <div v-if="loading" class="settings-body settings-body-center">
        <div class="loading-state">
          <span class="loading-spinner" aria-hidden="true" />
          <p class="text-sm text-[var(--color-text-secondary)]">{{ $t("common.loading") }}</p>
        </div>
      </div>

      <div v-else-if="review" class="settings-body review-body">
        <div class="review-stats">
          <div class="review-stat-card">
            <CalendarDaysIcon />
            <div>
              <p class="review-stat-label">{{ $t("weekReview.week") }}</p>
              <p class="review-stat-value">{{ statsLine }}</p>
            </div>
          </div>
          <div class="review-stat-card">
            <CheckCircleIcon />
            <div>
              <p class="review-stat-label">{{ $t("weekReview.status") }}</p>
              <p class="review-stat-value">
                {{ isClosed ? $t("weekReview.closed") : $t("weekReview.open") }}
              </p>
            </div>
          </div>
        </div>

        <section class="settings-panel review-panel">
          <header class="settings-panel-header">
            <div class="notify-panel-head">
              <span class="notify-fold-icon notify-fold-icon-rules">
                <ClipboardDocumentIcon />
              </span>
              <div>
                <p class="drawer-eyebrow">{{ $t("weekReview.notes") }}</p>
                <h2 class="settings-panel-title">{{ $t("weekReview.notesTitle") }}</h2>
              </div>
            </div>
          </header>
          <div class="settings-panel-body">
            <textarea
              v-model="notes"
              class="field px-3 py-2 review-notes"
              rows="8"
              :placeholder="$t('weekReview.notesPlaceholder')"
            />
          </div>
        </section>

        <section class="settings-panel review-panel">
          <header class="settings-panel-header">
            <h2 class="settings-panel-title">{{ $t("weekReview.openTasks") }}</h2>
          </header>
          <div class="settings-panel-body">
            <ul v-if="review.open_tasks.length" class="review-open-list">
              <li v-for="task in review.open_tasks" :key="task.id" class="review-open-item">
                <span class="review-open-title">{{ task.title }}</span>
                <span class="review-open-meta">{{ task.column_name }}</span>
              </li>
            </ul>
            <p v-else class="notify-field-hint">{{ $t("weekReview.noOpenTasks") }}</p>
          </div>
        </section>

        <div class="review-actions">
          <button
            class="btn btn-secondary"
            type="button"
            :disabled="closing || isClosed"
            @click="loadReview"
          >
            <ArrowPathIcon class="icon-sm" />
            {{ $t("weekReview.refresh") }}
          </button>
          <button
            class="btn btn-primary"
            type="button"
            :disabled="closing || isClosed"
            @click="closeWeekAction"
          >
            {{ closing ? $t("weekReview.closing") : isClosed ? $t("weekReview.weekClosed") : $t("weekReview.closeWeek") }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
