<script setup lang="ts">
import { computed } from "vue";
import { CalendarDaysIcon, HashtagIcon, LinkIcon, TagIcon } from "@heroicons/vue/24/outline";

import type { BoardTask } from "@/features/board/types";
import { useBoardStore } from "@/features/board/stores/board";
import { priorityLabel, taskTypeLabel } from "@/features/board/labels";
import { columnDotStyle, tagChipStyle } from "@/lib/column-color";
import { formatDateTime } from "@/lib/datetime";
import { statusDisplayName } from "@/lib/workflow-labels";

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
      return { name: statusDisplayName(fromGraph), color: fromGraph.color };
    }
  }
  if (props.task.task_status_name) {
    return { name: statusDisplayName({ name: props.task.task_status_name }), color: "slate" };
  }
  return null;
});

const descriptionPreview = computed(() => props.task.description?.trim() ?? "");

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

const taskTypeBadgeClass: Record<string, string> = {
  epic: "badge-task-type-epic",
  story: "badge-task-type-story",
  task: "badge-task-type-task",
  bug: "badge-task-type-bug",
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
        <h3 class="task-card-title min-w-0 flex-1">{{ task.title }}</h3>
        <div class="task-card-badges">
          <span
            v-if="task.story_points != null"
            class="badge badge-story-points"
            :title="$t('board.storyPointsShort', { points: task.story_points })"
          >
            <HashtagIcon class="badge-story-points-icon" aria-hidden="true" />
            <span class="badge-story-points-value">{{ task.story_points }}</span>
            <span class="badge-story-points-unit">SP</span>
          </span>
          <span
            class="badge badge-task-type"
            :class="taskTypeBadgeClass[task.task_type] ?? taskTypeBadgeClass.task"
          >
            {{ taskTypeLabel(task.task_type) }}
          </span>
          <span
            class="badge"
            :class="priorityBadgeClass[task.priority] ?? priorityBadgeClass.normal"
          >
            {{ priorityLabel(task.priority) }}
          </span>
        </div>
      </div>

      <p v-if="descriptionPreview" class="task-card-description">
        {{ descriptionPreview }}
      </p>

      <p v-if="taskStatus" class="task-meta-row mt-2">
        <span class="task-card-status-dot" :style="columnDotStyle(taskStatus.color)" />
        {{ taskStatus.name }}
      </p>

      <p v-if="task.links_count" class="task-meta-row mt-2">
        <LinkIcon class="icon-sm" />
        {{ $t("board.linksCount", { count: task.links_count }) }}
      </p>

      <p v-if="task.due_at" class="task-meta-row mt-2.5">
        <CalendarDaysIcon class="icon-sm" />
        {{ formatDateTime(task.due_at) }}
      </p>

      <div v-if="task.tags.length" class="mt-2.5 flex flex-wrap gap-1.5">
        <span
          v-for="tag in task.tags"
          :key="tag.id"
          class="tag-chip"
          :style="tagChipStyle(tag.color)"
        >
          <TagIcon class="size-3" />
          {{ tag.name }}
        </span>
      </div>
    </div>
  </article>
</template>
