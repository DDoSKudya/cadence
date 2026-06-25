<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ArrowPathIcon, CheckIcon } from "@heroicons/vue/24/outline";

import { saveColumnWorkflow } from "@/features/settings/api";
import { useActionFeedback } from "@/composables/useActionFeedback";
import { columnDisplayName } from "@/features/settings/scheme-display";
import type { SettingsColumn } from "@/features/settings/types";
import {
  matrixFromWorkflow,
  transitionsFromMatrix,
  type ColumnWorkflow,
} from "@/features/settings/workflow";
import { columnDotStyle } from "@/lib/column-color";

const props = defineProps<{
  columns: SettingsColumn[];
  workflow: ColumnWorkflow;
  readOnly?: boolean;
}>();

const emit = defineEmits<{
  saved: [ColumnWorkflow];
}>();

const feedback = useActionFeedback();
const readOnly = computed(() => props.readOnly ?? false);
const matrix = ref<Record<string, boolean>>({});
const saving = ref(false);
const formError = ref("");

const sortedColumns = computed(() =>
  [...props.columns].sort((left, right) => left.position - right.position),
);

const totalPossible = computed(() => {
  const count = sortedColumns.value.length;
  return count > 1 ? count * (count - 1) : 0;
});

const allowedCount = computed(
  () => Object.values(matrix.value).filter(Boolean).length,
);

function syncMatrix() {
  matrix.value = matrixFromWorkflow(props.workflow, sortedColumns.value);
}

watch(
  () => [props.workflow, props.columns] as const,
  () => {
    syncMatrix();
  },
  { immediate: true, deep: true },
);

function cellKey(fromColumnId: number, toColumnId: number): string {
  return `${fromColumnId}->${toColumnId}`;
}

function isChecked(fromColumnId: number, toColumnId: number): boolean {
  return matrix.value[cellKey(fromColumnId, toColumnId)] ?? false;
}

function toggleCell(fromColumnId: number, toColumnId: number) {
  if (readOnly.value) {
    return;
  }
  const key = cellKey(fromColumnId, toColumnId);
  matrix.value = {
    ...matrix.value,
    [key]: !matrix.value[key],
  };
}

function rowTargets(fromColumn: SettingsColumn): SettingsColumn[] {
  return sortedColumns.value.filter((column) => column.id !== fromColumn.id);
}

function rowAllowedCount(fromColumnId: number): number {
  const fromColumn = sortedColumns.value.find((column) => column.id === fromColumnId);
  if (!fromColumn) {
    return 0;
  }
  return rowTargets(fromColumn).filter((column) => isChecked(fromColumnId, column.id)).length;
}

function rowTotalTargets(fromColumnId: number): number {
  void fromColumnId;
  return Math.max(sortedColumns.value.length - 1, 0);
}

function setRowAll(fromColumnId: number, enabled: boolean) {
  if (readOnly.value) {
    return;
  }
  const fromColumn = sortedColumns.value.find((column) => column.id === fromColumnId);
  if (!fromColumn) {
    return;
  }
  const next = { ...matrix.value };
  for (const target of rowTargets(fromColumn)) {
    next[cellKey(fromColumnId, target.id)] = enabled;
  }
  matrix.value = next;
}

async function persistTransitions(transitions: ColumnWorkflow["transitions"]) {
  saving.value = true;
  formError.value = "";
  try {
    const saved = await saveColumnWorkflow(transitions);
    emit("saved", saved);
    feedback.successKey("toast.workflowSaved");
  } catch (saveError) {
    feedback.fromError(saveError, "errors.saveWorkflow");
  } finally {
    saving.value = false;
  }
}

async function saveMatrix() {
  await persistTransitions(transitionsFromMatrix(sortedColumns.value, matrix.value));
}

async function allowAllTransitions() {
  await persistTransitions([]);
}
</script>

