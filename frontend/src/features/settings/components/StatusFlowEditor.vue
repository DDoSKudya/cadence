<script setup lang="ts">
import { computed, markRaw, nextTick, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  VueFlow,
  MarkerType,
  type Connection,
  type EdgeChange,
  type NodeChange,
  type NodeDragEvent,
} from "@vue-flow/core";
import { Background } from "@vue-flow/background";
import { Controls } from "@vue-flow/controls";

import { saveTaskStatusGraph, saveTaskStatusLayout } from "@/features/settings/api";
import { useActionFeedback } from "@/composables/useActionFeedback";
import type { SettingsColumn } from "@/features/settings/types";
import type {
  TaskStatusGraph,
  TaskStatusNode,
  TaskStatusTransition,
} from "@/features/settings/task-status-graph";
import { statusNodeKey, isTerminalStatus } from "@/features/settings/task-status-graph";
import { colorToHex } from "@/lib/column-color";
import { statusDisplayName } from "@/lib/workflow-labels";

import StatusFlowInspector from "./StatusFlowInspector.vue";
import StatusFlowNode from "./StatusFlowNode.vue";
import StatusFlowPalette from "./StatusFlowPalette.vue";

import "@vue-flow/core/dist/style.css";
import "@vue-flow/core/dist/theme-default.css";
import "@vue-flow/controls/dist/style.css";

interface FlowNode {
  id: string;
  type?: string;
  position: { x: number; y: number };
  data: Record<string, unknown>;
  draggable?: boolean;
  connectable?: boolean;
}

interface FlowEdge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
  type?: string;
  markerEnd?: string | { type: MarkerType; color?: string; width?: number; height?: number };
  style?: Record<string, string | number>;
  pathOptions?: { borderRadius?: number; offset?: number };
  interactionWidth?: number;
  label?: string;
  labelStyle?: Record<string, string | number>;
  selectable?: boolean;
  deletable?: boolean;
  data?: { isCancel?: boolean };
}

const STATUS_COLORS = ["slate", "blue", "amber", "indigo", "green", "violet", "red"] as const;

const props = defineProps<{
  graph: TaskStatusGraph;
  columns: SettingsColumn[];
  readOnly?: boolean;
  maxStatuses?: number;
}>();

const emit = defineEmits<{
  saved: [TaskStatusGraph];
}>();

const { t } = useI18n();
const feedback = useActionFeedback();
const structureLocked = computed(() => props.readOnly ?? false);
const saving = ref(false);
const layoutSaving = ref(false);
const layoutSaved = ref(false);
const layoutError = ref("");
const formError = ref("");
const nodes = ref<FlowNode[]>([]);
const edges = ref<FlowEdge[]>([]);
const draftStatuses = ref<TaskStatusNode[]>([]);
const draftTransitions = ref<TaskStatusTransition[]>([]);
const nextTempId = ref(1);
const selectedNodeId = ref<string | null>(null);
const selectedEdgeId = ref<string | null>(null);
const flowRef = ref<{
  fitView: (options?: { padding?: number; duration?: number }) => void;
  screenToFlowCoordinate: (position: { x: number; y: number }) => { x: number; y: number };
} | null>(null);

const flowStatuses = computed(() => draftStatuses.value.filter((status) => status.on_flow));
const paletteStatuses = computed(() => draftStatuses.value.filter((status) => !status.on_flow));

const nodeTypes = {
  status: markRaw(StatusFlowNode),
} as Record<string, object>;

const defaultEdgeOptions = {
  type: "smoothstep",
  pathOptions: { borderRadius: 22, offset: 36 },
  markerEnd: {
    type: MarkerType.ArrowClosed,
    color: "var(--status-flow-edge-color)",
    width: 18,
    height: 18,
  },
  style: {
    strokeWidth: 2.5,
    stroke: "var(--status-flow-edge-color)",
  },
  interactionWidth: 16,
};

const cancelNodeId = computed(() => {
  const cancel = flowStatuses.value.find(
    (status) => status.slug === "cancel" || status.name.toLowerCase() === "cancel",
  );
  return cancel ? nodeIdForStatus(cancel) : null;
});

const cancelSourceIds = computed(() => {
  const targetId = cancelNodeId.value;
  if (!targetId) {
    return new Set<string>();
  }
  return new Set(
    draftTransitions.value
      .filter((transition) => String(transition.to_status_id) === targetId)
      .map((transition) => String(transition.from_status_id)),
  );
});

