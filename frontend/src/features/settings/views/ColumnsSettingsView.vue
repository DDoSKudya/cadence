<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  ArrowPathIcon,
  Bars3Icon,
  PlusIcon,
  QueueListIcon,
  Squares2X2Icon,
  TagIcon,
  ViewColumnsIcon,
} from "@heroicons/vue/24/outline";

import ColumnPanel from "@/features/settings/components/ColumnPanel.vue";
import ColumnWorkflowMatrix from "@/features/settings/components/ColumnWorkflowMatrix.vue";
import SchemeCreatePanel from "@/features/settings/components/SchemeCreatePanel.vue";
import SchemePicker from "@/features/settings/components/SchemePicker.vue";
import TagsSettingsPanel from "@/features/settings/components/TagsSettingsPanel.vue";
import draggable from "vuedraggable";
import { useI18n } from "vue-i18n";
import {
  deleteBoardScheme,
  fetchBoardSchemes,
  fetchColumnWorkflow,
  fetchColumns,
  fetchTaskStatusGraph,
  reorderColumns,
  switchBoardScheme,
} from "@/features/settings/api";
import type { SchemeSwitchResult } from "@/features/settings/api";
import { columnDisplayName } from "@/features/settings/scheme-display";
import { DEFAULT_BOARD_LIMITS, type BoardLimits } from "@/features/settings/constants";
import type { BoardScheme, SettingsColumn } from "@/features/settings/types";
import type { TaskStatusGraph } from "@/features/settings/task-status-graph";
import type { ColumnWorkflow } from "@/features/settings/workflow";
import { columnDotStyle } from "@/lib/column-color";
import { useActionFeedback } from "@/composables/useActionFeedback";
import { useBoardStore } from "@/features/board/stores/board";

const StatusFlowEditor = defineAsyncComponent(
  () => import("@/features/settings/components/StatusFlowEditor.vue"),
);

type ColumnsTab = "columns" | "workflow" | "statuses" | "tags";
const COLUMNS_TABS: ColumnsTab[] = ["columns", "workflow", "statuses", "tags"];

const { t } = useI18n();
const feedback = useActionFeedback();
const route = useRoute();
const router = useRouter();
const boardStore = useBoardStore();
const columns = ref<SettingsColumn[]>([]);
const activeScheme = ref<BoardScheme | null>(null);
const schemes = ref<BoardScheme[]>([]);
const boardLimits = ref<BoardLimits>({ ...DEFAULT_BOARD_LIMITS });
const workflow = ref<ColumnWorkflow>({ enforced: false, transitions: [] });
const statusGraph = ref<TaskStatusGraph>({ enforced: false, statuses: [], transitions: [] });
const displayColumns = ref<SettingsColumn[]>([]);
const loading = ref(true);
const error = ref("");
const workflowError = ref("");
const statusGraphError = ref("");
const reordering = ref(false);
const switchingScheme = ref(false);
const orderBeforeDrag = ref<number[]>([]);

function parseTab(value: unknown): ColumnsTab {
  if (typeof value === "string" && COLUMNS_TABS.includes(value as ColumnsTab)) {
    return value as ColumnsTab;
  }
  return "columns";
}

const activeTab = ref<ColumnsTab>(parseTab(route.query.tab));
const schemeCreateShow = ref(false);
const confirmOpen = ref(false);
const confirmTitle = ref("");
const confirmMessage = ref("");
const confirmLabel = ref("");
const confirmDanger = ref(false);
const confirmLoading = ref(false);
const pendingConfirmAction = ref<(() => Promise<void>) | null>(null);

const panelShow = ref(false);
const panelMode = ref<"create" | "edit">("create");
const panelColumn = ref<SettingsColumn | null>(null);

const metaLine = computed(() => t("settings.columnsMeta", displayColumns.value.length));

const isSchemeLocked = computed(() => activeScheme.value?.is_locked ?? false);

