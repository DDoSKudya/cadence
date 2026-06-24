<script setup lang="ts">
import { computed } from "vue";
import { PlusIcon } from "@heroicons/vue/24/outline";

import type { TaskStatusNode } from "@/features/settings/task-status-graph";
import { statusNodeKey } from "@/features/settings/task-status-graph";
import { columnDotStyle } from "@/lib/column-color";

const props = defineProps<{
  statuses: TaskStatusNode[];
  selectedId: string | null;
  readOnly?: boolean;
  canAdd?: boolean;
  maxStatuses?: number;
}>();

const emit = defineEmits<{
  select: [string];
  add: [];
}>();

const readOnly = computed(() => props.readOnly ?? false);
const addDisabled = computed(() => readOnly.value || !(props.canAdd ?? true));

interface PaletteGroup {
  key: string;
  label: string;
  items: TaskStatusNode[];
}

const groups = computed((): PaletteGroup[] => {
  const byColumn = new Map<string, TaskStatusNode[]>();
  const unbound: TaskStatusNode[] = [];

  for (const status of props.statuses) {
    const label = status.column_name?.trim();
    if (!label) {
      unbound.push(status);
      continue;
    }
    const bucket = byColumn.get(label) ?? [];
    bucket.push(status);
    byColumn.set(label, bucket);
  }

  const result: PaletteGroup[] = Array.from(byColumn.entries()).map(([label, items]) => ({
    key: label,
    label,
    items: [...items].sort((left, right) => (left.position ?? 0) - (right.position ?? 0)),
  }));

  if (unbound.length) {
    result.push({
      key: "__unbound__",
      label: "",
      items: unbound,
    });
  }

  return result;
});

function nodeId(status: TaskStatusNode): string {
  return statusNodeKey(status);
}

function isSelected(status: TaskStatusNode): boolean {
  return props.selectedId === nodeId(status);
}

function onDragStart(event: DragEvent, status: TaskStatusNode) {
  if (readOnly.value) {
    event.preventDefault();
    return;
  }
  event.dataTransfer?.setData("application/cadence-status", nodeId(status));
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = "move";
  }
}
</script>

<template>
  <aside class="status-flow-palette" role="region" :aria-label="$t('settings.statusFlowPaletteTitle')">
    <header class="status-flow-palette-header">
      <p class="status-flow-palette-eyebrow">{{ $t("settings.statusFlowPaletteEyebrow") }}</p>
      <h3 class="status-flow-palette-title">{{ $t("settings.statusFlowPaletteTitle") }}</h3>
      <p class="status-flow-palette-hint">{{ $t("settings.statusFlowPaletteHint") }}</p>
    </header>

    <div v-if="statuses.length === 0" class="status-flow-palette-empty">
      {{ $t("settings.statusFlowPaletteEmpty") }}
    </div>

    <div v-else class="status-flow-palette-groups">
      <section v-for="group in groups" :key="group.key" class="status-flow-palette-group">
        <h4 v-if="group.label" class="status-flow-palette-group-title">{{ group.label }}</h4>
        <h4 v-else class="status-flow-palette-group-title status-flow-palette-group-title-muted">
          {{ $t("settings.statusFlowColumnNone") }}
        </h4>

        <ul class="status-flow-palette-list">
          <li
            v-for="(status, index) in group.items"
            :key="nodeId(status)"
            class="scheme-stagger-item"
            :style="{ '--scheme-item-delay': `${index * 40}ms` }"
          >
            <button
              class="status-flow-palette-item"
              :class="{ 'status-flow-palette-item-selected': isSelected(status) }"
              type="button"
              :draggable="!readOnly"
              @click="emit('select', nodeId(status))"
              @dragstart="onDragStart($event, status)"
            >
              <span class="status-flow-palette-dot" :style="columnDotStyle(status.color)" />
              <span class="status-flow-palette-item-copy">
                <span class="status-flow-palette-item-name">{{ status.name }}</span>
                <span v-if="status.is_initial || status.is_terminal" class="status-flow-palette-badges">
                  <span v-if="status.is_initial" class="status-flow-palette-badge">
                    {{ $t("settings.statusFlowInitial") }}
                  </span>
                  <span
                    v-if="status.is_terminal"
                    class="status-flow-palette-badge status-flow-palette-badge-terminal"
                  >
                    {{ $t("settings.statusFlowTerminal") }}
                  </span>
                </span>
              </span>
            </button>
          </li>
        </ul>
      </section>
    </div>

    <footer class="status-flow-palette-footer">
      <button
        class="status-flow-palette-action"
        type="button"
        :disabled="addDisabled"
        :title="
          readOnly
            ? $t('settings.statusFlowLockedHint')
            : !props.canAdd
              ? $t('settings.statusFlowLimitTitle', { max: props.maxStatuses ?? 20 })
              : undefined
        "
        @click="emit('add')"
      >
        <PlusIcon class="icon-sm" />
        <span>{{ $t("settings.statusFlowAdd") }}</span>
      </button>
    </footer>
  </aside>
</template>