const statusLimit = computed(() => props.maxStatuses ?? props.graph.limits?.max_task_statuses ?? 20);
const canAddStatus = computed(
  () => !structureLocked.value && draftStatuses.value.length < statusLimit.value,
);

const selectedStatus = computed(() =>
  flowStatuses.value.find((status) => nodeIdForStatus(status) === selectedNodeId.value) ?? null,
);

const selectedTransition = computed(() => {
  const edge = edges.value.find((item) => item.id === selectedEdgeId.value);
  if (!edge) {
    return null;
  }
  return (
    draftTransitions.value.find(
      (transition) =>
        String(transition.from_status_id) === edge.source &&
        String(transition.to_status_id) === edge.target,
    ) ?? {
      from_status_id: edge.source,
      to_status_id: edge.target,
      rules: {},
    }
  );
});

const selectedTransitionLabel = computed(() => {
  if (!selectedTransition.value) {
    return "";
  }
  const from = draftStatuses.value.find(
    (status) => nodeIdForStatus(status) === String(selectedTransition.value?.from_status_id),
  );
  const to = draftStatuses.value.find(
    (status) => nodeIdForStatus(status) === String(selectedTransition.value?.to_status_id),
  );
  return `${from?.name ?? "?"} → ${to?.name ?? "?"}`;
});

function nodeIdForStatus(status: TaskStatusNode): string {
  return statusNodeKey(status);
}

function normalizeStatus(status: TaskStatusNode): TaskStatusNode {
  return {
    ...status,
    on_flow: status.on_flow ?? false,
    is_terminal: status.is_terminal ?? false,
    rules: status.rules ?? {},
    column_id: status.column_id ?? null,
    column_name: status.column_name ?? null,
  };
}

function flowNodeForStatus(status: TaskStatusNode): FlowNode {
  return {
    id: nodeIdForStatus(status),
    type: "status",
    position: { x: status.layout_x, y: status.layout_y },
    data: nodeDataForStatus(status),
    draggable: true,
    connectable: !structureLocked.value,
  };
}

function syncNodesFromFlow() {
  nodes.value = flowStatuses.value.map((status) => flowNodeForStatus(status)) as FlowNode[];
}

function nodeDataForStatus(status: TaskStatusNode) {
  const nodeId = nodeIdForStatus(status);
  const isCancel =
    status.slug === "cancel" || status.name.trim().toLowerCase() === "cancel";
  return {
    name: statusDisplayName(status),
    color: status.color,
    slug: status.slug,
    columnName: status.column_name,
    isInitial: status.is_initial,
    isTerminal: isTerminalStatus(status),
    creationOnly: Boolean(status.rules.creation_only),
    hasCancelOut: cancelSourceIds.value.has(nodeId),
    isCancelNode: isCancel,
    readOnly: structureLocked.value,
    onRename: (name: string) => updateNodeName(nodeId, name),
    onDelete: () => removeStatus(nodeId),
  };
}

function edgeColorForSource(sourceNodeId: string): string {
  const status = draftStatuses.value.find(
    (item) => nodeIdForStatus(item) === sourceNodeId,
  );
  return colorToHex(status?.color ?? "slate");
}

function edgeStyleForTransition(
  transition: TaskStatusTransition,
): Record<string, string | number> {
  const sourceColor = edgeColorForSource(String(transition.from_status_id));
  const isCancel =
    cancelNodeId.value !== null &&
    String(transition.to_status_id) === cancelNodeId.value;
  if (isCancel) {
    return {
      strokeWidth: 1.75,
      stroke: sourceColor,
      strokeDasharray: "6 4",
      opacity: 0.88,
    };
  }
  return {
    strokeWidth: 2.25,
    stroke: sourceColor,
  };
}

function edgeMarkerForTransition(transition: TaskStatusTransition) {
  const sourceColor = edgeColorForSource(String(transition.from_status_id));
  return {
    type: MarkerType.ArrowClosed,
    color: sourceColor,
    width: 18,
    height: 18,
  };
}

function handlesForTransition(transition: TaskStatusTransition) {
  const isCancel =
    cancelNodeId.value !== null &&
    String(transition.to_status_id) === cancelNodeId.value;
  if (!isCancel) {
    return {};
  }
  return {
    sourceHandle: "cancel-out",
    targetHandle: "cancel-in",
  };
}

