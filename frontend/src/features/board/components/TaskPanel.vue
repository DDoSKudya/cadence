<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  BellIcon,
  CalendarDaysIcon,
  CheckCircleIcon,
  LinkIcon,
  TagIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";

import * as boardApi from "@/features/board/api";
import { priorityLabel } from "@/features/board/labels";
import { useBoardStore } from "@/features/board/stores/board";
import type { TaskDetail } from "@/features/board/types";
import { fromLocalInput, toLocalInput } from "@/lib/task-form";

const board = useBoardStore();
const { t } = useI18n();

const task = ref<TaskDetail | null>(null);
const loading = ref(false);
const saving = ref(false);
const closing = ref(false);
const formError = ref("");
const titleInput = ref<HTMLInputElement | null>(null);

const title = ref("");
const description = ref("");
const columnId = ref<number | null>(null);
const priority = ref("normal");
const dueAt = ref("");
const evidenceUrl = ref("");
const reminderEnabled = ref(true);
const selectedTagSlugs = ref<string[]>([]);

const isOpen = computed(() => board.taskPanel !== null);
const isCreate = computed(() => board.taskPanel?.mode === "create");
const panelTitle = computed(() => (isCreate.value ? t("board.newTask") : t("board.task")));
const isClosed = computed(() => Boolean(task.value?.closed_at));

const defaultColumnId = computed(() => {
  const backlog = board.sortedColumns.find((column) => column.system_type === "backlog");
  return backlog?.id ?? board.sortedColumns[0]?.id ?? null;
});

function resetCreateForm() {
  task.value = null;
  formError.value = "";
  title.value = "";
  description.value = "";
  columnId.value = defaultColumnId.value;
  priority.value = "normal";
  dueAt.value = "";
  evidenceUrl.value = "";
  reminderEnabled.value = true;
  selectedTagSlugs.value = [];
}

function syncForm(nextTask: TaskDetail) {
  title.value = nextTask.title;
  description.value = nextTask.description;
  columnId.value = nextTask.column_id;
  priority.value = nextTask.priority;
  dueAt.value = toLocalInput(nextTask.due_at);
  evidenceUrl.value = nextTask.evidence_url;
  reminderEnabled.value = nextTask.reminder_enabled;
  selectedTagSlugs.value = nextTask.tags.map((tag) => tag.slug);
}

async function loadTask(taskId: number) {
  loading.value = true;
  formError.value = "";
  try {
    const loaded = await boardApi.fetchTask(taskId);
    task.value = loaded;
    syncForm(loaded);
  } catch (loadError) {
    formError.value =
      loadError instanceof Error ? loadError.message : t("board.loadFailed");
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
    if (panel.mode === "create") {
      resetCreateForm();
      await nextTick();
      titleInput.value?.focus();
      return;
    }
    void loadTask(panel.taskId);
  },
);

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

  saving.value = true;
  formError.value = "";
  try {
    await board.createTask({
      title: trimmed,
      column_id: targetColumnId,
      description: description.value,
      priority: priority.value,
      tags: selectedTagSlugs.value,
      due_at: fromLocalInput(dueAt.value),
      evidence_url: evidenceUrl.value.trim(),
      reminder_enabled: reminderEnabled.value,
    });
    closePanel();
  } catch (saveError) {
    formError.value =
      saveError instanceof Error ? saveError.message : t("board.createFailed");
  } finally {
    saving.value = false;
  }
}

async function saveTask() {
  if (!task.value) {
    return;
  }
  saving.value = true;
  formError.value = "";
  try {
    const updated = await boardApi.updateTask(task.value.id, {
      title: title.value.trim(),
      description: description.value,
      priority: priority.value,
      tags: selectedTagSlugs.value,
      due_at: fromLocalInput(dueAt.value),
      evidence_url: evidenceUrl.value.trim(),
      reminder_enabled: reminderEnabled.value,
    });
    task.value = updated;
    syncForm(updated);
    await board.refreshAfterDrawer();
  } catch (saveError) {
    formError.value =
      saveError instanceof Error ? saveError.message : t("board.saveFailed");
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
    await boardApi.closeTask(task.value.id, "", evidenceUrl.value.trim() || undefined);
    closePanel();
    await board.refreshAfterDrawer();
  } catch (closeError) {
    formError.value =
      closeError instanceof Error ? closeError.message : t("board.closeFailed");
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

            <label v-if="isCreate" class="form-field">
              <span class="form-label">{{ $t("board.column") }}</span>
              <select v-model="columnId" class="field px-3 py-2">
                <option v-for="column in board.sortedColumns" :key="column.id" :value="column.id">
                  {{ column.name }}
                </option>
              </select>
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
                <LinkIcon class="icon-sm inline" />
                {{ $t("board.evidenceUrl") }}
              </span>
              <input
                v-model="evidenceUrl"
                class="field px-3 py-2"
                :placeholder="$t('board.evidencePlaceholder')"
                type="url"
              />
            </label>

            <label class="form-field form-field-inline">
              <input v-model="reminderEnabled" type="checkbox" />
              <span class="form-label-inline">
                <BellIcon class="icon-sm" />
                {{ $t("board.remindersEnabled") }}
              </span>
            </label>

            <fieldset v-if="board.tags.length" class="form-field">
              <legend class="form-label">
                <TagIcon class="icon-sm inline" />
                {{ $t("common.tags") }}
              </legend>
              <div class="tag-picker">
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
                  <span>{{ tag.name }}</span>
                </label>
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
              v-if="!isClosed"
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
