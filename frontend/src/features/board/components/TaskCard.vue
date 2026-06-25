<script setup lang="ts">
import { computed } from "vue";
import { CalendarDaysIcon, TagIcon } from "@heroicons/vue/24/outline";

import type { BoardTask } from "@/features/board/types";
import { useBoardStore } from "@/features/board/stores/board";
import { priorityLabel } from "@/features/board/labels";
import { columnDotStyle } from "@/lib/column-color";
import { formatDateTime } from "@/lib/datetime";

const props = defineProps<{
  task: BoardTask;
}>();

defineEmits<{
  open: [taskId: number];
}>();

const board = useBoardStore();

const taskStatus = computed(() => {
  const statusId = props.task.task_status_id;
  if (statusId) {
    const fromGraph = board.statusGraph.statuses.find((status) => status.id === statusId);
    if (fromGraph) {
      return { name: fromGraph.name, color: fromGraph.color };
    }
  }
  if (props.task.task_status_name) {
    return { name: props.task.task_status_name, color: "slate" };
  }
  return null;
});

const priorityBadgeClass: Record<string, string> = {
  high: "badge-priority-high",
  normal: "badge-priority-normal",
  low: "badge-priority-low",
};

const priorityAccentClass: Record<string, string> = {
  high: "task-card-priority-high",
  normal: "task-card-priority-normal",
  low: "task-card-priority-low",
};

</script>

<template>
  <article
    class="task-card"
    :class="priorityAccentClass[task.priority] ?? priorityAccentClass.normal"
    @click="$emit('open', task.id)"
  >
    <div class="task-card-content">
      <div class="flex items-start justify-between gap-2">
        <h3 class="task-card-title">{{ task.title }}</h3>
        <span
          class="badge shrink-0"
          :class="priorityBadgeClass[task.priority] ?? priorityBadgeClass.normal"
        >
          {{ priorityLabel(task.priority) }}
        </span>
      </div>

      <p v-if="taskStatus" class="task-meta-row mt-2">
        <span class="task-card-status-dot" :style="columnDotStyle(taskStatus.color)" />
        {{ taskStatus.name }}
      </p>

      <p v-if="task.due_at" class="task-meta-row mt-2.5">
        <CalendarDaysIcon class="icon-sm" />
        {{ formatDateTime(task.due_at) }}
      </p>

      <div v-if="task.tags.length" class="mt-2.5 flex flex-wrap gap-1.5">
        <span v-for="tag in task.tags" :key="tag.id" class="tag-chip">
          <TagIcon class="size-3" />
          {{ tag.name }}
        </span>
      </div>
    </div>
  </article>
</template>