function cancelEdgeOffset(transition: TaskStatusTransition): number {
  const targetId = cancelNodeId.value;
  if (!targetId) {
    return 36;
  }
  const cancelTransitions = draftTransitions.value.filter(
    (item) => String(item.to_status_id) === targetId,
  );
  const index = cancelTransitions.findIndex(
    (item) =>
      String(item.from_status_id) === String(transition.from_status_id) &&
      String(item.to_status_id) === String(transition.to_status_id),
  );
  return 28 + Math.max(index, 0) * 22;
}

function edgeFromTransition(transition: TaskStatusTransition, index: number): FlowEdge {
  const isCancel =
    cancelNodeId.value !== null &&
    String(transition.to_status_id) === cancelNodeId.value;
  return {
    id: `edge-${index}-${transition.from_status_id}-${transition.to_status_id}`,
    source: String(transition.from_status_id),
    target: String(transition.to_status_id),
    type: "smoothstep",
    ...handlesForTransition(transition),
    pathOptions: isCancel
      ? { borderRadius: 28, offset: cancelEdgeOffset(transition) }
      : { borderRadius: 22, offset: 36 },
    markerEnd: edgeMarkerForTransition(transition),
    style: edgeStyleForTransition(transition),
    interactionWidth: 16,
    selectable: !structureLocked.value,
    deletable: !structureLocked.value,
    data: { isCancel },
  };
}

function syncFromGraph(graph: TaskStatusGraph) {
  draftStatuses.value = graph.statuses.map((status) => normalizeStatus({ ...status }));
  draftTransitions.value = graph.transitions.map((transition) => ({
    ...transition,
    rules: transition.rules ?? {},
  }));
  syncNodesFromFlow();
  edges.value = draftTransitions.value.map(edgeFromTransition) as FlowEdge[];
  selectedNodeId.value = null;
  selectedEdgeId.value = null;
  if (flowStatuses.value.length) {
    void nextTick(() => {
      flowRef.value?.fitView({ padding: 0.22, duration: 250 });
    });
  }
}

watch(
  () => props.graph,
  (graph) => {
    syncFromGraph(graph);
  },
  { immediate: true, deep: true },
);

watch(structureLocked, (locked) => {
  nodes.value = nodes.value.map((node) => ({
    ...node,
    draggable: true,
    connectable: !locked,
    data: {
      ...node.data,
      readOnly: locked,
    },
  })) as FlowNode[];
  edges.value = edges.value.map((edge) => ({
    ...edge,
    selectable: !locked,
    deletable: !locked,
  })) as FlowEdge[];
});

function onConnect(connection: Connection) {
  if (structureLocked.value || !connection.source || !connection.target) {
    return;
  }
  if (connection.source === connection.target) {
    return;
  }
  const exists = edges.value.some(
    (edge) => edge.source === connection.source && edge.target === connection.target,
  );
  if (exists) {
    return;
  }
  const transition: TaskStatusTransition = {
    from_status_id: connection.source,
    to_status_id: connection.target,
    rules: {},
  };
  draftTransitions.value = [...draftTransitions.value, transition];
  rebuildEdges();
  refreshAllNodes();
}

function focusNode(nodeId: string) {
  selectedNodeId.value = nodeId;
  selectedEdgeId.value = null;
  void nextTick(() => {
    flowRef.value?.fitView({ padding: 0.45, duration: 300 });
  });
}

function placeOnCanvas(statusKey: string, position: { x: number; y: number }) {
  if (structureLocked.value) {
    return;
  }
  const status = draftStatuses.value.find((item) => nodeIdForStatus(item) === statusKey);
  if (!status || status.on_flow) {
    return;
  }
  status.on_flow = true;
  status.layout_x = position.x;
  status.layout_y = position.y;
  nodes.value = [...nodes.value, flowNodeForStatus(status)] as FlowNode[];
  focusNode(statusKey);
}

function onCanvasDragOver(event: DragEvent) {
  if (structureLocked.value) {
    return;
  }
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "move";
  }
}

function onCanvasDrop(event: DragEvent) {
  if (structureLocked.value) {
    return;
  }
  event.preventDefault();
  const statusKey = event.dataTransfer?.getData("application/cadence-status");
  if (!statusKey || !flowRef.value) {
    return;
  }
  const position = flowRef.value.screenToFlowCoordinate({
    x: event.clientX,
    y: event.clientY,
  });
  placeOnCanvas(statusKey, position);
}

