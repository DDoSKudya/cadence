<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { TrashIcon, XMarkIcon } from "@heroicons/vue/24/outline";

import ColumnColorField from "@/features/settings/components/ColumnColorField.vue";
import ColumnStatusBindings from "@/features/settings/components/ColumnStatusBindings.vue";
import { useActionFeedback } from "@/composables/useActionFeedback";
import {
  ColumnInUseError,
  createColumn,
  deleteColumn,
  updateColumn,
} from "@/features/settings/api";
import type { SettingsColumn } from "@/features/settings/types";
import type { TaskStatusGraph } from "@/features/settings/task-status-graph";
import { columnDotStyle, columnPreviewLaneStyle } from "@/lib/column-color";
import { statusDisplayName } from "@/lib/workflow-labels";

const props = defineProps<{
  mode: "create" | "edit";
  column: SettingsColumn | null;
  statusGraph: TaskStatusGraph;
  readOnly?: boolean;
  createDisabled?: boolean;
  createDisabledTitle?: string;
}>();

const emit = defineEmits<{
  close: [];
  changed: [];
}>();
const { t } = useI18n();
const feedback = useActionFeedback();

const name = ref("");
const color = ref("slate");
const wipLimit = ref("");
const boundStatusIds = ref<number[]>([]);
const saving = ref(false);
const deleting = ref(false);
const formError = ref("");

const isCreate = computed(() => props.mode === "create");
const isReadOnly = computed(() => props.readOnly ?? false);
const canDelete = computed(
  () => !isCreate.value && !isReadOnly.value && props.column?.system_type !== "done",
);
const panelTitle = computed(() =>
  isCreate.value ? t("settings.newColumn") : props.column?.name || t("settings.editColumn"),
);

const attachedStatusNames = computed(() => {
  const ids = new Set(boundStatusIds.value);
  return props.statusGraph.statuses
    .filter((status) => status.id !== null && ids.has(status.id))
    .map((status) => statusDisplayName(status));
});

const previewStyle = computed(() =>
  columnPreviewLaneStyle(color.value || "slate"),
);

function resetCreateForm() {
  name.value = "";
  color.value = "slate";
  wipLimit.value = "";
  boundStatusIds.value = [];
  formError.value = "";
}

function syncEditForm() {
  if (!props.column) {
    return;
  }
  name.value = props.column.name;
  color.value = props.column.color;
  wipLimit.value =
    props.column.wip_limit === null ? "" : String(props.column.wip_limit);
  boundStatusIds.value = [...(props.column.bound_status_ids ?? [])];
  formError.value = "";
}

watch(
  () => [props.mode, props.column?.id] as const,
  ([mode]) => {
    if (mode === "create") {
      resetCreateForm();
      return;
    }
    syncEditForm();
  },
  { immediate: true },
);

function onKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") {
    close();
  }
}

onMounted(() => {
  document.addEventListener("keydown", onKeydown);
});

onUnmounted(() => {
  document.removeEventListener("keydown", onKeydown);
});

function close() {
  emit("close");
}

function parseWipLimit(): number | null {
  const trimmed = wipLimit.value.trim();
  if (!trimmed) {
    return null;
  }
  const value = Number(trimmed);
  return Number.isFinite(value) && value >= 1 ? value : null;
}

async function submitCreate() {
  if (props.createDisabled) {
    return;
  }
  if (!name.value.trim()) {
    formError.value = t("settings.columnNameRequired");
    return;
  }

  saving.value = true;
  formError.value = "";

  try {
    await createColumn({
      name: name.value.trim(),
      color: color.value.trim() || "slate",
    });
    feedback.successKey("toast.columnCreated");
  } catch (createError) {
    saving.value = false;
    feedback.fromError(createError, "errors.createColumn");
    return;
  }

  saving.value = false;
  emit("changed");
  close();
}

async function submitEdit() {
  if (!props.column) {
    return;
  }
  if (!name.value.trim()) {
    formError.value = t("settings.columnNameRequired");
    return;
  }

  saving.value = true;
  formError.value = "";

  try {
    await updateColumn(props.column.id, {
      name: name.value.trim(),
      color: color.value.trim() || "slate",
      wip_limit: parseWipLimit(),
      task_status_ids: boundStatusIds.value,
    });
    feedback.successKey("toast.columnSaved");
  } catch (updateError) {
    saving.value = false;
    feedback.fromError(updateError, "errors.saveColumn");
    return;
  }

  saving.value = false;
  emit("changed");
  close();
}

