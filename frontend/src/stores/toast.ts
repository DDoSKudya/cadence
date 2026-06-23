import { defineStore } from "pinia";
import { ref } from "vue";

export type ToastType = "success" | "info" | "error" | "warning";

export interface ToastItem {
  id: number;
  message: string;
  type: ToastType;
}

const DEFAULT_DURATION_MS = 2800;

export const useToastStore = defineStore("toast", () => {
  const items = ref<ToastItem[]>([]);
  let nextId = 0;

  function remove(id: number) {
    items.value = items.value.filter((item) => item.id !== id);
  }

  function show(message: string, options: { type?: ToastType; duration?: number } = {}) {
    const trimmed = message.trim();
    if (!trimmed) {
      return;
    }

    const id = ++nextId;
    const type = options.type ?? "success";
    items.value.push({ id, message: trimmed, type });

    window.setTimeout(() => {
      remove(id);
    }, options.duration ?? DEFAULT_DURATION_MS);
  }

  function success(message: string, duration?: number) {
    show(message, { type: "success", duration });
  }

  function info(message: string, duration?: number) {
    show(message, { type: "info", duration });
  }

  function error(message: string, duration?: number) {
    show(message, { type: "error", duration });
  }

  return {
    items,
    show,
    success,
    info,
    error,
    remove,
  };
});
