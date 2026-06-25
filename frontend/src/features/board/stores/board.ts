import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { getCurrentWeekKey } from "@/lib/week";
import { t } from "@/i18n";
import { useActionFeedback } from "@/composables/useActionFeedback";

import * as boardApi from "../api";
import type { BoardColumn, BoardTask, Tag, TaskCreatePayload } from "../types";
import type { TaskStatusGraph } from "@/features/settings/task-status-graph";
import { fetchTaskStatusGraph } from "@/features/settings/api";

export const useBoardStore = defineStore("board", () => {
  const weekKey = ref(getCurrentWeekKey());
  const weekId = ref<number | null>(null);
  const boardName = ref("");
  const boardIsDefault = ref(false);
  const columns = ref<BoardColumn[]>([]);
  const tags = ref<Tag[]>([]);
  const statusGraph = ref<TaskStatusGraph>({ enforced: false, statuses: [], transitions: [] });
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
      const [payload, graph] = await Promise.all([
        boardApi.fetchBoard(weekKey.value),
        fetchTaskStatusGraph().catch(() => ({
          enforced: false,
          statuses: [],
          transitions: [],
        })),
      ]);
      boardName.value = payload.board.name;
      boardIsDefault.value = Boolean(payload.board.is_default);
      weekId.value = payload.week.id;
      columns.value = payload.columns;
      statusGraph.value = graph;
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

  function findTaskColumnId(taskId: number): number | null {
    for (const column of columns.value) {
      if (column.tasks.some((task) => task.id === taskId)) {
        return column.id;
      }
    }
    return null;
  }

  async function createTask(payload: Omit<TaskCreatePayload, "week"> & { week?: string }) {
    const feedback = useActionFeedback();
    try {
      const task = await boardApi.createTask({
        ...payload,
        week: payload.week ?? weekKey.value,
      });
      replaceTask(task);
      feedback.successKey("toast.taskCreated");
      return task;
    } catch (createError) {
      feedback.fromError(createError, "board.createFailed");
      throw createError;
    }
  }

  async function moveTask(taskId: number, targetColumnId: number, targetPosition: number) {
    const feedback = useActionFeedback();
    const sourceColumnId = findTaskColumnId(taskId);
    try {
      const task = await boardApi.moveTask(taskId, targetColumnId, targetPosition);
      removeTask(taskId);
      replaceTask(task);
      if (sourceColumnId !== null && sourceColumnId !== targetColumnId) {
        feedback.successKey("toast.taskMoved");
      }
    } catch (moveError) {
      feedback.fromError(moveError, "board.moveFailed");
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
    boardIsDefault,
    columns,
    tags,
    statusGraph,
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
