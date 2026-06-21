<script setup lang="ts">
import { computed } from "vue";
import { ChevronLeftIcon, ChevronRightIcon } from "@heroicons/vue/24/outline";

import { getCurrentWeekKey, weekLabel } from "@/lib/week";
import { useBoardStore } from "@/features/board/stores/board";

const board = useBoardStore();

const label = computed(() => weekLabel(board.weekKey));
const isCurrentWeek = computed(() => board.weekKey === getCurrentWeekKey());
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
