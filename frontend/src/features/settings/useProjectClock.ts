import { computed, onMounted, onUnmounted, ref } from "vue";

export function useProjectClock(serverTimeIso: () => string | null, timezone: () => string) {
  const tick = ref(Date.now());
  const serverOffsetMs = ref(0);
  let timer: number | undefined;

  function syncOffset(serverTime: string | null) {
    if (!serverTime) {
      serverOffsetMs.value = 0;
      return;
    }
    const parsed = Date.parse(serverTime);
    if (Number.isNaN(parsed)) {
      serverOffsetMs.value = 0;
      return;
    }
    serverOffsetMs.value = parsed - Date.now();
  }

  const now = computed(() => new Date(tick.value + serverOffsetMs.value));

  const formattedTime = computed(() => {
    const locale = document.documentElement.lang === "ru" ? "ru-RU" : "en-US";
    return new Intl.DateTimeFormat(locale, {
      timeZone: timezone(),
      weekday: "short",
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(now.value);
  });

  const formattedDate = computed(() => {
    const locale = document.documentElement.lang === "ru" ? "ru-RU" : "en-US";
    return new Intl.DateTimeFormat(locale, {
      timeZone: timezone(),
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
    }).format(now.value);
  });

  onMounted(() => {
    syncOffset(serverTimeIso());
    timer = window.setInterval(() => {
      tick.value = Date.now();
    }, 1000);
  });

  onUnmounted(() => {
    if (timer !== undefined) {
      window.clearInterval(timer);
    }
  });

  return {
    formattedTime,
    formattedDate,
    syncOffset,
  };
}
