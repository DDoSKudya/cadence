<script setup lang="ts">
import { PlusIcon } from "@heroicons/vue/24/outline";

import { useBoardStore } from "@/features/board/stores/board";

const board = useBoardStore();
</script>

<template>
  <button class="btn-primary board-action-btn" type="button" @click="board.openCreateTask()">
    <PlusIcon class="icon-sm" />
    {{ $t("board.createTaskButton") }}
  </button>
</template>
