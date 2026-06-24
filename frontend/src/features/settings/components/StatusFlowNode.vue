<script setup lang="ts">
import { computed, ref } from "vue";
import { Handle, Position } from "@vue-flow/core";
import { XMarkIcon } from "@heroicons/vue/24/outline";

import { columnDotStyle, colorToHex } from "@/lib/column-color";

interface StatusFlowNodeData {
  name?: string;
  color?: string;
  slug?: string;
  columnName?: string | null;
  isInitial?: boolean;
  isTerminal?: boolean;
  creationOnly?: boolean;
  readOnly?: boolean;
  hasCancelOut?: boolean;
  isCancelNode?: boolean;
  onRename?: (name: string) => void;
  onDelete?: () => void;
}

const props = defineProps<{
  id: string;
  data: StatusFlowNodeData;
  selected?: boolean;
}>();

const editing = ref(false);
const draftName = ref("");

const readOnly = computed(() => Boolean(props.data.readOnly));
const name = computed(() => String(props.data.name ?? ""));
const color = computed(() => String(props.data.color ?? "slate"));
const accentStyle = computed(() => ({
  background: `linear-gradient(180deg, ${colorToHex(color.value)} 0%, color-mix(in srgb, ${colorToHex(color.value)} 72%, #0f172a) 100%)`,
}));

async function startEdit() {
  if (readOnly.value) {
    return;
  }
  draftName.value = name.value;
  editing.value = true;
}

function commitEdit() {
  const trimmed = draftName.value.trim();
  if (trimmed && typeof props.data.onRename === "function") {
    props.data.onRename(trimmed);
  }
  editing.value = false;
}

function cancelEdit() {
  editing.value = false;
}

function removeNode() {
  if (readOnly.value || typeof props.data.onDelete !== "function") {
    return;
  }
  props.data.onDelete();
}
</script>

<template>
  <div
    class="status-node"
    :class="{
      'status-node-selected': selected,
      'status-node-readonly': readOnly,
      'status-node-cancel': data.isCancelNode,
      'status-node-terminal': data.isTerminal,
    }"
    :style="{ '--status-node-accent': colorToHex(color) }"
  >
    <span class="status-node-accent" :style="accentStyle" />

    <Handle
      id="in"
      class="status-node-handle status-node-handle-in"
      type="target"
      :position="Position.Left"
      :connectable="!readOnly"
    />

    <Handle
      v-if="data.isCancelNode"
      id="cancel-in"
      class="status-node-handle status-node-handle-cancel-in"
      type="target"
      :position="Position.Top"
      :connectable="!readOnly"
    />

    <div class="status-node-body" @dblclick="startEdit">
      <div v-if="data.isInitial || data.isTerminal || data.creationOnly" class="status-node-badges">
        <span v-if="data.isInitial" class="status-node-badge status-node-badge-initial">
          {{ $t("settings.statusFlowInitial") }}
        </span>
        <span v-if="data.isTerminal" class="status-node-badge status-node-badge-terminal">
          {{ $t("settings.statusFlowTerminal") }}
        </span>
        <span v-if="data.creationOnly" class="status-node-badge status-node-badge-muted">
          {{ $t("settings.statusRuleCreationOnly") }}
        </span>
      </div>

      <input
        v-if="editing"
        v-model="draftName"
        class="status-node-input"
        type="text"
        maxlength="100"
        @keydown.enter.prevent="commitEdit"
        @keydown.esc.prevent="cancelEdit"
        @blur="commitEdit"
      />
      <p v-else class="status-node-name">{{ name }}</p>

      <p v-if="data.columnName" class="status-node-column">
        <span class="status-node-column-dot" :style="columnDotStyle(color)" />
        {{ $t("settings.statusFlowColumn", { column: data.columnName }) }}
      </p>
    </div>

    <Handle
      id="out"
      class="status-node-handle status-node-handle-out"
      type="source"
      :position="Position.Right"
      :connectable="!readOnly"
    />

    <Handle
      v-if="data.hasCancelOut"
      id="cancel-out"
      class="status-node-handle status-node-handle-cancel-out"
      type="source"
      :position="Position.Bottom"
      :connectable="!readOnly"
    />

    <button
      v-if="!readOnly"
      class="status-node-remove"
      type="button"
      :aria-label="$t('common.delete')"
      @click.stop="removeNode"
    >
      <XMarkIcon class="icon-xs" />
    </button>
  </div>
</template>