const isSchemeLimitReached = computed(
  () => schemes.value.length >= boardLimits.value.max_schemes,
);
const isColumnLimitReached = computed(
  () => displayColumns.value.length >= boardLimits.value.max_columns,
);
const canCreateScheme = computed(() => !isSchemeLimitReached.value);
const canCreateColumn = computed(() => !isSchemeLocked.value && !isColumnLimitReached.value);

const schemeLimitTitle = computed(() =>
  t("settings.schemeLimitReached", { max: boardLimits.value.max_schemes }),
);
const columnLimitTitle = computed(() =>
  t("settings.columnLimitReached", { max: boardLimits.value.max_columns }),
);

const selectedColumnId = computed(() =>
  panelShow.value && panelMode.value === "edit" ? panelColumn.value?.id : null,
);

watch(activeTab, (tab) => {
  if (parseTab(route.query.tab) === tab) {
    return;
  }
  const query = { ...route.query, tab };
  void router.replace({ name: "settings-columns", query });
});

watch(
  () => route.query.tab,
  (tab) => {
    const next = parseTab(tab);
    if (activeTab.value !== next) {
      activeTab.value = next;
    }
  },
);

function syncDisplayColumns() {
  displayColumns.value = [...columns.value].sort(
    (left, right) => left.position - right.position,
  );
}

async function loadColumns() {
  loading.value = true;
  error.value = "";
  workflowError.value = "";

  try {
    const [columnsPayload, loadedSchemes] = await Promise.all([
      fetchColumns(),
      fetchBoardSchemes(),
    ]);
    columns.value = columnsPayload.columns;
    activeScheme.value = columnsPayload.scheme;
    schemes.value = loadedSchemes.schemes;
    boardLimits.value = {
      max_schemes: loadedSchemes.limits.max_schemes || columnsPayload.limits.max_schemes,
      max_columns: columnsPayload.limits.max_columns || loadedSchemes.limits.max_columns,
      max_task_statuses:
        columnsPayload.limits.max_task_statuses ||
        loadedSchemes.limits.max_task_statuses ||
        DEFAULT_BOARD_LIMITS.max_task_statuses,
    };
    syncDisplayColumns();
  } catch (loadError) {
    error.value =
      loadError instanceof Error ? loadError.message : t("errors.loadColumns");
    loading.value = false;
    return;
  }

  try {
    workflow.value = await fetchColumnWorkflow();
  } catch (loadError) {
    workflow.value = { enforced: false, transitions: [] };
    workflowError.value =
      loadError instanceof Error ? loadError.message : t("errors.loadWorkflow");
  }

  try {
    statusGraph.value = await fetchTaskStatusGraph();
    statusGraphError.value = "";
  } catch (loadError) {
    statusGraph.value = { enforced: false, statuses: [], transitions: [] };
    statusGraphError.value =
      loadError instanceof Error ? loadError.message : t("errors.loadStatusWorkflow");
  } finally {
    loading.value = false;
  }
}

function onWorkflowSaved(nextWorkflow: ColumnWorkflow) {
  workflow.value = nextWorkflow;
}

function onStatusGraphSaved(nextGraph: TaskStatusGraph) {
  statusGraph.value = nextGraph;
}

function schemeTitle(scheme: BoardScheme | undefined, slug: string): string {
  if (scheme?.slug === "default") {
    return t("settings.schemeDefaultName");
  }
  return scheme?.name || slug;
}

function openConfirmDialog(
  title: string,
  message: string,
  action: () => Promise<void>,
  options: { danger?: boolean; label?: string } = {},
) {
  confirmTitle.value = title;
  confirmMessage.value = message;
  confirmLabel.value = options.label || t("common.confirm");
  pendingConfirmAction.value = action;
  confirmDanger.value = options.danger ?? false;
  confirmOpen.value = true;
}

