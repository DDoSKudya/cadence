<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { useBoardStore } from "@/features/board/stores/board";

const board = useBoardStore();
const now = ref(new Date());
let clockTimer: number | undefined;

const reviewLink = computed(() =>
  board.weekId ? { name: "week-review", params: { id: board.weekId } } : null,
);
const showReviewLink = computed(() => {
  const day = now.value.getDay();
  const hour = now.value.getHours();

  return (day === 5 && hour >= 12) || day === 6 || day === 0;
});

onMounted(() => {
  clockTimer = window.setInterval(() => {
    now.value = new Date();
  }, 60000);
});

onUnmounted(() => {
  window.clearInterval(clockTimer);
});
</script>

<template>
  <div v-if="showReviewLink && reviewLink" class="week-nav">
    <RouterLink class="week-nav-review" :to="reviewLink">
      {{ $t("board.review") }}
    </RouterLink>
  </div>
</template>
