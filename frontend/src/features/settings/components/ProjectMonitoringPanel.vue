<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import {
  BoltIcon,
  CircleStackIcon,
  CpuChipIcon,
  QueueListIcon,
  ServerStackIcon,
} from "@heroicons/vue/24/outline";
import type { Component } from "vue";

import ServiceLogPanel from "@/features/settings/components/ServiceLogPanel.vue";
import type { PlatformStatus, ServiceHealth, ServiceStatus } from "@/features/settings/platform-api";
import { useProjectClock } from "@/features/settings/useProjectClock";
import {
  readAllowedQueryValue,
  replaceSettingsQueryParam,
} from "@/features/settings/query-state";
import type { NotificationSettingsForm } from "@/features/settings/project-api";
import { formatDateTime } from "@/lib/datetime";

const props = defineProps<{
  status: PlatformStatus | null;
  loading: boolean;
  error: string;
  settings: NotificationSettingsForm | null;
  onReload?: () => void | Promise<void>;
}>();

const { t } = useI18n();
const route = useRoute();
const router = useRouter();

const SERVICE_IDS = new Set(["api", "database", "broker", "worker"]);

const activeServiceId = ref<string | null>(null);

const clock = useProjectClock(
  () => props.status?.server_time ?? null,
  () => props.settings?.timezone ?? props.status?.timezone ?? "UTC",
);

watch(
  () => props.status?.server_time,
  (value) => {
    clock.syncOffset(value ?? null);
  },
);

const SERVICE_LABEL_KEYS: Record<string, string> = {
  api: "settings.project.services.api",
  database: "settings.project.services.database",
  broker: "settings.project.services.broker",
  worker: "settings.project.services.worker",
};

const SERVICE_DESC_KEYS: Record<string, string> = {
  api: "settings.project.services.apiDesc",
  database: "settings.project.services.databaseDesc",
  broker: "settings.project.services.brokerDesc",
  worker: "settings.project.services.workerDesc",
};

const SERVICE_ICONS: Record<string, Component> = {
  api: BoltIcon,
  database: CircleStackIcon,
  broker: QueueListIcon,
  worker: CpuChipIcon,
};

const overallStatus = computed(() => props.status?.overall_status ?? "down");

const healthyCount = computed(() => {
  if (!props.status) {
    return 0;
  }
  return props.status.services.filter((service) => service.status === "ok").length;
});

const totalServices = computed(() => props.status?.services.length ?? 0);

const lastCheckedLabel = computed(() => {
  if (!props.status?.checked_at) {
    return "";
  }
  return formatDateTime(props.status.checked_at);
});

function serviceLabel(service: ServiceHealth) {
  return t(SERVICE_LABEL_KEYS[service.id] ?? service.id);
}

function serviceDescription(service: ServiceHealth) {
  const key = SERVICE_DESC_KEYS[service.id];
  return key ? t(key) : "";
}

function serviceIcon(service: ServiceHealth) {
  return SERVICE_ICONS[service.id] ?? ServerStackIcon;
}

function statusLabel(status: ServiceStatus) {
  return t(`settings.project.status.${status}`);
}

function serviceMeta(service: ServiceHealth) {
  const parts: string[] = [];

  if (service.latency_ms > 0) {
    parts.push(t("settings.project.monitoring.latency", { ms: service.latency_ms }));
  }

  if (service.detail && service.status === "ok") {
    parts.push(service.detail);
  }

  if (service.status !== "ok") {
    if (service.detail && service.detail.length <= 80) {
      parts.push(service.detail);
    } else if (service.detail) {
      parts.push(t("settings.project.monitoring.connectionFailed"));
    }
  }

  return parts.join(" · ");
}

const activeService = computed(() => {
  if (!props.status || !activeServiceId.value) {
    return null;
  }
  return props.status.services.find((service) => service.id === activeServiceId.value) ?? null;
});

function openServiceLogs(serviceId: string) {
  activeServiceId.value = serviceId;
}

function closeServiceLogs() {
  activeServiceId.value = null;
}

function syncServiceQuery() {
  const nextService = activeServiceId.value;
  const currentService = readAllowedQueryValue(route.query.service, [...SERVICE_IDS]);
  if (nextService === currentService) {
    return;
  }
  const query = replaceSettingsQueryParam(route.query, "service", nextService);
  void router.replace({
    name: "settings-general",
    query,
  });
}

function applyServiceFromRoute() {
  const next = readAllowedQueryValue(route.query.service, [...SERVICE_IDS]);
  if (activeServiceId.value === next) {
    return;
  }
  activeServiceId.value = next;
}

