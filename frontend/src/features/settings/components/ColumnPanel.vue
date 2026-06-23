<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { TrashIcon } from "@heroicons/vue/24/outline";

import ColumnColorField from "@/features/settings/components/ColumnColorField.vue";
import {
  ColumnInUseError,
  createColumn,
  deleteColumn,
  updateColumn,
} from "@/features/settings/api";
import { systemTypeLabel } from "@/features/board/labels";
import type { SettingsColumn } from "@/features/settings/types";

const props = defineProps<{
  mode: "create" | "edit";
  column: SettingsColumn | null;
}>();

const emit = defineEmits<{
  close: [];
  changed: [];
}>();
const { t } = useI18n();

const name = ref("");
const color = ref("slate");
const wipLimit = ref("");
const saving = ref(false);
const deleting = ref(false);
const formError = ref("");

const isCreate = computed(() => props.mode === "create");
const canDelete = computed(
  () => !isCreate.value && props.column?.system_type !== "done",
);
const panelTitle = computed(() =>
  isCreate.value ? t("settings.newColumn") : props.column?.name || t("settings.editColumn"),
);

function resetCreateForm() {
  name.value = "";
  color.value = "slate";
  wipLimit.value = "";
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
  } catch (createError) {
    saving.value = false;
    formError.value =
      createError instanceof Error ? createError.message : t("errors.createColumn");
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
    });
  } catch (updateError) {
    saving.value = false;
    formError.value =
      updateError instanceof Error ? updateError.message : t("errors.saveColumn");
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
  } catch (removeError) {
    deleting.value = false;
    if (removeError instanceof ColumnInUseError) {
      formError.value = removeError.message;
      return;
    }
    formError.value =
      removeError instanceof Error ? removeError.message : t("errors.deleteColumn");
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
  <section class="settings-panel" role="region" :aria-label="panelTitle">
    <header class="settings-panel-header">
      <div>
        <p class="drawer-eyebrow">
          {{ isCreate ? $t("board.createEyebrow") : $t("board.editEyebrow") }}
        </p>
        <h2 class="settings-panel-title">{{ panelTitle }}</h2>
      </div>
    </header>

    <div class="settings-panel-body">
      <p v-if="formError" class="alert-error mb-4">{{ formError }}</p>

      <form class="task-form" @submit.prevent="submit">
        <label class="form-field">
          <span class="form-label">{{ $t("common.name") }}</span>
          <input
            v-model="name"
            class="field px-3 py-2"
            :placeholder="isCreate ? $t('settings.columnNamePlaceholder') : undefined"
            required
            type="text"
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
          />
        </label>

        <div v-if="!isCreate && column" class="form-field">
          <span class="form-label">{{ $t("settings.systemType") }}</span>
          <p class="columns-type-readonly">
            {{ systemTypeLabel(column.system_type) }}
          </p>
        </div>
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
          :disabled="saving || deleting"
          type="button"
          @click="submit"
        >
          {{ saving ? $t("common.saving") : isCreate ? $t("common.create") : $t("common.save") }}
        </button>
      </div>
    </footer>
  </section>
</template>