function onPaletteSelect(nodeId: string) {
  const status = draftStatuses.value.find((item) => nodeIdForStatus(item) === nodeId);
  if (status?.on_flow) {
    focusNode(nodeId);
  }
}

function onNodesChange(changes: NodeChange[]) {
  for (const change of changes) {
    if (change.type === "position" && change.position) {
      const status = draftStatuses.value.find(
        (item) => nodeIdForStatus(item) === change.id,
      );
      if (status) {
        status.layout_x = change.position.x;
        status.layout_y = change.position.y;
      }
    }
    if (change.type === "remove" && !structureLocked.value) {
      removeStatus(change.id);
    }
  }
}

function onEdgesChange(changes: EdgeChange[]) {
  let removed = false;
  for (const change of changes) {
    if (change.type === "remove") {
      removed = true;
      const edge = edges.value.find((item) => item.id === change.id);
      if (edge) {
        draftTransitions.value = draftTransitions.value.filter(
          (transition) =>
            !(
              String(transition.from_status_id) === edge.source &&
              String(transition.to_status_id) === edge.target
            ),
        );
      }
      if (selectedEdgeId.value === change.id) {
        selectedEdgeId.value = null;
      }
    }
  }
  if (removed) {
    rebuildEdges();
    refreshAllNodes();
  }
}

function onNodeClick(event: { node: { id: string } }) {
  selectedNodeId.value = event.node.id;
  selectedEdgeId.value = null;
}

function onEdgeClick(event: { edge: { id: string } }) {
  selectedEdgeId.value = event.edge.id;
  selectedNodeId.value = null;
}

function updateNodeName(nodeId: string, name: string) {
  const status = draftStatuses.value.find((item) => nodeIdForStatus(item) === nodeId);
  if (!status) {
    return;
  }
  status.name = name.trim();
  refreshAllNodes();
}

function updateStatus(nextStatus: TaskStatusNode) {
  const nodeId = nodeIdForStatus(nextStatus);
  draftStatuses.value = draftStatuses.value.map((status) =>
    nodeIdForStatus(status) === nodeId ? normalizeStatus(nextStatus) : status,
  );
  refreshAllNodes();
}

function updateTransition(nextTransition: TaskStatusTransition) {
  draftTransitions.value = draftTransitions.value.map((transition) =>
    String(transition.from_status_id) === String(nextTransition.from_status_id) &&
    String(transition.to_status_id) === String(nextTransition.to_status_id)
      ? nextTransition
      : transition,
  );
}

function refreshAllNodes() {
  nodes.value = nodes.value.map((node) => {
    const status = draftStatuses.value.find((item) => nodeIdForStatus(item) === node.id);
    if (!status) {
      return node;
    }
    return {
      ...node,
      data: nodeDataForStatus(status),
    };
  }) as FlowNode[];
}

function rebuildEdges() {
  edges.value = draftTransitions.value.map(edgeFromTransition) as FlowEdge[];
}

function addStatus() {
  if (!canAddStatus.value) {
    return;
  }
  const clientKey = `tmp-${nextTempId.value++}`;
  const index = flowStatuses.value.length;
  const status = normalizeStatus({
    id: null,
    client_key: clientKey,
    name: t("settings.statusFlowNewName"),
    color: STATUS_COLORS[index % STATUS_COLORS.length],
    layout_x: 60 + index * 280,
    layout_y: 60 + (index % 2) * 24,
    on_flow: true,
    is_initial: flowStatuses.value.length === 0,
    is_terminal: false,
    column_id: null,
    column_name: null,
    rules: {},
  });
  draftStatuses.value = [...draftStatuses.value, status];
  nodes.value = [...nodes.value, flowNodeForStatus(status)] as FlowNode[];
  focusNode(clientKey);
}

function removeStatus(nodeId: string) {
  if (structureLocked.value) {
    return;
  }
  const status = draftStatuses.value.find((item) => nodeIdForStatus(item) === nodeId);
  if (!status) {
    return;
  }

  draftTransitions.value = draftTransitions.value.filter(
    (transition) =>
      String(transition.from_status_id) !== nodeId &&
      String(transition.to_status_id) !== nodeId,
  );
  nodes.value = nodes.value.filter((node) => node.id !== nodeId);

  if (status.id !== null) {
    status.on_flow = false;
    status.layout_x = 0;
    status.layout_y = 0;
  } else {
    draftStatuses.value = draftStatuses.value.filter(
      (item) => nodeIdForStatus(item) !== nodeId,
    );
  }

  rebuildEdges();
  refreshAllNodes();
  if (selectedNodeId.value === nodeId) {
    selectedNodeId.value = null;
  }
}

