<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import draggable from "vuedraggable";
import { ExclamationTriangleIcon } from "@heroicons/vue/24/outline";

import {
  columnCountStyle,
  columnDotStyle,
  columnHeaderStyle,
} from "@/lib/column-color";
import { columnDisplayName } from "@/lib/column-display";
import { useBoardStore } from "@/features/board/stores/board";
import type { BoardColumn, BoardTask } from "@/features/board/types";

import TaskCard from "./TaskCard.vue";

const props = defineProps<{
  column: BoardColumn;
}>();

const board = useBoardStore();
const { locale } = useI18n();

const displayName = computed(() => {
  void locale.value;
  return columnDisplayName(props.column);
});

const visibleCount = computed(
  () => board.visibleTasks(props.column.id).length,
);

const taskCount = computed(() =>
  board.filtersActive ? visibleCount.value : props.column.tasks.length,
);

const wipExceeded = () =>
  props.column.wip_limit !== null && props.column.tasks.length > props.column.wip_limit;

interface DragChangeEvent {
  added?: { element: BoardTask; newIndex: number };
  moved?: { element: BoardTask; newIndex: number };
}

async function onDragChange(event: DragChangeEvent) {
  const change = event.added ?? event.moved;
  if (!change) {
    return;
  }
  try {
    await board.moveTask(change.element.id, props.column.id, change.newIndex);
  } catch {
    return;
  }
}
</script>

<template>
  <section class="board-column">
    <header
      class="board-column-header board-column-header-accent"
      :style="columnHeaderStyle(column.color)"
    >
      <div class="board-column-title">
        <span
          class="column-dot"
          :style="columnDotStyle(column.color)"
        />
        <h2 class="board-column-name">{{ displayName }}</h2>
        <span class="column-count" :style="columnCountStyle(column.color)">
          {{ taskCount }}
        </span>
      </div>
      <p v-if="wipExceeded()" class="column-wip-warning">
        <ExclamationTriangleIcon class="icon-sm" />
        {{ $t("board.wipExceeded", { current: column.tasks.length, limit: column.wip_limit }) }}
      </p>
    </header>

    <div class="board-column-body">
      <p v-if="board.filtersActive" class="column-hint">
        {{ $t("board.dragDisabledByFilters") }}
      </p>

      <draggable
        :list="column.tasks"
        item-key="id"
        group="board-tasks"
        :animation="200"
        :disabled="board.filtersActive"
        ghost-class="task-card-ghost"
        drag-class="task-card-drag"
        class="board-column-list"
        @change="onDragChange"
      >
        <template #item="{ element }">
          <TaskCard
            v-show="board.visibleTasks(column.id).some((task) => task.id === element.id)"
            :task="element"
            @open="board.openTask"
          />
        </template>
      </draggable>

      <p v-if="visibleCount === 0 && !board.filtersActive" class="column-empty">
        {{ $t("board.dropTaskHere") }}
      </p>
    </div>
  </section>
</template>
