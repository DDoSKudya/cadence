<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { apiFetch } from "@/shared/api/http";

interface BoardColumn {
  id: number;
  name: string;
  system_type: string;
  color: string;
  position: number;
  wip_limit: number | null;
}

const router = useRouter();
const columns = ref<BoardColumn[]>([]);
const loading = ref(true);
const error = ref("");
const newName = ref("");
const newColor = ref("slate");

const sortedColumns = computed(() =>
  [...columns.value].sort((left, right) => left.position - right.position),
);

async function loadColumns() {
  loading.value = true;
  error.value = "";
  const response = await apiFetch("/api/v1/columns/");
  if (!response.ok) {
    error.value = "Не удалось загрузить колонки";
    loading.value = false;
    return;
  }
  columns.value = await response.json();
  loading.value = false;
}

async function saveColumn(column: BoardColumn) {
  const response = await apiFetch(`/api/v1/columns/${column.id}/`, {
    method: "PATCH",
    body: JSON.stringify({
      name: column.name,
      color: column.color,
      wip_limit: column.wip_limit,
    }),
  });
  if (!response.ok) {
    error.value = "Не удалось сохранить колонку";
    await loadColumns();
  }
}

async function addColumn() {
  if (!newName.value.trim()) {
    return;
  }
  const response = await apiFetch("/api/v1/columns/", {
    method: "POST",
    body: JSON.stringify({
      name: newName.value.trim(),
      color: newColor.value.trim() || "slate",
    }),
  });
  if (!response.ok) {
    error.value = "Не удалось создать колонку";
    return;
  }
  newName.value = "";
  await loadColumns();
}

async function deactivateColumn(column: BoardColumn) {
  const response = await apiFetch(`/api/v1/columns/${column.id}/`, {
    method: "DELETE",
  });
  if (response.status === 409) {
    error.value = "В колонке есть задачи. Сначала перенесите их.";
    return;
  }
  if (!response.ok) {
    error.value = "Не удалось деактивировать колонку";
    return;
  }
  await loadColumns();
}

async function moveColumn(column: BoardColumn, direction: -1 | 1) {
  const ordered = sortedColumns.value;
  const index = ordered.findIndex((item) => item.id === column.id);
  const targetIndex = index + direction;
  if (index < 0 || targetIndex < 0 || targetIndex >= ordered.length) {
    return;
  }

  const reordered = [...ordered];
  const [moved] = reordered.splice(index, 1);
  reordered.splice(targetIndex, 0, moved);

  const response = await apiFetch("/api/v1/columns/reorder/", {
    method: "POST",
    body: JSON.stringify({ column_ids: reordered.map((item) => item.id) }),
  });
  if (!response.ok) {
    error.value = "Не удалось изменить порядок";
    await loadColumns();
    return;
  }
  columns.value = await response.json();
}

onMounted(loadColumns);
</script>

<template>
  <main class="min-h-screen bg-slate-50 p-6">
    <div class="mx-auto max-w-3xl">
      <div class="mb-6 flex items-center justify-between gap-4">
        <div>
          <p class="text-sm font-semibold uppercase tracking-wide text-blue-600">Cadence</p>
          <h1 class="text-2xl font-semibold text-slate-900">Колонки доски</h1>
        </div>
        <button
          class="text-sm font-medium text-slate-500 hover:text-slate-900"
          type="button"
          @click="router.push('/')"
        >
          На главную
        </button>
      </div>

      <p v-if="error" class="mb-4 text-sm text-red-600">{{ error }}</p>
      <p v-if="loading" class="text-sm text-slate-500">Загрузка...</p>

      <section v-else class="space-y-3">
        <article
          v-for="column in sortedColumns"
          :key="column.id"
          class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
        >
          <div class="grid gap-3 md:grid-cols-[1fr_120px_120px_auto] md:items-center">
            <input
              v-model="column.name"
              class="rounded-lg border border-slate-300 px-3 py-2"
              type="text"
              @change="saveColumn(column)"
            />
            <input
              v-model="column.color"
              class="rounded-lg border border-slate-300 px-3 py-2"
              placeholder="color"
              type="text"
              @change="saveColumn(column)"
            />
            <input
              v-model.number="column.wip_limit"
              class="rounded-lg border border-slate-300 px-3 py-2"
              placeholder="WIP"
              type="number"
              min="1"
              @change="saveColumn(column)"
            />
            <div class="flex gap-2">
              <button
                class="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                type="button"
                @click="moveColumn(column, -1)"
              >
                ↑
              </button>
              <button
                class="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                type="button"
                @click="moveColumn(column, 1)"
              >
                ↓
              </button>
              <button
                v-if="column.system_type !== 'done'"
                class="rounded-lg border border-red-200 px-3 py-2 text-sm text-red-600"
                type="button"
                @click="deactivateColumn(column)"
              >
                Убрать
              </button>
            </div>
          </div>
          <p class="mt-2 text-xs uppercase tracking-wide text-slate-400">
            {{ column.system_type }}
          </p>
        </article>
      </section>

      <form class="mt-6 flex flex-wrap gap-3" @submit.prevent="addColumn">
        <input
          v-model="newName"
          class="min-w-[200px] flex-1 rounded-lg border border-slate-300 px-3 py-2"
          placeholder="Новая колонка"
          type="text"
        />
        <input
          v-model="newColor"
          class="w-32 rounded-lg border border-slate-300 px-3 py-2"
          placeholder="color"
          type="text"
        />
        <button
          class="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white"
          type="submit"
        >
          Добавить
        </button>
      </form>
    </div>
  </main>
</template>
