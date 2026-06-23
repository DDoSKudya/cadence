import { onMounted, onUnmounted, ref } from "vue";

import { t } from "@/i18n";
import { fetchPlatformStatus, type PlatformStatus } from "@/features/settings/platform-api";

const POLL_INTERVAL_MS = 30_000;

export function usePlatformStatus() {
  const status = ref<PlatformStatus | null>(null);
  const loading = ref(true);
  const error = ref("");

  let pollTimer: number | undefined;

  async function load(options: { silent?: boolean } = {}) {
    if (!options.silent) {
      loading.value = true;
    }
    error.value = "";

    try {
      status.value = await fetchPlatformStatus();
    } catch (loadError) {
      error.value =
        loadError instanceof Error ? loadError.message : t("settings.project.monitoring.loadFailed");
    } finally {
      loading.value = false;
    }
  }

  function startPolling() {
    stopPolling();
    pollTimer = window.setInterval(() => {
      void load({ silent: true });
    }, POLL_INTERVAL_MS);
  }

  function stopPolling() {
    if (pollTimer !== undefined) {
      window.clearInterval(pollTimer);
      pollTimer = undefined;
    }
  }

  onMounted(() => {
    void load();
    startPolling();
  });

  onUnmounted(stopPolling);

  return {
    status,
    loading,
    error,
    reload: () => load(),
  };
}