let layoutSaveTimer: ReturnType<typeof setTimeout> | null = null;
let layoutSavedTimer: ReturnType<typeof setTimeout> | null = null;

function applyLayoutFromServer(saved: TaskStatusGraph) {
  for (const serverStatus of saved.statuses) {
    const local = draftStatuses.value.find((status) => status.id === serverStatus.id);
    if (!local) {
      continue;
    }
    local.layout_x = serverStatus.layout_x;
    local.layout_y = serverStatus.layout_y;
  }
  nodes.value = nodes.value.map((node) => {
    const status = draftStatuses.value.find((item) => nodeIdForStatus(item) === node.id);
    if (!status) {
      return node;
    }
    return {
      ...node,
      position: { x: status.layout_x, y: status.layout_y },
    };
  }) as FlowNode[];
}

function scheduleLayoutSave() {
  if (layoutSaving.value) {
    return;
  }
  if (layoutSaveTimer) {
    clearTimeout(layoutSaveTimer);
  }
  layoutSaveTimer = setTimeout(() => {
    void persistLayout();
  }, 350);
}

async function persistLayout() {
  const payload = flowStatuses.value
    .filter((status) => status.id !== null)
    .map((status) => ({
      id: status.id as number,
      layout_x: status.layout_x,
      layout_y: status.layout_y,
    }));
  if (!payload.length || layoutSaving.value) {
    return;
  }

  layoutSaving.value = true;
  layoutError.value = "";
  try {
    const saved = await saveTaskStatusLayout(payload);
    applyLayoutFromServer(saved);
    emit("saved", saved);
    layoutSaved.value = true;
    if (layoutSavedTimer) {
      clearTimeout(layoutSavedTimer);
    }
    layoutSavedTimer = setTimeout(() => {
      layoutSaved.value = false;
    }, 1800);
  } catch (saveError) {
    feedback.fromError(saveError, "errors.saveStatusWorkflow");
  } finally {
    layoutSaving.value = false;
  }
}

function onNodeDragStop(event: NodeDragEvent) {
  const status = draftStatuses.value.find(
    (item) => nodeIdForStatus(item) === event.node.id,
  );
  if (!status) {
    return;
  }
  status.layout_x = event.node.position.x;
  status.layout_y = event.node.position.y;
  scheduleLayoutSave();
}

function buildPayload() {
  return {
    statuses: flowStatuses.value.map((status, index) => ({
      id: status.id,
      client_key: status.client_key,
      name: status.name,
      color: status.color,
      layout_x: status.layout_x,
      layout_y: status.layout_y,
      on_flow: true,
      is_initial: status.is_initial,
      is_terminal: status.is_terminal,
      column_id: status.column_id,
      rules: status.rules ?? {},
      position: index,
    })),
    transitions: draftTransitions.value.map((transition) => ({
      from_status_id: transition.from_status_id,
      to_status_id: transition.to_status_id,
      rules: transition.rules ?? {},
    })),
  };
}