async function removeColumn() {
  if (!props.column || !canDelete.value) {
    return;
  }

  deleting.value = true;
  formError.value = "";

  try {
    await deleteColumn(props.column.id);
    feedback.successKey("toast.columnRemoved");
  } catch (removeError) {
    deleting.value = false;
    if (removeError instanceof ColumnInUseError) {
      feedback.errorKey("errors.columnHasTasks");
      return;
    }
    feedback.fromError(removeError, "errors.deleteColumn");
    return;
  }

  deleting.value = false;
  emit("changed");
  close();
}

function submit() {
  if (isCreate.value) {
    void submitCreate();
    return;
  }
  void submitEdit();
}
</script>

<template>
  <section class="settings-panel columns-detail-panel" role="region" :aria-label="panelTitle">
    <header class="settings-panel-header columns-detail-header">
      <div class="columns-detail-header-main">
        <p class="drawer-eyebrow">
          {{ isCreate ? $t("board.createEyebrow") : $t("board.editEyebrow") }}
        </p>
        <h2 class="settings-panel-title">{{ panelTitle }}</h2>
      </div>
      <button
        class="icon-btn columns-action-btn"
        type="button"
        :aria-label="$t('common.close')"
        @click="close"
      >
        <XMarkIcon class="icon-sm" />
      </button>
    </header>

    <div class="settings-panel-body columns-detail-body">
      <p v-if="formError" class="alert-error">{{ formError }}</p>

      <div class="columns-preview-card" :style="previewStyle">
        <span class="columns-preview-dot" :style="columnDotStyle(color)" />
        <div class="columns-preview-card-copy">
          <span class="columns-preview-card-name">
            {{ name.trim() || $t("settings.columnNamePlaceholder") }}
          </span>
          <span v-if="attachedStatusNames.length" class="columns-preview-card-status">
            {{ attachedStatusNames.join(" · ") }}
          </span>
        </div>
      </div>

      <form class="task-form columns-detail-form" @submit.prevent="submit">
        <p v-if="isReadOnly" class="columns-readonly-banner">
          {{ $t("settings.columnReadOnlyBanner") }}
        </p>
        <section class="columns-form-section">
          <h3 class="columns-form-section-title">{{ $t("settings.columnAppearanceSection") }}</h3>

          <label class="form-field">
            <span class="form-label">{{ $t("common.name") }}</span>
            <input
              v-model="name"
              class="field px-3 py-2"
              :placeholder="isCreate ? $t('settings.columnNamePlaceholder') : undefined"
            required
            type="text"
            :disabled="isReadOnly"
          />
          </label>

          <div class="form-field">
            <span class="form-label">{{ $t("settings.columnColor") }}</span>
            <ColumnColorField v-model="color" />
          </div>

          <label v-if="!isCreate" class="form-field">
            <span class="form-label">{{ $t("settings.wipLimit") }}</span>
            <input
              v-model="wipLimit"
              class="field px-3 py-2"
              :placeholder="$t('settings.noLimit')"
              type="number"
              min="1"
              :disabled="isReadOnly"
            />
          </label>
        </section>

        <section class="columns-form-section">
          <h3 class="columns-form-section-title">{{ $t("settings.columnStatusBindingsTitle") }}</h3>

          <div v-if="!isCreate && column" class="form-field">
            <p class="form-hint column-status-bindings-hint">
              {{ $t("settings.columnStatusBindingsHint") }}
            </p>
            <ColumnStatusBindings
              v-model="boundStatusIds"
              :statuses="statusGraph.statuses"
              :read-only="isReadOnly"
            />
          </div>
          <p v-else class="form-hint">{{ $t("settings.columnStatusBindingsAfterCreate") }}</p>
        </section>
      </form>
    </div>

    <footer class="settings-panel-footer" :class="{ 'drawer-footer-split': canDelete }">
      <button
        v-if="canDelete"
        class="btn-ghost columns-delete-btn px-4 py-2 text-sm"
        type="button"
        :disabled="deleting || saving"
        @click="removeColumn"
      >
        <TrashIcon class="icon-sm" />
        {{ $t("common.remove") }}
      </button>
      <div class="drawer-footer-actions">
        <button class="btn-ghost px-4 py-2 text-sm" type="button" @click="close">
          {{ $t("common.cancel") }}
        </button>
        <button
          class="btn-primary px-4 py-2 text-sm disabled:opacity-60"
          :disabled="saving || deleting || isReadOnly || (isCreate && createDisabled)"
          :title="isCreate && createDisabled ? createDisabledTitle : undefined"
          type="button"
          @click="submit"
        >
          {{ saving ? $t("common.saving") : isCreate ? $t("common.create") : $t("common.save") }}
        </button>
      </div>
    </footer>
  </section>
</template>
