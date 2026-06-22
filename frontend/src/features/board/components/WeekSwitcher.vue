<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { ChevronLeftIcon, ChevronRightIcon } from "@heroicons/vue/24/outline";

import { getCurrentWeekKey, weekLabel } from "@/lib/week";
import { useBoardStore } from "@/features/board/stores/board";

const board = useBoardStore();

const label = computed(() => weekLabel(board.weekKey));
const isCurrentWeek = computed(() => board.weekKey === getCurrentWeekKey());
const reviewLink = computed(() =>
  board.weekId ? { name: "week-review", params: { id: board.weekId } } : null,
);
</script>

<template>
  <div class="week-nav">
    <div class="week-switcher" role="group" aria-label="Неделя">
      <button
        class="week-switcher-btn"
        type="button"
        aria-label="Предыдущая неделя"
        @click="board.shiftWeek(-1)"
      >
        <ChevronLeftIcon class="icon-sm" />
      </button>
      <span class="week-label">{{ label }}</span>
      <button
        class="week-switcher-btn"
        type="button"
        aria-label="Следующая неделя"
        @click="board.shiftWeek(1)"
      >
        <ChevronRightIcon class="icon-sm" />
      </button>
    </div>
    <RouterLink v-if="reviewLink" class="week-nav-review" :to="reviewLink">
      Обзор
    </RouterLink>
    <button
      class="week-nav-reset"
      type="button"
      :disabled="isCurrentWeek"
      @click="board.goToCurrentWeek()"
    >
      Сейчас
    </button>
  </div>
</template>
