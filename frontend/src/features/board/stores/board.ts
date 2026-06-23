import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { getCurrentWeekKey } from "@/lib/week";
import { t } from "@/i18n";

import * as boardApi from "../api";
import type { BoardColumn, BoardTask, Tag, TaskCreatePayload } from "../types";

export const useBoardStore = defineStore("board", () => {
  const weekKey = ref(getCurrentWeekKey());
  const weekId = ref<number | null>(null);
  const boardName = ref("");
  const columns = ref<BoardColumn[]>([]);
  const tags = ref<Tag[]>([]);
  const loading = ref(false);
  const error = ref("");
  const taskPanel = ref<{ mode: "create" } | { mode: "edit"; taskId: number } | null>(null);
  const searchQuery = ref("");
  const priorityFilter = ref("");
  const tagFilter = ref("");

  const filtersActive = computed(
    () =>
      searchQuery.value.trim().length > 0 ||
      priorityFilter.value.length > 0 ||
      tagFilter.value.length > 0,
  );

  const sortedColumns = computed(() =>
    [...columns.value].sort((left, right) => left.position - right.position),
  );

  function taskMatchesFilters(task: BoardTask): boolean {
    const query = searchQuery.value.trim().toLowerCase();
    if (query && !task.title.toLowerCase().includes(query)) {
      return false;
    }
    if (priorityFilter.value && task.priority !== priorityFilter.value) {
      return false;
    }
    if (tagFilter.value && !task.tags.some((tag) => tag.slug === tagFilter.value)) {
      return false;
    }
    return true;
  }

  function visibleTasks(columnId: number): BoardTask[] {
    const column = columns.value.find((item) => item.id === columnId);
    if (!column) {
      return [];
    }
    return column.tasks.filter(taskMatchesFilters);
  }

  function findColumn(columnId: number): BoardColumn | undefined {
    return columns.value.find((item) => item.id === columnId);
  }

  function replaceTask(task: BoardTask) {
    const column = findColumn(task.column_id);
    if (!column) {
      return;
    }
    const index = column.tasks.findIndex((item) => item.id === task.id);
    if (index >= 0) {
      column.tasks[index] = task;
      return;
    }
    column.tasks.push(task);
    column.tasks.sort((left, right) => left.position - right.position);
  }

  function removeTask(taskId: number) {
    for (const column of columns.value) {
      const index = column.tasks.findIndex((item) => item.id === taskId);
      if (index >= 0) {
        column.tasks.splice(index, 1);
        return;
      }
    }
  }

  async function loadBoard() {
    loading.value = true;
    error.value = "";
    try {
      const payload = await boardApi.fetchBoard(weekKey.value);
      boardName.value = payload.board.name;
      weekId.value = payload.week.id;
      columns.value = payload.columns;
    } catch (loadError) {
      error.value = loadError instanceof Error ? loadError.message : t("board.loadBoardFailed");
    } finally {
      loading.value = false;
    }
  }

  async function loadTags() {
    try {
      tags.value = await boardApi.fetchTags();
    } catch {
      tags.value = [];
    }
  }

  async function createTask(payload: Omit<TaskCreatePayload, "week"> & { week?: string }) {
    error.value = "";
    const task = await boardApi.createTask({
      ...payload,
      week: payload.week ?? weekKey.value,
    });
    replaceTask(task);
    return task;
  }

  async function moveTask(taskId: number, targetColumnId: number, targetPosition: number) {
    error.value = "";
    try {
      const task = await boardApi.moveTask(taskId, targetColumnId, targetPosition);
      removeTask(taskId);
      replaceTask(task);
    } catch (moveError) {
      error.value = moveError instanceof Error ? moveError.message : t("board.moveFailed");
      await loadBoard();
      throw moveError;
    }
  }

  async function refreshAfterDrawer() {
    await loadBoard();
  }

  function openCreateTask() {
    taskPanel.value = { mode: "create" };
  }

  function openTask(taskId: number) {
    taskPanel.value = { mode: "edit", taskId };
  }

  function closeTaskPanel() {
    taskPanel.value = null;
  }

  function clearFilters() {
    searchQuery.value = "";
    priorityFilter.value = "";
    tagFilter.value = "";
  }

  return {
    weekKey,
    weekId,
    boardName,
    columns,
    tags,
    loading,
    error,
    taskPanel,
    searchQuery,
    priorityFilter,
    tagFilter,
    filtersActive,
    sortedColumns,
    visibleTasks,
    findColumn,
    loadBoard,
    loadTags,
    createTask,
    moveTask,
    refreshAfterDrawer,
    openCreateTask,
    openTask,
    closeTaskPanel,
    clearFilters,
  };
});
