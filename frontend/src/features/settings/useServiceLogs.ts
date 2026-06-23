import { onUnmounted, ref, watch, type Ref } from "vue";

import { fetchServiceLogs, type ServiceLogEntry, type ServiceLogsResponse } from "@/features/settings/platform-api";

const POLL_INTERVAL_MS = 5000;

export function useServiceLogs(serviceId: Ref<string | null>) {
  const entries = ref<ServiceLogEntry[]>([]);
  const hasFile = ref(false);
  const loading = ref(false);
  const error = ref("");
  let pollTimer: ReturnType<typeof setInterval> | null = null;

  async function load() {
    if (!serviceId.value) {
      return;
    }

    loading.value = entries.value.length === 0;
    error.value = "";

    try {
      const response: ServiceLogsResponse = await fetchServiceLogs(serviceId.value);
      entries.value = response.entries;
      hasFile.value = response.has_file;
    } catch (loadError) {
      error.value = loadError instanceof Error ? loadError.message : String(loadError);
    } finally {
      loading.value = false;
    }
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  watch(
    serviceId,
    (value) => {
      stopPolling();
      entries.value = [];
      hasFile.value = false;
      error.value = "";

      if (!value) {
        return;
      }

      void load();
      pollTimer = setInterval(() => {
        void load();
      }, POLL_INTERVAL_MS);
    },
    { immediate: true },
  );

  onUnmounted(stopPolling);

  return {
    entries,
    hasFile,
    loading,
    error,
    reload: load,
  };
}