function closeConfirmDialog() {
  if (confirmLoading.value) {
    return;
  }
  confirmOpen.value = false;
  pendingConfirmAction.value = null;
}

async function onConfirmDialogConfirm() {
  const action = pendingConfirmAction.value;
  if (!action) {
    return;
  }

  confirmLoading.value = true;
  try {
    await action();
    confirmOpen.value = false;
  } finally {
    confirmLoading.value = false;
    pendingConfirmAction.value = null;
  }
}

async function onSchemeChoose(slug: string) {
  if (!slug || slug === activeScheme.value?.slug) {
    return;
  }

  const scheme = schemes.value.find((item) => item.slug === slug);
  openConfirmDialog(
    t("settings.schemeSwitchConfirmTitle"),
    t("settings.schemeSwitchConfirm", { name: schemeTitle(scheme, slug) }),
    () => applySchemeSwitch(slug),
    { danger: true },
  );
}

async function onSchemeDelete(slug: string) {
  const scheme = schemes.value.find((item) => item.slug === slug);
  if (!scheme || scheme.is_locked || activeScheme.value?.slug === slug) {
    return;
  }

  openConfirmDialog(
    t("settings.schemeDeleteConfirmTitle"),
    t("settings.schemeDeleteConfirm", { name: scheme.name }),
    () => applySchemeDelete(slug),
    { danger: true, label: t("common.delete") },
  );
}

async function applySchemeDelete(slug: string) {
  switchingScheme.value = true;
  error.value = "";
  try {
    await deleteBoardScheme(slug);
    await loadColumns();
    schemeCreateShow.value = false;
    panelShow.value = false;
    feedback.successKey("toast.schemeDeleted");
  } catch (deleteError) {
    feedback.fromError(deleteError, "errors.deleteScheme");
  } finally {
    switchingScheme.value = false;
  }
}

async function applySchemeSwitch(slug: string) {
  switchingScheme.value = true;
  error.value = "";
  try {
    const result = await switchBoardScheme(slug);
    applySchemeResult(result);
    schemeCreateShow.value = false;
    feedback.successKey("toast.schemeSwitched");
  } catch (switchError) {
    feedback.fromError(switchError, "errors.switchScheme");
  } finally {
    switchingScheme.value = false;
  }
}

function applySchemeResult(result: SchemeSwitchResult) {
  columns.value = result.columns;
  activeScheme.value = result.scheme;
  workflow.value = result.workflow;
  statusGraph.value = result.status_graph;
  syncDisplayColumns();
  panelShow.value = false;
  boardStore.tagFilter = "";
  void boardStore.loadTags();
}

function onSchemeCreated() {
  void loadSchemesList().then(() => {
    schemeCreateShow.value = false;
  });
}

async function loadSchemesList() {
  const payload = await fetchBoardSchemes();
  schemes.value = payload.schemes;
  boardLimits.value = payload.limits;
}

function openSchemeCreate() {
  if (!canCreateScheme.value) {
    return;
  }
  schemeCreateShow.value = !schemeCreateShow.value;
  if (schemeCreateShow.value) {
    panelShow.value = false;
  }
}

function closeSchemeCreate() {
  schemeCreateShow.value = false;
}

async function persistOrder() {
  if (reordering.value || isSchemeLocked.value) {
    return;
  }

  const nextOrder = displayColumns.value.map((column) => column.id);
  const unchanged =
    orderBeforeDrag.value.length === nextOrder.length &&
    orderBeforeDrag.value.every((id, index) => id === nextOrder[index]);
  if (unchanged) {
    return;
  }

  reordering.value = true;
  error.value = "";

  try {
    columns.value = await reorderColumns(nextOrder);
    syncDisplayColumns();
    feedback.successKey("toast.columnsReordered");
  } catch (reorderError) {
    feedback.fromError(reorderError, "errors.reorderColumns");
    syncDisplayColumns();
  } finally {
    reordering.value = false;
  }
}

