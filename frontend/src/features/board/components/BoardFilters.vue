<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import { FunnelIcon, MagnifyingGlassIcon, XMarkIcon } from "@heroicons/vue/24/outline";

import { priorityLabel } from "@/features/board/labels";
import { useBoardStore } from "@/features/board/stores/board";

const board = useBoardStore();

const open = ref(false);

const activeFilterCount = computed(() => {
  let count = 0;
  if (board.priorityFilter) count += 1;
  if (board.tagFilter) count += 1;
  return count;
});

function onKeydown(event: KeyboardEvent) {
  if (event.key === "Escape" && open.value) {
    closePanel();
  }
}

watch(open, (isOpen) => {
  if (isOpen) {
    document.addEventListener("keydown", onKeydown);
    return;
  }
  document.removeEventListener("keydown", onKeydown);
});

onUnmounted(() => {
  document.removeEventListener("keydown", onKeydown);
});

function showPanel() {
  open.value = true;
}

function closePanel() {
  open.value = false;
}

function resetFilters() {
  board.priorityFilter = "";
  board.tagFilter = "";
}
</script>

<template>
  <div class="board-filters shrink-0">
    <div class="search-field">
      <MagnifyingGlassIcon class="search-field-icon" />
      <input
        v-model="board.searchQuery"
        class="field px-3 py-2 text-sm"
        :placeholder="$t('board.searchPlaceholder')"
        type="search"
      />
    </div>

    <button
      class="icon-btn"
      :class="{ 'icon-btn-active': open || activeFilterCount > 0 }"
      type="button"
      @click="showPanel"
    >
      <FunnelIcon class="icon-sm" />
      <span v-if="activeFilterCount > 0" class="text-xs font-semibold">{{ activeFilterCount }}</span>
    </button>

    <button
      v-if="board.filtersActive"
      class="btn-ghost px-2.5 py-2 text-sm"
      type="button"
      @click="board.clearFilters()"
    >
      <XMarkIcon class="icon-sm" />
    </button>
  </div>

  <Teleport to="body">
    <Transition name="slide-panel">
      <div v-if="open" class="drawer-backdrop" @click.self="closePanel">
        <aside class="drawer-panel drawer-panel-narrow" role="dialog" aria-labelledby="filters-title" aria-modal="true">
          <header class="drawer-header">
            <div>
              <p class="drawer-eyebrow">{{ $t("board.filtersEyebrow") }}</p>
              <h2 id="filters-title" class="drawer-title">{{ $t("common.filters") }}</h2>
            </div>
            <button class="icon-btn" type="button" @click="closePanel">
              <XMarkIcon class="icon-sm" />
            </button>
          </header>

          <div class="drawer-body space-y-4">
            <label class="form-field block text-sm">
              <span class="form-label">{{ $t("common.priority") }}</span>
              <select v-model="board.priorityFilter" class="field mt-1.5 px-3 py-2">
                <option value="">{{ $t("common.all") }}</option>
                <option value="high">{{ priorityLabel("high") }}</option>
                <option value="normal">{{ priorityLabel("normal") }}</option>
                <option value="low">{{ priorityLabel("low") }}</option>
              </select>
            </label>

            <label class="form-field block text-sm">
              <span class="form-label">{{ $t("common.tag") }}</span>
              <select v-model="board.tagFilter" class="field mt-1.5 px-3 py-2">
                <option value="">{{ $t("common.all") }}</option>
                <option v-for="tag in board.tags" :key="tag.id" :value="tag.slug">
                  {{ tag.name }}
                </option>
              </select>
            </label>
          </div>

          <footer v-if="activeFilterCount > 0" class="drawer-footer">
            <button class="btn-ghost px-4 py-2 text-sm" type="button" @click="resetFilters">
              {{ $t("common.reset") }}
            </button>
          </footer>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>
