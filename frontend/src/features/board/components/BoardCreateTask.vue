<script setup lang="ts">
import { PlusIcon } from "@heroicons/vue/24/outline";

import { useBoardStore } from "@/features/board/stores/board";

const board = useBoardStore();
</script>

<template>
  <button class="btn-primary px-3 py-2 text-sm" type="button" @click="board.openCreateTask()">
    <PlusIcon class="icon-sm" />
    Задача
  </button>
</template>
