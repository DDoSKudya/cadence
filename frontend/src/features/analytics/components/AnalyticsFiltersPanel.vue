<script setup lang="ts">
import { XMarkIcon } from "@heroicons/vue/24/outline";

import { sourceLabel } from "@/features/analytics/labels";
import type { AnalyticsFilters } from "@/features/analytics/types";
import type { Tag } from "@/features/board/types";

const SOURCE_OPTIONS = ["ui", "api", "json_import", "telegram"] as const;

const open = defineModel<boolean>("open", { default: false });
const draftFilters = defineModel<AnalyticsFilters>("draftFilters", { required: true });

defineProps<{
  tags: Tag[];
  filtersActive: boolean;
}>();

const emit = defineEmits<{
  apply: [];
  clear: [];
}>();

function close() {
  open.value = false;
}

function apply() {
  emit("apply");
  close();
}

function clear() {
  emit("clear");
}
</script>

<template>
  <Teleport to="body">
    <Transition name="slide-panel">
      <div v-if="open" class="drawer-backdrop" @click.self="close">
        <aside
          class="drawer-panel drawer-panel-narrow"
          role="dialog"
          aria-labelledby="analytics-filters-title"
          aria-modal="true"
        >
          <header class="drawer-header">
            <div>
              <p class="drawer-eyebrow">{{ $t("analytics.filtersEyebrow") }}</p>
              <h2 id="analytics-filters-title" class="drawer-title">{{ $t("analytics.filtersTitle") }}</h2>
            </div>
            <button class="icon-btn" type="button" @click="close">
              <XMarkIcon class="icon-sm" />
            </button>
          </header>

          <div class="drawer-body">
            <form class="task-form" @submit.prevent="apply">
              <label class="form-field">
                <span class="form-label">{{ $t("common.week") }}</span>
                <input
                  v-model="draftFilters.week"
                  class="field px-3 py-2"
                  :placeholder="$t('analytics.weekPlaceholder')"
                  type="text"
                />
              </label>
              <label class="form-field">
                <span class="form-label">{{ $t("common.from") }}</span>
                <input v-model="draftFilters.from" class="field px-3 py-2" type="date" />
              </label>
              <label class="form-field">
                <span class="form-label">{{ $t("common.to") }}</span>
                <input v-model="draftFilters.to" class="field px-3 py-2" type="date" />
              </label>
              <label class="form-field">
                <span class="form-label">{{ $t("common.tag") }}</span>
                <select v-model="draftFilters.tag" class="field px-3 py-2">
                  <option value="">{{ $t("common.all") }}</option>
                  <option v-for="tag in tags" :key="tag.id" :value="tag.slug">
                    {{ tag.name }}
                  </option>
                </select>
              </label>
              <label class="form-field">
                <span class="form-label">{{ $t("common.source") }}</span>
                <select v-model="draftFilters.source" class="field px-3 py-2">
                  <option value="">{{ $t("common.all") }}</option>
                  <option v-for="source in SOURCE_OPTIONS" :key="source" :value="source">
                    {{ sourceLabel(source) }}
                  </option>
                </select>
              </label>
            </form>
          </div>

          <footer class="drawer-footer">
            <button
              v-if="filtersActive"
              class="btn-secondary"
              type="button"
              @click="clear"
            >
              {{ $t("common.reset") }}
            </button>
            <button class="btn-primary" type="button" @click="apply">{{ $t("common.apply") }}</button>
          </footer>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>
