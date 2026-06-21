<script setup lang="ts">
import { CalendarDaysIcon, TagIcon } from "@heroicons/vue/24/outline";

import type { BoardTask } from "@/features/board/types";
import { priorityLabel } from "@/features/board/labels";

defineProps<{
  task: BoardTask;
}>();

defineEmits<{
  open: [taskId: number];
}>();

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

function formatDue(value: string | null): string {
  if (!value) {
    return "";
  }
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
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

      <p v-if="task.due_at" class="task-meta-row mt-2.5">
        <CalendarDaysIcon class="icon-sm" />
        {{ formatDue(task.due_at) }}
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
