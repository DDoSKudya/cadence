<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { useRouter } from "vue-router";

import LocaleFlagIcon from "@/features/settings/components/LocaleFlagIcon.vue";
import ProjectSettingDetailPanel from "@/features/settings/components/ProjectSettingDetailPanel.vue";
import { localeLabelKey } from "@/features/settings/locale-display";
import {
  PROJECT_SETTING_GROUPS,
  findProjectSettingItem,
  type ProjectSettingPanelId,
} from "@/features/settings/project-groups";
import type { useProjectSettings } from "@/features/settings/useProjectSettings";

const props = defineProps<{
  settings: ReturnType<typeof useProjectSettings>;
  activeItem: string | null;
}>();

const emit = defineEmits<{
  "update:activeItem": [itemId: string | null];
}>();

const { t } = useI18n();
const router = useRouter();

const form = computed(() => props.settings.form.value);

const activeMatch = computed(() => findProjectSettingItem(props.activeItem));

const activePanel = computed(() => activeMatch.value?.item.panel ?? null);

function rowMeta(itemId: string) {
  if (!form.value) {
    return "";
  }
  if (itemId === "timezone") {
    return form.value.timezone;
  }
  return "";
}

function openItem(itemId: string, panel?: ProjectSettingPanelId, route?: string) {
  if (route) {
    void router.push(route);
    return;
  }
  if (!panel) {
    return;
  }
  emit("update:activeItem", itemId);
}

function closeDetail() {
  emit("update:activeItem", null);
}

function itemHint(panel: ProjectSettingPanelId) {
  if (panel === "language") {
    return t("settings.languageHint");
  }
  return t("settings.hub.items.timezone.hint");
}
</script>

<template>
  <section v-if="form" class="settings-panel project-settings-panel">
    <header class="settings-panel-header">
      <div class="notify-panel-head">
        <div>
          <h2 class="settings-panel-title">{{ t("settings.project.groupsTitle") }}</h2>
        </div>
      </div>
    </header>

    <div class="settings-panel-body project-settings-panel-body">
      <div class="project-settings-workspace">
        <Transition mode="out-in" name="project-settings-swap">
          <div v-if="!activePanel" key="settings-list" class="project-settings-groups">
          <section
            v-for="group in PROJECT_SETTING_GROUPS"
            :key="group.id"
            class="project-settings-group"
          >
            <header class="project-settings-group-head">
              <span class="notify-fold-icon" :class="group.iconClass">
                <component :is="group.icon" />
              </span>
              <h3 class="project-settings-group-title">{{ t(group.titleKey) }}</h3>
            </header>

            <div class="project-settings-group-items">
              <button
                v-for="item in group.items"
                :key="item.id"
                class="project-settings-row project-settings-row-clickable"
                type="button"
                :aria-label="t(item.titleKey)"
                @click="openItem(item.id, item.panel, item.route)"
              >
                <span class="project-settings-row-icon">
                  <component :is="item.icon" />
                </span>
                <span class="project-settings-row-copy">
                  <span class="project-settings-row-title">{{ t(item.titleKey) }}</span>
                  <span class="project-settings-row-meta">
                    <template v-if="item.id === 'language'">
                      <span class="project-settings-locale-meta">
                        <LocaleFlagIcon :locale="form.language" />
                        <span>{{ t(localeLabelKey(form.language)) }}</span>
                      </span>
                    </template>
                    <template v-else>
                      {{ rowMeta(item.id) || t(item.descriptionKey) }}
                    </template>
                  </span>
                </span>
                <span class="project-monitor-service-chevron" aria-hidden="true">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M9 18l6-6-6-6" />
                  </svg>
                </span>
              </button>
            </div>
          </section>
        </div>

        <ProjectSettingDetailPanel
          v-else-if="activeMatch && activePanel"
          :key="`settings-detail-${activePanel}`"
          :panel="activePanel"
          :title-key="activeMatch.item.titleKey"
          :hint="itemHint(activePanel)"
          :settings="settings"
          :language="form.language"
          :timezone="form.timezone"
          @close="closeDetail"
        />
        </Transition>
      </div>
    </div>
  </section>
</template>