<template>
  <section
    class="settings-panel columns-workflow-panel"
    role="region"
    :aria-label="$t('settings.workflowTitle')"
  >
    <header class="settings-panel-header workflow-board-header">
      <div class="workflow-board-header-copy">
        <p class="drawer-eyebrow">{{ $t("settings.workflowEyebrow") }}</p>
        <h2 class="settings-panel-title">{{ $t("settings.workflowTitle") }}</h2>
        <p class="columns-workflow-hint">
          {{
            workflow.enforced
              ? $t("settings.workflowEnforcedHint")
              : $t("settings.workflowOpenHint")
          }}
        </p>
      </div>

      <div class="workflow-board-meta">
        <span
          class="workflow-mode-badge"
          :class="
            workflow.enforced ? 'workflow-mode-badge-restricted' : 'workflow-mode-badge-open'
          "
        >
          {{
            workflow.enforced
              ? $t("settings.workflowStatusRestricted")
              : $t("settings.workflowStatusOpen")
          }}
        </span>
        <span v-if="sortedColumns.length > 1" class="workflow-board-summary">
          {{ $t("settings.workflowSummary", { allowed: allowedCount, total: totalPossible }) }}
        </span>
      </div>
    </header>

    <div class="settings-panel-body columns-workflow-body">
      <p v-if="formError" class="alert-error">{{ formError }}</p>

      <p v-if="sortedColumns.length < 2" class="workflow-board-empty">
        {{ $t("settings.workflowNeedColumns") }}
      </p>

      <div v-else class="workflow-board" role="list">
        <article
          v-for="(fromColumn, index) in sortedColumns"
          :key="fromColumn.id"
          class="workflow-row scheme-stagger-item"
          :style="{ '--scheme-item-delay': `${index * 40}ms` }"
          role="listitem"
        >
          <div class="workflow-row-source">
            <span class="workflow-row-source-accent" :style="columnDotStyle(fromColumn.color)" />
            <div class="workflow-row-source-copy">
              <p class="workflow-row-source-label">{{ $t("settings.workflowFromColumn") }}</p>
              <p class="workflow-row-source-name">{{ columnDisplayName(fromColumn) }}</p>
              <p class="workflow-row-source-meta">
                {{
                  $t("settings.workflowRowSummary", {
                    count: rowAllowedCount(fromColumn.id),
                    total: rowTotalTargets(fromColumn.id),
                  })
                }}
              </p>
            </div>
          </div>

          <div class="workflow-row-targets">
            <div class="workflow-row-targets-head">
              <p class="workflow-row-targets-label">{{ $t("settings.workflowToColumns") }}</p>
              <div v-if="!readOnly" class="workflow-row-actions">
                <button
                  class="workflow-row-action"
                  type="button"
                  @click="setRowAll(fromColumn.id, true)"
                >
                  {{ $t("settings.workflowSelectAll") }}
                </button>
                <button
                  class="workflow-row-action"
                  type="button"
                  @click="setRowAll(fromColumn.id, false)"
                >
                  {{ $t("settings.workflowClearAll") }}
                </button>
              </div>
            </div>

            <div class="workflow-chip-grid">
              <button
                v-for="toColumn in rowTargets(fromColumn)"
                :key="`${fromColumn.id}-${toColumn.id}`"
                class="workflow-chip"
                :class="{ 'workflow-chip-on': isChecked(fromColumn.id, toColumn.id) }"
                type="button"
                :disabled="readOnly"
                :aria-pressed="isChecked(fromColumn.id, toColumn.id)"
                :aria-label="
                  $t('settings.workflowToggleAria', {
                    from: columnDisplayName(fromColumn),
                    to: columnDisplayName(toColumn),
                  })
                "
                @click="toggleCell(fromColumn.id, toColumn.id)"
              >
                <span class="workflow-chip-dot" :style="columnDotStyle(toColumn.color)" />
                <span class="workflow-chip-name">{{ columnDisplayName(toColumn) }}</span>
                <CheckIcon
                  v-if="isChecked(fromColumn.id, toColumn.id)"
                  class="workflow-chip-check icon-sm"
                  aria-hidden="true"
                />
              </button>
            </div>
          </div>
        </article>
      </div>
    </div>

    <footer class="settings-panel-footer drawer-footer-split">
      <button
        class="btn-ghost columns-workflow-reset px-4 py-2 text-sm"
        type="button"
        :disabled="saving || !workflow.enforced || readOnly"
        @click="allowAllTransitions"
      >
        <ArrowPathIcon class="icon-sm" />
        {{ $t("settings.workflowAllowAll") }}
      </button>
      <div class="drawer-footer-actions">
        <button
          class="btn-primary px-4 py-2 text-sm disabled:opacity-60"
          type="button"
          :disabled="saving || readOnly || sortedColumns.length < 2"
          @click="saveMatrix"
        >
          {{ saving ? $t("common.saving") : $t("settings.workflowSave") }}
        </button>
      </div>
    </footer>
  </section>
</template>
