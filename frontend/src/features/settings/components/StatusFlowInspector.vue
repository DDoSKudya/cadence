<script setup lang="ts">
import { computed } from "vue";

import type { SettingsColumn } from "@/features/settings/types";
import type { TaskStatusNode, TaskStatusTransition } from "@/features/settings/task-status-graph";
import { statusDisplayName } from "@/lib/workflow-labels";

const props = defineProps<{
  status: TaskStatusNode | null;
  transition: TaskStatusTransition | null;
  transitionLabel: string;
  columns: SettingsColumn[];
  readOnly?: boolean;
}>();

const emit = defineEmits<{
  updateStatus: [TaskStatusNode];
  updateTransition: [TaskStatusTransition];
}>();

const readOnly = computed(() => props.readOnly ?? false);

function updateStatus(patch: Partial<TaskStatusNode>) {
  if (!props.status || readOnly.value) {
    return;
  }
  emit("updateStatus", { ...props.status, ...patch });
}

function updateStatusRules(key: string, value: unknown) {
  if (!props.status || readOnly.value) {
    return;
  }
  const rules = { ...props.status.rules, [key]: value };
  if (value === false || value === "" || (Array.isArray(value) && value.length === 0)) {
    delete rules[key];
  }
  emit("updateStatus", { ...props.status, rules });
}

function updateTransitionRules(requiredFields: string) {
  if (!props.transition || readOnly.value) {
    return;
  }
  const fields = requiredFields
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const rules = { ...props.transition.rules };
  if (fields.length) {
    rules.required_fields = fields;
  } else {
    delete rules.required_fields;
  }
  emit("updateTransition", { ...props.transition, rules });
}

const requiredFieldsText = computed(() => {
  const fields = props.transition?.rules?.required_fields;
  return Array.isArray(fields) ? fields.join(", ") : "";
});
</script>

<template>
  <aside v-if="status || transition" class="status-flow-inspector">
    <template v-if="status">
      <p class="status-flow-inspector-eyebrow">{{ $t("settings.statusFlowInspectorStatus") }}</p>
      <h3 class="status-flow-inspector-title">{{ statusDisplayName(status) }}</h3>

      <label class="status-flow-field">
        <span>{{ $t("settings.statusFlowColumnLabel") }}</span>
        <select
          class="status-flow-select"
          :disabled="readOnly"
          :value="status.column_id ?? ''"
          @change="
            updateStatus({
              column_id: ($event.target as HTMLSelectElement).value
                ? Number(($event.target as HTMLSelectElement).value)
                : null,
              column_name:
                columns.find(
                  (column) => column.id === Number(($event.target as HTMLSelectElement).value),
                )?.name ?? null,
            })
          "
        >
          <option value="">{{ $t("settings.statusFlowColumnNone") }}</option>
          <option v-for="column in columns" :key="column.id" :value="column.id">
            {{ column.name }}
          </option>
        </select>
      </label>

      <div class="status-flow-checks">
        <label class="status-flow-check">
          <input
            type="checkbox"
            :checked="status.is_initial"
            :disabled="readOnly"
            @change="updateStatus({ is_initial: ($event.target as HTMLInputElement).checked })"
          />
          <span>{{ $t("settings.statusFlowInitial") }}</span>
        </label>
        <label class="status-flow-check">
          <input
            type="checkbox"
            :checked="status.is_terminal"
            :disabled="readOnly"
            @change="updateStatus({ is_terminal: ($event.target as HTMLInputElement).checked })"
          />
          <span>{{ $t("settings.statusFlowTerminal") }}</span>
        </label>
        <label class="status-flow-check">
          <input
            type="checkbox"
            :checked="Boolean(status.rules.creation_only)"
            :disabled="readOnly"
            @change="updateStatusRules('creation_only', ($event.target as HTMLInputElement).checked)"
          />
          <span>{{ $t("settings.statusRuleCreationOnly") }}</span>
        </label>
        <label class="status-flow-check">
          <input
            type="checkbox"
            :checked="Boolean(status.rules.auto_move_column)"
            :disabled="readOnly"
            @change="
              updateStatusRules('auto_move_column', ($event.target as HTMLInputElement).checked)
            "
          />
          <span>{{ $t("settings.statusRuleAutoMove") }}</span>
        </label>
      </div>
    </template>

    <template v-else-if="transition">
      <p class="status-flow-inspector-eyebrow">{{ $t("settings.statusFlowInspectorTransition") }}</p>
      <h3 class="status-flow-inspector-title">{{ transitionLabel }}</h3>

      <label class="status-flow-field">
        <span>{{ $t("settings.statusRuleRequiredFields") }}</span>
        <input
          class="status-flow-input"
          type="text"
          :value="requiredFieldsText"
          :disabled="readOnly"
          :placeholder="$t('settings.statusRuleRequiredFieldsPlaceholder')"
          @change="updateTransitionRules(($event.target as HTMLInputElement).value)"
        />
      </label>

      <label class="status-flow-check">
        <input
          type="checkbox"
          :checked="Boolean(transition.rules?.auto_move_column)"
          :disabled="readOnly"
          @change="
            emit('updateTransition', {
              ...transition,
              rules: {
                ...transition.rules,
                auto_move_column: ($event.target as HTMLInputElement).checked || undefined,
              },
            })
          "
        />
        <span>{{ $t("settings.statusRuleAutoMove") }}</span>
      </label>
    </template>
  </aside>
</template>