function onDragStart() {
  orderBeforeDrag.value = displayColumns.value.map((column) => column.id);
}

interface DragEndEvent {
  oldIndex?: number;
  newIndex?: number;
}

function onDragEnd(event: DragEndEvent) {
  if (event.oldIndex === undefined || event.newIndex === undefined) {
    return;
  }
  if (event.oldIndex === event.newIndex) {
    return;
  }
  void persistOrder();
}

function openCreate() {
  if (isSchemeLocked.value || isColumnLimitReached.value) {
    return;
  }
  activeTab.value = "columns";
  error.value = "";
  panelMode.value = "create";
  panelColumn.value = null;
  panelShow.value = true;
}

function openEdit(column: SettingsColumn) {
  activeTab.value = "columns";
  error.value = "";
  panelMode.value = "edit";
  panelColumn.value = column;
  panelShow.value = true;
}

function closePanel() {
  panelShow.value = false;
}

function onColumnChanged() {
  error.value = "";
  void loadColumns();
}

function openWorkflowTab() {
  activeTab.value = "workflow";
  panelShow.value = false;
}

function isSelected(column: SettingsColumn): boolean {
  return selectedColumnId.value === column.id;
}

function wipLabel(column: SettingsColumn): string | null {
  if (column.wip_limit === null) {
    return null;
  }
  return t("board.wipLimit", { count: column.wip_limit });
}

onMounted(loadColumns);
</script>

