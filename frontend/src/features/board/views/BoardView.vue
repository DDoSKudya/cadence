<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";

import BoardColumn from "@/features/board/components/BoardColumn.vue";
import BoardCreateTask from "@/features/board/components/BoardCreateTask.vue";
import BoardFilters from "@/features/board/components/BoardFilters.vue";
import BoardImportJson from "@/features/board/components/BoardImportJson.vue";
import TaskPanel from "@/features/board/components/TaskPanel.vue";
import WeekSwitcher from "@/features/board/components/WeekSwitcher.vue";
import { useBoardStore } from "@/features/board/stores/board";
import { boardDisplayName } from "@/lib/column-display";

const board = useBoardStore();
const { t, locale } = useI18n();

const totalTasks = computed(() =>
  board.sortedColumns.reduce((total, column) => total + column.tasks.length, 0),
);

const pageTitle = computed(() => {
  void locale.value;
  if (board.boardIsDefault) {
    return boardDisplayName({ name: board.boardName, is_default: true });
  }
  return board.boardName || t("board.titleFallback");
});

const metaLine = computed(() => {
  const tasks = t("board.taskCount", totalTasks.value);
  const columns = t("board.columnCount", board.sortedColumns.length);
  return `${tasks} · ${columns}`;
});

onMounted(async () => {
  await Promise.all([board.loadBoard(), board.loadTags()]);
});
</script>

<template>
  <div class="board-page">
    <div class="board-shell">
      <header class="board-toolbar shrink-0">
        <div class="board-toolbar-info">
          <h1 class="page-title">{{ pageTitle }}</h1>
          <p class="page-meta">{{ metaLine }}</p>
        </div>

        <div class="board-toolbar-actions">
          <BoardFilters />
          <WeekSwitcher />
          <BoardImportJson />
          <BoardCreateTask />
        </div>
      </header>

      <p v-if="board.error" class="alert-error mx-4 mt-3 shrink-0">
        {{ board.error }}
      </p>

      <Transition mode="out-in" name="board-swap">
        <div
          v-if="board.loading"
          key="loading"
          class="board-canvas board-canvas-center"
        >
          <div class="loading-state">
            <span class="loading-spinner" aria-hidden="true" />
            <p>{{ $t("board.loading") }}</p>
          </div>
        </div>

        <div v-else key="board" class="board-canvas">
          <BoardColumn v-for="column in board.sortedColumns" :key="column.id" :column="column" />
        </div>
      </Transition>
    </div>

    <TaskPanel />
  </div>
</template>