watch(activeServiceId, () => {
  syncServiceQuery();
});

watch(
  () => route.query.service,
  () => {
    applyServiceFromRoute();
  },
);

onMounted(() => {
  applyServiceFromRoute();
});
</script>

<template>
  <aside class="settings-panel project-monitor-panel">
    <header class="settings-panel-header project-monitor-header">
      <div class="notify-panel-head">
        <span class="notify-fold-icon project-settings-icon-monitor">
          <ServerStackIcon />
        </span>
        <div>
          <p class="drawer-eyebrow">{{ t("settings.project.monitoring.eyebrow") }}</p>
          <h2 class="settings-panel-title">{{ t("settings.project.monitoring.title") }}</h2>
        </div>
      </div>
    </header>

    <div class="settings-panel-body project-monitor-body">
      <section class="project-monitor-hero">
        <div class="project-monitor-hero-main">
          <p class="project-monitor-hero-label">{{ t("settings.project.monitoring.serverTime") }}</p>
          <p class="project-monitor-hero-time">{{ clock.formattedTime }}</p>
          <p class="project-monitor-hero-date">{{ clock.formattedDate }}</p>
          <p v-if="settings" class="project-monitor-hero-zone">{{ settings.timezone }}</p>
        </div>

        <div v-if="status" class="project-monitor-hero-summary">
          <span
            class="project-monitor-hero-badge"
            :class="`project-monitor-hero-badge-${overallStatus}`"
          >
            {{ statusLabel(overallStatus) }}
          </span>
          <span class="project-monitor-hero-count">
            {{ t("settings.project.monitoring.serviceHealth", { ok: healthyCount, total: totalServices }) }}
          </span>
        </div>
      </section>

      <section class="project-monitor-section">
        <div class="project-monitor-section-head">
          <h3 class="project-monitor-section-title">{{ t("settings.project.monitoring.services") }}</h3>
          <span v-if="lastCheckedLabel" class="project-monitor-section-meta">
            {{ t("settings.project.monitoring.updatedAt", { time: lastCheckedLabel }) }}
          </span>
        </div>

        <p v-if="error" class="project-monitor-error">
          {{ error }}
          <button
            v-if="onReload"
            class="btn btn-secondary mt-2"
            type="button"
            @click="onReload()"
          >
            {{ t("common.retry") }}
          </button>
        </p>

        <div v-else-if="loading" class="project-monitor-loading">
          <span class="loading-spinner" aria-hidden="true" />
          <span>{{ t("common.loading") }}</span>
        </div>

        <Transition v-else mode="out-in" name="project-monitor-swap">
          <ul v-if="status && !activeService" key="monitor-list" class="project-monitor-list">
          <li
            v-for="service in status.services"
            :key="service.id"
            class="project-monitor-service project-monitor-service-clickable"
            :class="`project-monitor-service-${service.status}`"
            role="button"
            tabindex="0"
            :aria-label="t('settings.project.logs.viewLogs', { service: serviceLabel(service) })"
            @click="openServiceLogs(service.id)"
            @keydown.enter.prevent="openServiceLogs(service.id)"
            @keydown.space.prevent="openServiceLogs(service.id)"
          >
            <span class="project-monitor-service-icon" :class="`project-monitor-service-icon-${service.status}`">
              <component :is="serviceIcon(service)" />
            </span>

            <div class="project-monitor-service-body">
              <div class="project-monitor-service-top">
                <div class="project-monitor-service-copy">
                  <span class="project-monitor-service-name">{{ serviceLabel(service) }}</span>
                  <span class="project-monitor-service-desc">{{ serviceDescription(service) }}</span>
                </div>

                <span
                  v-if="service.status !== 'ok'"
                  class="project-monitor-service-badge"
                  :class="`project-monitor-service-badge-${service.status}`"
                >
                  {{ statusLabel(service.status) }}
                </span>
              </div>

              <p v-if="serviceMeta(service)" class="project-monitor-service-meta">
                {{ serviceMeta(service) }}
              </p>
            </div>

            <span class="project-monitor-service-chevron" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 18l6-6-6-6" />
              </svg>
            </span>
          </li>
          </ul>

          <ServiceLogPanel
            v-else-if="activeService"
            key="monitor-logs"
            :service="activeService"
            :service-label="serviceLabel(activeService)"
            @close="closeServiceLogs"
          />
        </Transition>
      </section>
    </div>
  </aside>
</template>
