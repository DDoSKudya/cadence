<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { ChevronDownIcon, XMarkIcon } from "@heroicons/vue/24/outline";

import type { TaskStatusNode } from "@/features/settings/task-status-graph";
import { columnDotStyle } from "@/lib/column-color";
import { statusDisplayName } from "@/lib/workflow-labels";

const props = defineProps<{
  modelValue: number[];
  statuses: TaskStatusNode[];
  readOnly?: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [number[]];
}>();

const readOnly = computed(() => props.readOnly ?? false);
const draftIds = ref<number[]>([]);
const menuOpen = ref(false);
const rootRef = ref<HTMLElement | null>(null);

watch(
  () => props.modelValue,
  (value) => {
    draftIds.value = [...value];
  },
  { immediate: true },
);

const sortedStatuses = computed(() =>
  [...props.statuses]
    .filter((status) => status.id !== null)
    .sort((left, right) => (left.position ?? 0) - (right.position ?? 0)),
);

const attachedStatuses = computed(() =>
  sortedStatuses.value.filter(
    (status) => status.id !== null && draftIds.value.includes(status.id),
  ),
);

const availableStatuses = computed(() =>
  sortedStatuses.value.filter(
    (status) => status.id !== null && !draftIds.value.includes(status.id),
  ),
);

function emitIds(next: Set<number>) {
  draftIds.value = Array.from(next).sort((left, right) => left - right);
  emit("update:modelValue", draftIds.value);
}

function addStatus(statusId: number) {
  if (readOnly.value) {
    return;
  }
  const next = new Set(draftIds.value);
  next.add(statusId);
  emitIds(next);
  menuOpen.value = false;
}

function removeStatus(statusId: number) {
  if (readOnly.value) {
    return;
  }
  const next = new Set(draftIds.value);
  next.delete(statusId);
  emitIds(next);
}

function toggleMenu() {
  if (readOnly.value || sortedStatuses.value.length === 0) {
    return;
  }
  menuOpen.value = !menuOpen.value;
}

function onDocumentClick(event: MouseEvent) {
  if (!menuOpen.value || !rootRef.value) {
    return;
  }
  if (!rootRef.value.contains(event.target as Node)) {
    menuOpen.value = false;
  }
}

onMounted(() => {
  document.addEventListener("click", onDocumentClick);
});

onUnmounted(() => {
  document.removeEventListener("click", onDocumentClick);
});
</script>

<template>
  <section ref="rootRef" class="status-multi-select-wrap">
    <div
      class="status-multi-select"
      :class="{
        'status-multi-select-open': menuOpen,
        'status-multi-select-readonly': readOnly,
        'status-multi-select-empty': attachedStatuses.length === 0,
      }"
    >
      <button
        class="status-multi-select-control"
        type="button"
        :disabled="readOnly || sortedStatuses.length === 0"
        @click="toggleMenu"
      >
        <div class="status-multi-select-value">
          <span v-if="attachedStatuses.length === 0" class="status-multi-select-placeholder">
            {{ $t("settings.columnStatusBindingsPlaceholder") }}
          </span>
          <span
            v-for="status in attachedStatuses"
            :key="status.id ?? status.name"
            class="status-multi-select-chip"
          >
            <span class="status-multi-select-chip-dot" :style="columnDotStyle(status.color)" />
            <span class="status-multi-select-chip-label">{{ statusDisplayName(status) }}</span>
            <button
              v-if="!readOnly"
              class="status-multi-select-chip-remove"
              type="button"
              :aria-label="$t('common.remove')"
              @click.stop="status.id !== null && removeStatus(status.id)"
            >
              <XMarkIcon class="icon-xs" />
            </button>
          </span>
        </div>
        <ChevronDownIcon v-if="!readOnly" class="status-multi-select-chevron icon-sm" />
      </button>

      <ul v-if="menuOpen && !readOnly" class="status-multi-select-menu" role="listbox">
        <li v-if="availableStatuses.length === 0" class="status-multi-select-menu-empty">
          {{ $t("settings.columnStatusBindingsAllSelected") }}
        </li>
        <li v-for="status in availableStatuses" :key="status.id ?? status.name">
          <button
            class="status-multi-select-option"
            type="button"
            role="option"
            @click="status.id !== null && addStatus(status.id)"
          >
            <span class="status-multi-select-chip-dot" :style="columnDotStyle(status.color)" />
            <span>{{ statusDisplayName(status) }}</span>
          </button>
        </li>
      </ul>
    </div>

    <p v-if="sortedStatuses.length === 0" class="column-status-bindings-empty">
      {{ $t("settings.columnStatusBindingsNoStatuses") }}
    </p>
  </section>
</template>
