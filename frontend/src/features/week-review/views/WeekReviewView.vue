<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
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
import { pluralRu } from "@/lib/plural";

const route = useRoute();
const router = useRouter();

const loading = ref(true);
const saving = ref(false);
const closing = ref(false);
const error = ref("");
const notice = ref("");
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
    pluralRu(stats.tasks_total, "задача", "задачи", "задач"),
    `${stats.tasks_closed} закрыто`,
    `${stats.tasks_open} открыто`,
  ].join(" · ");
});

async function loadReview() {
  if (!Number.isFinite(weekId.value) || weekId.value <= 0) {
    error.value = "Некорректная неделя";
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
      loadError instanceof Error ? loadError.message : "Не удалось загрузить обзор";
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
  notice.value = "";
  try {
    const updatedWeek = await saveWeekReviewNotes(weekId.value, notes.value);
    savedNotes.value = notes.value;
    review.value = {
      ...review.value,
      week: { ...review.value.week, ...updatedWeek },
    };
    notice.value = "Сохранено";
  } catch (saveError) {
    error.value =
      saveError instanceof Error ? saveError.message : "Не удалось сохранить";
  } finally {
    saving.value = false;
  }
}

async function closeWeekAction() {
  if (!review.value || isClosed.value) {
    return;
  }

  const openCount = review.value.stats.tasks_open;
  const confirmed = window.confirm(
    openCount > 0
      ? `Закрыть неделю и перенести ${openCount} незакрытых задач на следующую?`
      : "Закрыть неделю?",
  );
  if (!confirmed) {
    return;
  }

  closing.value = true;
  error.value = "";
  notice.value = "";
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
    notice.value =
      result.result.carried_over > 0
        ? `Неделя закрыта, перенесено ${result.result.carried_over}`
        : "Неделя закрыта";
  } catch (closeError) {
    error.value =
      closeError instanceof Error ? closeError.message : "Не удалось закрыть неделю";
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

watch(notice, (value) => {
  if (value) {
    window.setTimeout(() => {
      notice.value = "";
    }, 2500);
  }
});

onMounted(loadReview);
</script>

<template>
  <div class="settings-page">
    <div class="board-shell settings-board-shell">
      <header class="board-toolbar shrink-0">
        <div class="board-toolbar-info">
          <h1 class="page-title">Обзор недели</h1>
          <p class="page-meta">{{ headerMeta }}</p>
        </div>

        <div class="board-toolbar-actions">
          <button class="btn-ghost px-4 py-2 text-sm" type="button" @click="router.push('/board')">
            На доску
          </button>
          <button
            v-if="isDirty"
            class="btn-primary px-4 py-2 text-sm disabled:opacity-60"
            type="button"
            :disabled="saving"
            @click="saveNotes"
          >
            {{ saving ? "Сохранение…" : "Сохранить" }}
          </button>
        </div>
      </header>

      <p v-if="error" class="alert-error mx-4 mt-3 shrink-0">{{ error }}</p>
      <p v-else-if="notice" class="alert-notice mx-4 mt-3 shrink-0">{{ notice }}</p>

      <div v-if="loading" class="settings-body settings-body-center">
        <div class="loading-state">
          <span class="loading-spinner" aria-hidden="true" />
          <p class="text-sm text-[var(--color-text-secondary)]">Загрузка…</p>
        </div>
      </div>

      <div v-else-if="review" class="settings-body review-body">
        <div class="review-stats">
          <div class="review-stat-card">
            <CalendarDaysIcon />
            <div>
              <p class="review-stat-label">Неделя</p>
              <p class="review-stat-value">{{ statsLine }}</p>
            </div>
          </div>
          <div class="review-stat-card">
            <CheckCircleIcon />
            <div>
              <p class="review-stat-label">Статус</p>
              <p class="review-stat-value">
                {{ isClosed ? "Закрыта" : "Открыта" }}
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
                <p class="drawer-eyebrow">Заметки</p>
                <h2 class="settings-panel-title">Итоги недели</h2>
              </div>
            </div>
          </header>
          <div class="settings-panel-body">
            <textarea
              v-model="notes"
              class="field px-3 py-2 review-notes"
              rows="8"
              placeholder="Что получилось, что осталось, выводы…"
            />
          </div>
        </section>

        <section class="settings-panel review-panel">
          <header class="settings-panel-header">
            <h2 class="settings-panel-title">Незакрытые задачи</h2>
          </header>
          <div class="settings-panel-body">
            <ul v-if="review.open_tasks.length" class="review-open-list">
              <li v-for="task in review.open_tasks" :key="task.id" class="review-open-item">
                <span class="review-open-title">{{ task.title }}</span>
                <span class="review-open-meta">{{ task.column_name }}</span>
              </li>
            </ul>
            <p v-else class="notify-field-hint">Все задачи недели закрыты</p>
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
            Обновить
          </button>
          <button
            class="btn btn-primary"
            type="button"
            :disabled="closing || isClosed"
            @click="closeWeekAction"
          >
            {{ closing ? "Закрытие…" : isClosed ? "Неделя закрыта" : "Закрыть неделю" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