async function persistGraph() {
  saving.value = true;
  formError.value = "";
  layoutError.value = "";
  try {
    const saved = await saveTaskStatusGraph(buildPayload());
    emit("saved", saved);
    syncFromGraph(saved);
    feedback.successKey("toast.statusWorkflowSaved");
  } catch (saveError) {
    feedback.fromError(saveError, "errors.saveStatusWorkflow");
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <section
    class="settings-panel status-flow-panel"
    role="region"
    :aria-label="$t('settings.statusWorkflowTitle')"
  >
    <header class="settings-panel-header status-flow-header">
      <div class="status-flow-header-copy">
        <p class="drawer-eyebrow">{{ $t("settings.statusWorkflowEyebrow") }}</p>
        <h2 class="settings-panel-title">{{ $t("settings.statusesTab") }}</h2>
        <p class="status-flow-header-hint">
          {{
            structureLocked
              ? $t("settings.statusFlowLockedLayoutHint")
              : $t("settings.statusFlowConnectHint")
          }}
        </p>
      </div>
    </header>

    <div class="settings-panel-body status-flow-body">
      <Transition name="scheme-alert-slide">
        <p v-if="formError" key="error" class="alert-error status-flow-error">{{ formError }}</p>
      </Transition>

      <Transition name="scheme-alert-slide" mode="out-in">
        <p
          v-if="layoutSaving"
          key="saving"
          class="status-flow-layout-status"
        >
          {{ $t("settings.statusFlowLayoutSaving") }}
        </p>
        <p
          v-else-if="layoutError"
          key="layout-error"
          class="alert-error status-flow-error"
        >
          {{ layoutError }}
        </p>
        <p
          v-else-if="layoutSaved"
          key="saved"
          class="status-flow-layout-status status-flow-layout-status-saved"
        >
          {{ $t("settings.statusFlowLayoutSaved") }}
        </p>
      </Transition>

      <div class="status-flow-workspace">
      <StatusFlowPalette
        :statuses="paletteStatuses"
        :selected-id="selectedNodeId"
        :read-only="structureLocked"
        :can-add="canAddStatus"
        :max-statuses="props.maxStatuses"
        @select="onPaletteSelect"
        @add="addStatus"
      />

      <div
        class="status-flow-canvas-wrap"
        @dragover="onCanvasDragOver"
        @drop="onCanvasDrop"
      >
        <div class="status-flow-legend">
          <span class="status-flow-legend-item">
            <span class="status-flow-legend-line status-flow-legend-line-main" />
            {{ $t("settings.statusFlowLegendMain") }}
          </span>
          <span class="status-flow-legend-item">
            <span class="status-flow-legend-line status-flow-legend-line-cancel" />
            {{ $t("settings.statusFlowLegendCancel") }}
          </span>
        </div>

        <VueFlow
          ref="flowRef"
          v-model:nodes="nodes"
          v-model:edges="edges"
          :node-types="nodeTypes"
          :default-edge-options="defaultEdgeOptions"
          :nodes-draggable="true"
          :nodes-connectable="!structureLocked"
          :elements-selectable="true"
          :delete-key-code="structureLocked ? null : 'Delete'"
          :min-zoom="0.35"
          :max-zoom="1.4"
          fit-view-on-init
          class="status-flow-canvas"
          @connect="onConnect"
          @nodes-change="onNodesChange"
          @edges-change="onEdgesChange"
          @node-drag-stop="onNodeDragStop"
          @node-click="onNodeClick"
          @edge-click="onEdgeClick"
          @pane-click="selectedNodeId = null; selectedEdgeId = null"
        >
          <Background :gap="28" :size="1.5" pattern-color="var(--status-flow-grid-color)" />
          <Controls
            class="status-flow-controls"
            :show-interactive="false"
            position="bottom-right"
          />
        </VueFlow>

        <div v-if="flowStatuses.length === 0" class="status-flow-empty">
          <p>
            {{
              paletteStatuses.length
                ? $t("settings.statusFlowDragHint")
                : $t("settings.statusFlowEmpty")
            }}
          </p>
        </div>
      </div>

      <aside class="status-flow-inspector-shell">
        <div class="status-flow-inspector-body">
          <Transition name="scheme-inspector-swap" mode="out-in">
            <StatusFlowInspector
              v-if="selectedStatus || selectedTransition"
              key="inspector"
              :status="selectedStatus"
              :transition="selectedEdgeId ? selectedTransition : null"
              :transition-label="selectedTransitionLabel"
              :columns="columns"
              :read-only="structureLocked"
              @update-status="updateStatus"
              @update-transition="updateTransition"
            />

            <div
              v-else
              key="empty"
              class="status-flow-inspector status-flow-inspector-empty"
            >
              <p class="status-flow-inspector-eyebrow">{{ $t("settings.statusFlowInspectorStatus") }}</p>
              <h3 class="status-flow-inspector-title">{{ $t("settings.statusFlowInspectorEmptyTitle") }}</h3>
              <p class="status-flow-inspector-empty-text">{{ $t("settings.statusFlowInspectorEmptyText") }}</p>
            </div>
          </Transition>
        </div>

        <footer v-if="!structureLocked" class="status-flow-inspector-footer">
          <button
            class="btn-primary status-flow-save-btn disabled:opacity-60"
            type="button"
            :disabled="saving || flowStatuses.length === 0"
            @click="persistGraph"
          >
            {{ saving ? $t("common.saving") : $t("settings.statusWorkflowSave") }}
          </button>
        </footer>
      </aside>
    </div>
    </div>
  </section>
</template>