<template>
  <div class="settings-page">
    <div class="board-shell settings-board-shell columns-shell">
      <header class="board-toolbar shrink-0">
        <div class="board-toolbar-info">
          <h1 class="page-title">{{ $t("settings.columnsTitle") }}</h1>
          <p class="page-meta">{{ metaLine }} · {{ $t("settings.columnsPageMeta") }}</p>
        </div>
      </header>

      <Transition name="scheme-alert-slide">
        <p v-if="error" key="page-error" class="alert-error mx-4 mt-3 shrink-0">
          {{ error }}
        </p>
        <p
          v-else-if="workflowError && activeTab === 'workflow'"
          key="workflow-error"
          class="alert-error mx-4 mt-3 shrink-0"
        >
          {{ workflowError }}
        </p>
        <p
          v-else-if="statusGraphError && activeTab === 'statuses'"
          key="status-graph-error"
          class="alert-error mx-4 mt-3 shrink-0"
        >
          {{ statusGraphError }}
        </p>
      </Transition>

      <Transition name="scheme-body-swap" mode="out-in">
        <div v-if="loading" key="loading" class="settings-body settings-body-center">
          <div class="loading-state">
            <span class="loading-spinner" aria-hidden="true" />
            <p class="text-sm text-(--color-text-secondary)">{{ $t("common.loading") }}</p>
          </div>
        </div>

        <div v-else key="content" class="settings-body settings-body-split columns-page-body">
        <nav class="columns-segmented" :aria-label="$t('settings.columnsSectionsAria')">
          <button
            class="columns-segmented-btn"
            :class="{ 'columns-segmented-btn-active': activeTab === 'columns' }"
            type="button"
            @click="activeTab = 'columns'"
          >
            <ViewColumnsIcon class="icon-sm" />
            {{ $t("settings.columnsTab") }}
          </button>
          <button
            class="columns-segmented-btn"
            :class="{ 'columns-segmented-btn-active': activeTab === 'workflow' }"
            type="button"
            @click="activeTab = 'workflow'"
          >
            <ArrowPathIcon class="icon-sm" />
            {{ $t("settings.workflowTab") }}
          </button>
          <button
            class="columns-segmented-btn"
            :class="{ 'columns-segmented-btn-active': activeTab === 'statuses' }"
            type="button"
            @click="activeTab = 'statuses'"
          >
            <QueueListIcon class="icon-sm" />
            {{ $t("settings.statusesTab") }}
          </button>
          <button
            class="columns-segmented-btn"
            :class="{ 'columns-segmented-btn-active': activeTab === 'tags' }"
            type="button"
            @click="activeTab = 'tags'"
          >
            <TagIcon class="icon-sm" />
            {{ $t("settings.tagsTab") }}
          </button>
        </nav>

        <Transition name="scheme-tab-swap" mode="out-in">
          <div v-if="activeTab === 'columns'" key="columns" class="columns-layout">
          <aside class="settings-panel columns-list-panel">
            <header class="settings-panel-header columns-list-header">
              <div class="columns-list-header-main">
                <p class="drawer-eyebrow">{{ $t("settings.columnsList") }}</p>
                <h2 class="settings-panel-title">{{ $t("settings.columnsTab") }}</h2>
              </div>
            </header>

            <div class="settings-panel-body columns-list-body">
              <SchemePicker
                v-if="schemes.length"
                :schemes="schemes"
                :active-slug="activeScheme?.slug || null"
                :column-count="displayColumns.length"
                :disabled="switchingScheme || loading"
                :creating="schemeCreateShow"
                :create-disabled="!canCreateScheme"
                :create-disabled-title="schemeLimitTitle"
                @choose="onSchemeChoose"
                @create="openSchemeCreate"
                @delete="onSchemeDelete"
              />

              <Transition name="notify-fold-collapse">
                <div v-if="schemeCreateShow" key="scheme-create" class="columns-scheme-create-shell">
                  <SchemeCreatePanel
                    :disabled="!canCreateScheme"
                    :disabled-title="schemeLimitTitle"
                    @created="onSchemeCreated"
                    @cancel="closeSchemeCreate"
                  />
                </div>
              </Transition>

              <p v-if="displayColumns.length" class="columns-order-hint">{{ $t("settings.columnsOrderHint") }}</p>

              <draggable
                v-if="displayColumns.length"
                v-model="displayColumns"
                item-key="id"
                :disabled="isSchemeLocked"
                handle=".columns-drag-handle"
                :animation="150"
                ghost-class="columns-row-ghost"
                drag-class="columns-row-drag"
                class="columns-list"
                @start="onDragStart"
                @end="onDragEnd"
              >
                <template #item="{ element: column, index }">
                  <article
                    class="columns-list-row scheme-stagger-item"
                    :class="{ 'columns-list-row-active': isSelected(column) }"
                    :style="{ '--scheme-item-delay': `${index * 40}ms` }"
                    role="button"
                    tabindex="0"
                    @click="openEdit(column)"
                    @keydown.enter.prevent="openEdit(column)"
                  >
                    <button
                      v-if="!isSchemeLocked"
                      class="columns-drag-handle icon-btn columns-action-btn"
                      type="button"
                      :title="$t('settings.dragColumn')"
                      :aria-label="$t('settings.dragColumn')"
                      @click.stop
                    >
                      <Bars3Icon class="icon-sm" />
                    </button>

                    <span
                      class="columns-list-dot"
                      :style="columnDotStyle(column.color)"
                    />

                    <div class="columns-list-main">
                      <div class="columns-list-title-row">
                        <span class="columns-list-name">{{ columnDisplayName(column) }}</span>
                      </div>
                      <span class="columns-list-meta">
                        {{
                          wipLabel(column) ||
                          $t("settings.position", { position: index + 1 })
                        }}
                      </span>
                    </div>
                  </article>
                </template>
              </draggable>

              <div v-else class="columns-list-empty">
                <p class="columns-list-empty-text">{{ $t("settings.columnsListEmpty") }}</p>
              </div>
            </div>

            <footer
              v-if="!isSchemeLocked && !schemeCreateShow"
              class="columns-list-footer"
            >
              <button
                class="status-flow-palette-action"
                type="button"
                :disabled="!canCreateColumn"
                :title="isColumnLimitReached ? columnLimitTitle : undefined"
                @click="openCreate"
              >
                <PlusIcon class="icon-sm" />
                <span>{{ $t("settings.newColumn") }}</span>
              </button>
            </footer>
          </aside>

          <section class="columns-detail-shell">
            <Transition name="scheme-inspector-swap" mode="out-in">
              <ColumnPanel
                v-if="panelShow"
                :key="panelMode === 'create' ? 'create' : panelColumn?.id"
                :mode="panelMode"
                :column="panelColumn"
                :status-graph="statusGraph"
                :read-only="isSchemeLocked || Boolean(panelColumn?.is_locked)"
                :create-disabled="isColumnLimitReached"
                :create-disabled-title="columnLimitTitle"
                @close="closePanel"
                @changed="onColumnChanged"
              />

              <div v-else key="empty" class="settings-panel columns-detail-empty">
                <div class="columns-detail-empty-icon">
                  <Squares2X2Icon class="size-8" />
                </div>
                <h2 class="columns-detail-empty-title">
                  {{ $t("settings.columnDetailEmptyTitle") }}
                </h2>
                <p class="columns-detail-empty-text">
                  {{
                    isSchemeLocked
                      ? $t("settings.columnDetailEmptyText")
                      : $t("settings.columnDetailEmptyCustomText")
                  }}
                </p>
                <div class="columns-detail-empty-actions">
                  <button
                    class="btn-ghost px-4 py-2 text-sm"
                    type="button"
                    @click="openWorkflowTab"
                  >
                    <ArrowPathIcon class="icon-sm" />
                    {{ $t("settings.editTransitions") }}
                  </button>
                </div>
              </div>
            </Transition>
          </section>
        </div>

        <ColumnWorkflowMatrix
          v-else-if="activeTab === 'workflow'"
          key="workflow"
          :columns="displayColumns"
          :workflow="workflow"
          :read-only="isSchemeLocked"
          @saved="onWorkflowSaved"
        />

        <StatusFlowEditor
          v-else-if="activeTab === 'statuses'"
          key="statuses"
          :graph="statusGraph"
          :columns="displayColumns"
          :read-only="isSchemeLocked"
          :max-statuses="boardLimits.max_task_statuses"
          @saved="onStatusGraphSaved"
        />

        <div
          v-else-if="activeTab === 'tags'"
          key="tags"
          class="columns-tab-shell"
        >
          <TagsSettingsPanel :key="activeScheme?.slug ?? 'default'" />
        </div>
        </Transition>
        </div>
      </Transition>
    </div>

    <Teleport to="body">
      <Transition name="modal-fade">
        <div
          v-if="confirmOpen"
          class="modal-backdrop"
          role="presentation"
          @click.self="closeConfirmDialog"
        >
          <section
            class="modal-panel confirm-dialog-panel"
            role="alertdialog"
            aria-modal="true"
            :aria-labelledby="confirmTitle ? 'columns-confirm-title' : undefined"
            :aria-describedby="confirmMessage ? 'columns-confirm-message' : undefined"
            @click.stop
          >
            <header class="modal-header">
              <h2 id="columns-confirm-title" class="modal-title">{{ confirmTitle }}</h2>
            </header>

            <div class="modal-body">
              <p id="columns-confirm-message" class="confirm-dialog-message">
                {{ confirmMessage }}
              </p>
            </div>

            <footer class="modal-footer">
              <button
                class="btn-ghost px-4 py-2 text-sm"
                type="button"
                :disabled="confirmLoading"
                @click="closeConfirmDialog"
              >
                {{ $t("common.cancel") }}
              </button>
              <button
                class="px-4 py-2 text-sm"
                :class="confirmDanger ? 'btn-danger' : 'btn-primary'"
                type="button"
                :disabled="confirmLoading"
                @click="onConfirmDialogConfirm"
              >
                {{ confirmLoading ? $t("common.saving") : confirmLabel }}
              </button>
            </footer>
          </section>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
