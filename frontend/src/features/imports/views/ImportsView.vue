<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ArrowPathIcon, InboxArrowDownIcon } from "@heroicons/vue/24/outline";

import {
  fetchImports,
  retryImport,
  scanImports,
  type ImportLog,
} from "@/features/imports/api";

const imports = ref<ImportLog[]>([]);
const loading = ref(true);
const scanning = ref(false);
const retryingId = ref<number | null>(null);
const error = ref("");

async function loadImports() {
  loading.value = true;
  error.value = "";
  try {
    imports.value = await fetchImports();
  } catch (loadError) {
    error.value =
      loadError instanceof Error ? loadError.message : "Не удалось загрузить импорты";
  } finally {
    loading.value = false;
  }
}

async function scanInbox() {
  scanning.value = true;
  error.value = "";
  try {
    await scanImports();
    await loadImports();
  } catch (scanError) {
    error.value =
      scanError instanceof Error ? scanError.message : "Не удалось запустить сканирование";
  } finally {
    scanning.value = false;
  }
}

async function retry(importLog: ImportLog) {
  retryingId.value = importLog.id;
  error.value = "";
  try {
    await retryImport(importLog.id);
    await loadImports();
  } catch (retryError) {
    error.value =
      retryError instanceof Error ? retryError.message : "Не удалось повторить импорт";
  } finally {
    retryingId.value = null;
  }
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: "Ожидает",
    processing: "Обработка",
    succeeded: "Успех",
    failed: "Ошибка",
    skipped_duplicate: "Дубликат",
  };
  return labels[status] || status;
}

function formatDate(value: string | null): string {
  if (!value) {
    return "—";
  }
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

onMounted(loadImports);
</script>

<template>
  <div class="settings-page">
    <div class="board-shell settings-board-shell">
      <header class="board-toolbar shrink-0">
        <div class="board-toolbar-info">
          <h1 class="page-title">JSON inbox</h1>
          <p class="page-meta">Импорт задач из файлов в data/task-inbox/pending</p>
        </div>
        <div class="board-toolbar-actions">
          <button
            class="btn-primary px-3 py-2 text-sm disabled:opacity-60"
            type="button"
            :disabled="scanning"
            @click="scanInbox"
          >
            <ArrowPathIcon class="icon-sm" />
            Сканировать
          </button>
        </div>
      </header>

      <p v-if="error" class="alert-error mx-4 mt-3 shrink-0">{{ error }}</p>

      <div v-if="loading" class="settings-body settings-body-center">
        <div class="loading-state">
          <span class="loading-spinner" aria-hidden="true" />
          <p class="text-sm text-[var(--color-text-secondary)]">Загрузка импортов...</p>
        </div>
      </div>

      <div v-else class="settings-body imports-body">
        <div v-if="imports.length === 0" class="columns-empty">
          <div class="columns-empty-icon">
            <InboxArrowDownIcon class="size-8" />
          </div>
          <h2 class="columns-empty-title">Импортов пока нет</h2>
          <p class="columns-empty-text">
            Положите JSON в data/task-inbox/pending и нажмите «Сканировать».
          </p>
        </div>

        <div v-else class="imports-table-wrap">
          <table class="imports-table">
            <thead>
              <tr>
                <th>Файл</th>
                <th>Статус</th>
                <th>Задач</th>
                <th>Ключ</th>
                <th>Создан</th>
                <th />
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in imports" :key="item.id">
                <td>
                  <span class="imports-filename">{{ item.filename }}</span>
                  <p v-if="item.error_message" class="imports-error">{{ item.error_message }}</p>
                </td>
                <td>
                  <span class="imports-status" :class="`imports-status-${item.status}`">
                    {{ statusLabel(item.status) }}
                  </span>
                </td>
                <td>{{ item.tasks_created }}</td>
                <td class="imports-key">{{ item.idempotency_key || "—" }}</td>
                <td>{{ formatDate(item.created_at) }}</td>
                <td class="imports-actions">
                  <button
                    v-if="item.status === 'failed'"
                    class="btn-ghost px-3 py-1.5 text-sm disabled:opacity-60"
                    type="button"
                    :disabled="retryingId === item.id"
                    @click="retry(item)"
                  >
                    Повторить
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
