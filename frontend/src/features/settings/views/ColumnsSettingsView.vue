<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import draggable from "vuedraggable";
import {
  Bars3Icon,
  PlusIcon,
  ViewColumnsIcon,
} from "@heroicons/vue/24/outline";

import ColumnPanel from "@/features/settings/components/ColumnPanel.vue";
import { fetchColumns, reorderColumns } from "@/features/settings/api";
import type { SettingsColumn } from "@/features/settings/types";
import {
  columnDotStyle,
  columnPreviewLaneStyle,
} from "@/lib/column-color";
import { pluralRu } from "@/lib/plural";

const columns = ref<SettingsColumn[]>([]);
const displayColumns = ref<SettingsColumn[]>([]);
const loading = ref(true);
const error = ref("");
const reordering = ref(false);
const orderBeforeDrag = ref<number[]>([]);

const panelShow = ref(false);
const panelMode = ref<"create" | "edit">("create");
const panelColumn = ref<SettingsColumn | null>(null);

const metaLine = computed(() =>
  pluralRu(displayColumns.value.length, "колонка", "колонки", "колонок"),
);

const selectedColumnId = computed(() =>
  panelShow.value && panelMode.value === "edit" ? panelColumn.value?.id : null,
);

function syncDisplayColumns() {
  displayColumns.value = [...columns.value].sort(
    (left, right) => left.position - right.position,
  );
}

async function loadColumns() {
  loading.value = true;
  error.value = "";
  try {
    columns.value = await fetchColumns();
    syncDisplayColumns();
  } catch (loadError) {
    error.value =
      loadError instanceof Error ? loadError.message : "Не удалось загрузить колонки";
  } finally {
    loading.value = false;
  }
}

async function persistOrder() {
  if (reordering.value) {
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
  } catch (reorderError) {
    error.value =
      reorderError instanceof Error ? reorderError.message : "Не удалось изменить порядок";
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
  error.value = "";
  panelMode.value = "create";
  panelColumn.value = null;
  panelShow.value = true;
}

function openEdit(column: SettingsColumn) {
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

function isSelected(column: SettingsColumn): boolean {
  return selectedColumnId.value === column.id;
}

function wipLabel(column: SettingsColumn): string | null {
  if (column.wip_limit === null) {
    return null;
  }
  return `Лимит ${column.wip_limit}`;
}

onMounted(loadColumns);
</script>

<template>
  <div class="settings-page">
    <div class="board-shell settings-board-shell">
      <header class="board-toolbar shrink-0">
        <div class="board-toolbar-info">
          <h1 class="page-title">Колонки</h1>
          <p class="page-meta">{{ metaLine }} · порядок и оформление</p>
        </div>
      </header>

      <p v-if="error" class="alert-error mx-4 mt-3 shrink-0">
        {{ error }}
      </p>

      <div v-if="loading" class="settings-body settings-body-center">
        <div class="loading-state">
          <span class="loading-spinner" aria-hidden="true" />
          <p class="text-sm text-[var(--color-text-secondary)]">Загрузка колонок...</p>
        </div>
      </div>

      <div v-else class="settings-body settings-body-split">
        <section class="columns-preview" aria-label="Порядок колонок на доске">
          <div
            v-for="(column, index) in displayColumns"
            :key="column.id"
            class="columns-preview-lane"
            :class="{ 'columns-preview-lane-active': isSelected(column) }"
            :style="columnPreviewLaneStyle(column.color)"
            role="button"
            tabindex="0"
            @click="openEdit(column)"
            @keydown.enter.prevent="openEdit(column)"
          >
            <span
              class="columns-preview-dot"
              :style="columnDotStyle(column.color)"
            />
            <span class="columns-preview-name">{{ column.name }}</span>
            <span class="columns-preview-index">{{ index + 1 }}</span>
          </div>
        </section>

        <div class="settings-split">
          <aside class="columns-sidebar">
            <div class="columns-sidebar-head">
              <p class="columns-sidebar-label">Список</p>
            </div>

            <draggable
              v-model="displayColumns"
              item-key="id"
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
                  class="columns-list-row"
                  :class="{ 'columns-list-row-active': isSelected(column) }"
                  role="button"
                  tabindex="0"
                  @click="openEdit(column)"
                  @keydown.enter.prevent="openEdit(column)"
                >
                  <button
                    class="columns-drag-handle icon-btn columns-action-btn"
                    type="button"
                    title="Перетащите"
                    aria-label="Перетащите колонку"
                    @click.stop
                  >
                    <Bars3Icon class="icon-sm" />
                  </button>

                  <span
                    class="columns-list-dot"
                    :style="columnDotStyle(column.color)"
                  />

                  <div class="columns-list-main">
                    <span class="columns-list-name">{{ column.name }}</span>
                    <span class="columns-list-meta">
                      {{ wipLabel(column) || `Позиция ${index + 1}` }}
                    </span>
                  </div>
                </article>
              </template>
            </draggable>
          </aside>

          <section class="columns-workspace">
            <Transition name="settings-workspace" mode="out-in">
              <ColumnPanel
                v-if="panelShow"
                :key="panelMode === 'create' ? 'create' : panelColumn?.id"
                :mode="panelMode"
                :column="panelColumn"
                @close="closePanel"
                @changed="onColumnChanged"
              />

              <div v-else key="empty" class="columns-empty">
                <div class="columns-empty-icon">
                  <ViewColumnsIcon class="size-8" />
                </div>
                <h2 class="columns-empty-title">Настройка колонок</h2>
                <p class="columns-empty-text">
                  Выберите колонку в списке или на превью доски, чтобы изменить название,
                  цвет и лимит WIP.
                </p>
                <button class="btn-primary px-4 py-2 text-sm" type="button" @click="openCreate">
                  <PlusIcon class="icon-sm" />
                  Новая колонка
                </button>
              </div>
            </Transition>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>
