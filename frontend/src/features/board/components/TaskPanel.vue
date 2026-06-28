<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { RouterLink } from "vue-router";
import {
  BellIcon,
  CalendarDaysIcon,
  CheckCircleIcon,
  HashtagIcon,
  LinkIcon,
  TagIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";

import * as boardApi from "@/features/board/api";
import {
  LINK_TYPE_OPTIONS,
  linkTypeLabel,
  priorityLabel,
  TASK_TYPE_OPTIONS,
  taskTypeLabel,
} from "@/features/board/labels";
import { useBoardStore } from "@/features/board/stores/board";
import {
  allowedStatusTargets,
  findInitialStatus,
} from "@/features/board/task-status";
import { isTerminalBoardColumn } from "@/features/board/columns";
import { isTerminalStatus } from "@/features/settings/task-status-graph";
import type { BoardTask, TaskDetail, TaskLinkType, TaskType } from "@/features/board/types";
import { useActionFeedback } from "@/composables/useActionFeedback";
import { statusDisplayName } from "@/lib/workflow-labels";
import { columnDotStyle } from "@/lib/column-color";
import { columnDisplayName } from "@/lib/column-display";
import { fromLocalInput, toLocalInput } from "@/lib/task-form";

const board = useBoardStore();
const { t } = useI18n();
const feedback = useActionFeedback();

const task = ref<TaskDetail | null>(null);
const loading = ref(false);
const saving = ref(false);
const closing = ref(false);
const formError = ref("");
const titleInput = ref<HTMLInputElement | null>(null);

const title = ref("");
const description = ref("");
const taskType = ref<TaskType>("task");
const columnId = ref<number | null>(null);
const taskStatusId = ref<number | null>(null);
const priority = ref("normal");
const dueAt = ref("");
const storyPoints = ref("");
const externalRef = ref("");
const reminderEnabled = ref(true);
const selectedTagSlugs = ref<string[]>([]);

interface OutgoingLinkDraft {
  target_task_id: number;
  title: string;
  task_type: TaskType;
  link_type: TaskLinkType;
}

const outgoingLinks = ref<OutgoingLinkDraft[]>([]);
const linkSearchQuery = ref("");
const linkSearchResults = ref<BoardTask[]>([]);
const linkSearchLoading = ref(false);
let linkSearchTimer: ReturnType<typeof setTimeout> | null = null;

const incomingLinks = computed(() =>
  (task.value?.links ?? []).filter((link) => link.direction === "incoming"),
);

const linkedTargetIds = computed(() => new Set(outgoingLinks.value.map((link) => link.target_task_id)));

const isOpen = computed(() => board.taskPanel !== null);
const isCreate = computed(() => board.taskPanel?.mode === "create");
const panelTitle = computed(() => (isCreate.value ? t("board.newTask") : t("board.task")));
const isClosed = computed(() => Boolean(task.value?.closed_at));

const initialStatus = computed(() => findInitialStatus(board.statusGraph));

const defaultColumnId = computed(() => {
  if (initialStatus.value?.column_id) {
    return initialStatus.value.column_id;
  }
  return board.sortedColumns[0]?.id ?? null;
});

const createStatusLabel = computed(
  () => (initialStatus.value ? statusDisplayName(initialStatus.value) : "—"),
);

const statusOptions = computed(() => {
  if (!task.value?.task_status_id) {
    return board.statusGraph.statuses.filter((status) => status.id !== null);
  }
  const current = board.statusGraph.statuses.find(
    (status) => status.id === task.value?.task_status_id,
  );
  const targets = allowedStatusTargets(board.statusGraph, task.value.task_status_id);
  const options = current ? [current, ...targets.filter((s) => s.id !== current.id)] : targets;
  const seen = new Set<number>();
  return options.filter((status) => {
    if (status.id === null || seen.has(status.id)) {
      return false;
    }
    seen.add(status.id);
    return true;
  });
});

const statusLocked = computed(() => {
  const current = board.statusGraph.statuses.find(
    (status) => status.id === task.value?.task_status_id,
  );
  return isTerminalStatus(current);
});

const canCloseTask = computed(() => {
  if (!task.value || isClosed.value) {
    return false;
  }
  return isTerminalBoardColumn(task.value.column_id, board.sortedColumns);
});

function resetCreateForm() {
  task.value = null;
  formError.value = "";
  title.value = "";
  description.value = "";
  taskType.value = "task";
  columnId.value = defaultColumnId.value;
  taskStatusId.value = initialStatus.value?.id ?? null;
  priority.value = "normal";
  dueAt.value = "";
  storyPoints.value = "";
  externalRef.value = "";
  reminderEnabled.value = true;
  selectedTagSlugs.value = [];
  outgoingLinks.value = [];
  linkSearchQuery.value = "";
  linkSearchResults.value = [];
}

function syncOutgoingLinks(nextTask: TaskDetail) {
  outgoingLinks.value = nextTask.links
    .filter((link) => link.direction === "outgoing")
    .map((link) => ({
      target_task_id: link.task_id,
      title: link.title,
      task_type: link.task_type,
      link_type: link.link_type,
    }));
}

function syncForm(nextTask: TaskDetail) {
  title.value = nextTask.title;
  description.value = nextTask.description;
  taskType.value = nextTask.task_type;
  columnId.value = nextTask.column_id;
  taskStatusId.value = nextTask.task_status_id;
  priority.value = nextTask.priority;
  dueAt.value = toLocalInput(nextTask.due_at);
  storyPoints.value =
    nextTask.story_points != null ? String(nextTask.story_points) : "";
  externalRef.value = nextTask.external_ref ?? "";
  reminderEnabled.value = nextTask.reminder_enabled;
  selectedTagSlugs.value = nextTask.tags.map((tag) => tag.slug);
  syncOutgoingLinks(nextTask);
  linkSearchQuery.value = "";
  linkSearchResults.value = [];
}

async function loadTask(taskId: number) {
  loading.value = true;
  formError.value = "";
  try {
    const loaded = await boardApi.fetchTask(taskId);
    task.value = loaded;
    syncForm(loaded);
  } catch (loadError) {
    feedback.fromError(loadError, "board.loadFailed");
    task.value = null;
  } finally {
    loading.value = false;
  }
}

watch(
  () => board.taskPanel,
  async (panel) => {
    if (!panel) {
      task.value = null;
      formError.value = "";
      return;
    }
    void board.loadTags();
    if (panel.mode === "create") {
      resetCreateForm();
      await nextTick();
      titleInput.value?.focus();
      return;
    }
    void loadTask(panel.taskId);
  },
);

watch(defaultColumnId, (value) => {
  if (isCreate.value && columnId.value === null) {
    columnId.value = value;
  }
});

function onKeydown(event: KeyboardEvent) {
  if (event.key === "Escape" && isOpen.value) {
    closePanel();
  }
}

watch(isOpen, (open) => {
  if (open) {
    document.addEventListener("keydown", onKeydown);
    return;
  }
  document.removeEventListener("keydown", onKeydown);
});

onUnmounted(() => {
  document.removeEventListener("keydown", onKeydown);
  if (linkSearchTimer) {
    clearTimeout(linkSearchTimer);
  }
});

function toggleTag(slug: string) {
  if (selectedTagSlugs.value.includes(slug)) {
    selectedTagSlugs.value = selectedTagSlugs.value.filter((item) => item !== slug);
    return;
  }
  selectedTagSlugs.value = [...selectedTagSlugs.value, slug];
}

function closePanel() {
  board.closeTaskPanel();
}

function parseStoryPoints(): number | null | undefined {
  const trimmed = storyPoints.value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number.parseInt(trimmed, 10);
  if (!Number.isFinite(parsed) || parsed < 1 || parsed > 99) {
    return undefined;
  }
  return parsed;
}

function serializeOutgoingLinks() {
  return outgoingLinks.value.map((link) => ({
    target_task_id: link.target_task_id,
    link_type: link.link_type,
  }));
}

async function runLinkSearch() {
  const query = linkSearchQuery.value.trim();
  if (!query) {
    linkSearchResults.value = [];
    return;
  }

  linkSearchLoading.value = true;
  try {
    const results = await boardApi.searchTasks(query, task.value?.id);
    linkSearchResults.value = results.filter(
      (candidate) => !linkedTargetIds.value.has(candidate.id),
    );
  } catch (searchError) {
    feedback.fromError(searchError, "board.searchTasksFailed");
    linkSearchResults.value = [];
  } finally {
    linkSearchLoading.value = false;
  }
}

watch(linkSearchQuery, (value) => {
  if (linkSearchTimer) {
    clearTimeout(linkSearchTimer);
  }
  if (!value.trim()) {
    linkSearchResults.value = [];
    return;
  }
  linkSearchTimer = setTimeout(() => {
    void runLinkSearch();
  }, 250);
});

function addOutgoingLink(candidate: BoardTask, linkType: TaskLinkType = "relates") {
  if (linkedTargetIds.value.has(candidate.id)) {
    return;
  }
  outgoingLinks.value = [
    ...outgoingLinks.value,
    {
      target_task_id: candidate.id,
      title: candidate.title,
      task_type: candidate.task_type,
      link_type: linkType,
    },
  ];
  linkSearchResults.value = linkSearchResults.value.filter((item) => item.id !== candidate.id);
}

function removeOutgoingLink(targetTaskId: number) {
  outgoingLinks.value = outgoingLinks.value.filter(
    (link) => link.target_task_id !== targetTaskId,
  );
}

function updateOutgoingLinkType(targetTaskId: number, linkType: TaskLinkType) {
  outgoingLinks.value = outgoingLinks.value.map((link) =>
    link.target_task_id === targetTaskId ? { ...link, link_type: linkType } : link,
  );
}

function openLinkedTask(taskId: number) {
  board.openTask(taskId);
}

async function submitCreate() {
  const trimmed = title.value.trim();
  const targetColumnId = columnId.value ?? defaultColumnId.value;

  if (!trimmed) {
    formError.value = t("board.enterTaskTitle");
    return;
  }
  if (targetColumnId === null) {
    formError.value = t("board.noColumns");
    return;
  }

  const parsedStoryPoints = parseStoryPoints();
  if (parsedStoryPoints === undefined) {
    formError.value = t("board.storyPointsInvalid");
    return;
  }

  saving.value = true;
  formError.value = "";
  try {
    await board.createTask({
      title: trimmed,
      column_id: targetColumnId,
      task_type: taskType.value,
      description: description.value,
      priority: priority.value,
      tags: selectedTagSlugs.value,
      due_at: fromLocalInput(dueAt.value),
      story_points: parsedStoryPoints,
      external_ref: externalRef.value.trim(),
      reminder_enabled: reminderEnabled.value,
      links: serializeOutgoingLinks(),
    });
    closePanel();
  } catch (saveError) {
    feedback.fromError(saveError, "board.createFailed");
  } finally {
    saving.value = false;
  }
}

async function saveTask() {
  if (!task.value) {
    return;
  }
  const parsedStoryPoints = parseStoryPoints();
  if (parsedStoryPoints === undefined) {
    formError.value = t("board.storyPointsInvalid");
    return;
  }

  saving.value = true;
  formError.value = "";
  try {
    const statusChanged = taskStatusId.value !== task.value.task_status_id;
    await boardApi.updateTask(task.value.id, {
      title: title.value.trim(),
      description: description.value,
      task_type: taskType.value,
      priority: priority.value,
      tags: selectedTagSlugs.value,
      due_at: fromLocalInput(dueAt.value),
      story_points: parsedStoryPoints,
      external_ref: externalRef.value.trim(),
      reminder_enabled: reminderEnabled.value,
      links: serializeOutgoingLinks(),
      ...(statusChanged ? { task_status_id: taskStatusId.value } : {}),
    });
    closePanel();
    await board.refreshAfterDrawer();
    feedback.successKey("toast.taskUpdated");
  } catch (saveError) {
    feedback.fromError(saveError, "board.saveFailed");
  } finally {
    saving.value = false;
  }
}

async function closeTaskAction() {
  if (!task.value) {
    return;
  }
  closing.value = true;
  formError.value = "";
  try {
    await boardApi.closeTask(task.value.id);
    closePanel();
    await board.refreshAfterDrawer();
    feedback.successKey("toast.taskClosed");
  } catch (closeError) {
    feedback.fromError(closeError, "board.closeFailed");
  } finally {
    closing.value = false;
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition name="slide-panel">
      <div v-if="isOpen" class="drawer-backdrop" @click.self="closePanel">
        <aside
          class="drawer-panel"
          role="dialog"
          :aria-labelledby="isCreate ? 'task-create-title' : 'task-edit-title'"
          aria-modal="true"
        >
        <header class="drawer-header">
          <div>
            <p class="drawer-eyebrow">
              {{ isCreate ? $t("board.createEyebrow") : $t("board.editEyebrow") }}
            </p>
            <h2 :id="isCreate ? 'task-create-title' : 'task-edit-title'" class="drawer-title">
              {{ panelTitle }}
            </h2>
          </div>
          <button class="icon-btn" type="button" @click="closePanel">
            <XMarkIcon class="icon-sm" />
          </button>
        </header>

        <div class="drawer-body">
          <p v-if="loading" class="text-sm text-(--color-text-secondary)">{{ $t("common.loading") }}</p>
          <p v-else-if="formError" class="alert-error">{{ formError }}</p>

          <form
            v-if="isCreate || (task && !loading)"
            class="task-form"
            @submit.prevent="isCreate ? submitCreate() : saveTask()"
          >
            <label class="form-field">
              <span class="form-label">{{ $t("common.title") }}</span>
              <input
                ref="titleInput"
                v-model="title"
                class="field px-3 py-2"
                :placeholder="$t('board.titlePlaceholder')"
                required
                type="text"
              />
            </label>

            <label class="form-field">
              <span class="form-label">{{ $t("common.description") }}</span>
              <textarea
                v-model="description"
                class="field px-3 py-2"
                :placeholder="$t('board.descriptionPlaceholder')"
                rows="4"
              />
            </label>

            <label class="form-field">
              <span class="form-label">{{ $t("board.taskType") }}</span>
              <select v-model="taskType" class="field px-3 py-2" required>
                <option v-for="option in TASK_TYPE_OPTIONS" :key="option" :value="option">
                  {{ taskTypeLabel(option) }}
                </option>
              </select>
            </label>

            <label v-if="isCreate && !initialStatus?.column_id" class="form-field">
              <span class="form-label">{{ $t("board.column") }}</span>
              <select v-model="columnId" class="field px-3 py-2">
                <option v-for="column in board.sortedColumns" :key="column.id" :value="column.id">
                  {{ columnDisplayName(column) }}
                </option>
              </select>
            </label>

            <div v-if="isCreate" class="form-field">
              <span class="form-label">{{ $t("board.taskStatus") }}</span>
              <div class="task-status-readonly">
                <span
                  v-if="initialStatus"
                  class="task-status-readonly-dot"
                  :style="columnDotStyle(initialStatus.color)"
                />
                <span>{{ createStatusLabel }}</span>
              </div>
              <p class="form-hint">{{ $t("board.taskStatusInitialHint") }}</p>
            </div>

            <label v-else class="form-field">
              <span class="form-label">{{ $t("board.taskStatus") }}</span>
              <select
                v-model="taskStatusId"
                class="field px-3 py-2"
                :disabled="isClosed || statusLocked || statusOptions.length === 0"
              >
                <option
                  v-for="status in statusOptions"
                  :key="status.id ?? status.name"
                  :value="status.id"
                >
                  {{ statusDisplayName(status) }}
                </option>
              </select>
              <p v-if="statusLocked" class="form-hint">{{ $t("board.taskStatusTerminalHint") }}</p>
              <p v-else class="form-hint">{{ $t("board.taskStatusChangeHint") }}</p>
            </label>

            <label class="form-field">
              <span class="form-label">{{ $t("common.priority") }}</span>
              <select v-model="priority" class="field px-3 py-2">
                <option value="high">{{ priorityLabel("high") }}</option>
                <option value="normal">{{ priorityLabel("normal") }}</option>
                <option value="low">{{ priorityLabel("low") }}</option>
              </select>
            </label>

            <label class="form-field">
              <span class="form-label">
                <CalendarDaysIcon class="icon-sm inline" />
                {{ $t("board.dueDate") }}
              </span>
              <input v-model="dueAt" class="field px-3 py-2" type="datetime-local" />
            </label>

            <label class="form-field">
              <span class="form-label">
                <HashtagIcon class="icon-sm inline" />
                {{ $t("board.storyPoints") }}
              </span>
              <input
                v-model="storyPoints"
                class="field px-3 py-2"
                :placeholder="$t('board.storyPointsPlaceholder')"
                inputmode="numeric"
                min="1"
                max="99"
                type="number"
              />
              <p class="form-hint">{{ $t("board.storyPointsHint") }}</p>
            </label>

            <label class="form-field">
              <span class="form-label">{{ $t("board.externalRef") }}</span>
              <input
                v-model="externalRef"
                class="field px-3 py-2"
                :placeholder="$t('board.externalRefPlaceholder')"
                type="text"
              />
            </label>

            <label class="form-field form-field-inline">
              <input v-model="reminderEnabled" type="checkbox" />
              <span class="form-label-inline">
                <BellIcon class="icon-sm" />
                {{ $t("board.remindersEnabled") }}
              </span>
            </label>

            <fieldset class="form-field">
              <legend class="form-label">
                <TagIcon class="icon-sm inline" />
                {{ $t("common.tags") }}
              </legend>

              <div v-if="board.tags.length" class="tag-picker">
                <label
                  v-for="tag in board.tags"
                  :key="tag.id"
                  class="tag-picker-item"
                  :class="{ 'tag-picker-item-active': selectedTagSlugs.includes(tag.slug) }"
                >
                  <input
                    :checked="selectedTagSlugs.includes(tag.slug)"
                    type="checkbox"
                    @change="toggleTag(tag.slug)"
                  />
                  <span class="tag-picker-dot" :style="columnDotStyle(tag.color)" />
                  <span>{{ tag.name }}</span>
                </label>
              </div>

              <p v-else class="tag-picker-empty">
                {{ $t("board.noTagsYet") }}
              </p>

              <RouterLink class="tag-picker-manage" to="/settings/columns?tab=tags">
                {{ $t("board.manageTags") }}
              </RouterLink>
            </fieldset>

            <fieldset class="form-field">
              <legend class="form-label">
                <LinkIcon class="icon-sm inline" />
                {{ $t("board.taskLinks") }}
              </legend>
              <p class="form-hint">{{ $t("board.taskLinksHint") }}</p>

              <div v-if="incomingLinks.length" class="task-links-list">
                <div
                  v-for="link in incomingLinks"
                  :key="`incoming-${link.id ?? link.task_id}-${link.link_type}`"
                  class="task-link-row task-link-row-incoming"
                >
                  <div class="task-link-main">
                    <button
                      class="task-link-title text-left"
                      type="button"
                      @click="openLinkedTask(link.task_id)"
                    >
                      {{ link.title }}
                    </button>
                    <p class="task-link-meta">
                      {{ taskTypeLabel(link.task_type) }} ·
                      {{ linkTypeLabel(link.link_type, "incoming") }}
                    </p>
                  </div>
                </div>
              </div>

              <div v-if="outgoingLinks.length" class="task-links-list">
                <div
                  v-for="link in outgoingLinks"
                  :key="`outgoing-${link.target_task_id}-${link.link_type}`"
                  class="task-link-row"
                >
                  <div class="task-link-main">
                    <button
                      class="task-link-title text-left"
                      type="button"
                      @click="openLinkedTask(link.target_task_id)"
                    >
                      {{ link.title }}
                    </button>
                    <p class="task-link-meta">{{ taskTypeLabel(link.task_type) }}</p>
                  </div>
                  <select
                    class="field task-link-type-select px-2 py-1.5 text-sm"
                    :value="link.link_type"
                    @change="
                      updateOutgoingLinkType(
                        link.target_task_id,
                        ($event.target as HTMLSelectElement).value as TaskLinkType,
                      )
                    "
                  >
                    <option
                      v-for="option in LINK_TYPE_OPTIONS"
                      :key="option"
                      :value="option"
                    >
                      {{ linkTypeLabel(option, "outgoing") }}
                    </option>
                  </select>
                  <button
                    class="icon-btn"
                    type="button"
                    :title="$t('board.linkRemove')"
                    @click="removeOutgoingLink(link.target_task_id)"
                  >
                    <XMarkIcon class="icon-sm" />
                  </button>
                </div>
              </div>

              <label class="form-field mt-2">
                <span class="form-label">{{ $t("board.linkAdd") }}</span>
                <input
                  v-model="linkSearchQuery"
                  class="field px-3 py-2"
                  :placeholder="$t('board.linkSearchPlaceholder')"
                  type="search"
                />
              </label>

              <p v-if="linkSearchLoading" class="form-hint">{{ $t("common.loading") }}</p>
              <p
                v-else-if="linkSearchQuery.trim() && !linkSearchResults.length"
                class="form-hint"
              >
                {{ $t("board.linkSearchEmpty") }}
              </p>

              <div v-if="linkSearchResults.length" class="task-link-search-results">
                <div
                  v-for="candidate in linkSearchResults"
                  :key="candidate.id"
                  class="task-link-search-item"
                >
                  <div class="task-link-main">
                    <span class="task-link-title">{{ candidate.title }}</span>
                    <p class="task-link-meta">{{ taskTypeLabel(candidate.task_type) }}</p>
                  </div>
                  <button
                    class="btn-secondary px-2.5 py-1.5 text-xs"
                    type="button"
                    @click="addOutgoingLink(candidate)"
                  >
                    {{ $t("board.linkAdd") }}
                  </button>
                </div>
              </div>
            </fieldset>
          </form>
        </div>

        <footer v-if="isCreate || (task && !loading)" class="drawer-footer">
          <button
            v-if="isCreate"
            class="btn-primary px-4 py-2 text-sm disabled:opacity-60"
            :disabled="saving"
            type="button"
            @click="submitCreate"
          >
            {{ saving ? $t("common.saving") : $t("common.create") }}
          </button>
          <template v-else>
            <button
              class="btn-primary px-4 py-2 text-sm disabled:opacity-60"
              :disabled="saving || isClosed"
              type="button"
              @click="saveTask"
            >
              {{ saving ? $t("common.saving") : $t("common.save") }}
            </button>
            <button
              v-if="canCloseTask"
              class="btn-accent px-4 py-2 text-sm disabled:opacity-60"
              :disabled="closing"
              type="button"
              @click="closeTaskAction"
            >
              <CheckCircleIcon class="icon-sm" />
              {{ closing ? $t("board.closing") : $t("board.closeTask") }}
            </button>
          </template>
        </footer>
      </aside>
      </div>
    </Transition>
  </Teleport>
</template>
