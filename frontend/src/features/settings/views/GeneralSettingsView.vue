<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import { ArrowPathIcon, GlobeAltIcon } from "@heroicons/vue/24/outline";

import ProjectMonitoringPanel from "@/features/settings/components/ProjectMonitoringPanel.vue";
import ProjectSettingsPanel from "@/features/settings/components/ProjectSettingsPanel.vue";
import { usePlatformStatus } from "@/features/settings/usePlatformStatus";
import { useProjectSettings } from "@/features/settings/useProjectSettings";

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const settings = useProjectSettings();
const platform = usePlatformStatus();

const activeItem = ref<string | null>(null);

function syncRoute() {
  const current = typeof route.query.item === "string" ? route.query.item : null;
  if (current === activeItem.value) {
    return;
  }
  const query: Record<string, string> = {};
  if (typeof route.query.service === "string") {
    query.service = route.query.service;
  }
  if (activeItem.value) {
    query.item = activeItem.value;
  }
  void router.replace({
    name: "settings-general",
    query,
  });
}

function applyRouteState() {
  const item = typeof route.query.item === "string" ? route.query.item : null;
  const next = item === "language" || item === "timezone" ? item : null;
  if (activeItem.value === next) {
    return;
  }
  activeItem.value = next;
}

watch(activeItem, () => {
  syncRoute();
});

watch(
  () => route.query.item,
  () => {
    applyRouteState();
  },
);

onMounted(async () => {
  await settings.loadSettings();
  applyRouteState();
});
</script>

<template>
  <div class="settings-page">
    <div class="board-shell settings-board-shell">
      <header class="board-toolbar shrink-0">
        <div class="board-toolbar-info">
          <h1 class="page-title">{{ t("settings.hub.title") }}</h1>
          <p class="page-meta">{{ t("settings.hub.meta") }}</p>
        </div>
      </header>

      <p v-if="settings.loadFailed.value" class="alert-error mx-4 mt-3 shrink-0">
        {{ settings.error.value }}
      </p>
      <p v-else-if="settings.error.value" class="alert-error mx-4 mt-3 shrink-0">
        {{ settings.error.value }}
      </p>

      <div v-if="settings.loading.value" class="settings-body settings-body-center">
        <div class="loading-state">
          <span class="loading-spinner" aria-hidden="true" />
          <p class="text-sm text-[var(--color-text-secondary)]">{{ t("common.loading") }}</p>
        </div>
      </div>

      <div v-else-if="settings.loadFailed.value" class="settings-body settings-body-center">
        <div class="jobs-empty">
          <span class="jobs-empty-icon">
            <GlobeAltIcon class="size-7" />
          </span>
          <p class="jobs-empty-title">{{ t("errors.loadSettings") }}</p>
          <button class="btn btn-secondary mt-2" type="button" @click="settings.loadSettings()">
            <ArrowPathIcon class="icon-sm" />
            {{ t("common.retry") }}
          </button>
        </div>
      </div>

      <div v-else-if="settings.form.value" class="settings-body settings-body-split">
        <div class="project-layout">
          <ProjectMonitoringPanel
            :error="platform.error.value"
            :loading="platform.loading.value"
            :on-reload="platform.reload"
            :settings="settings.form.value"
            :status="platform.status.value"
          />

          <ProjectSettingsPanel
            v-model:active-item="activeItem"
            :settings="settings"
          />
        </div>
      </div>
    </div>
  </div>
</template>
