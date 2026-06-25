import { t } from "@/i18n";
import { useToastStore } from "@/stores/toast";

const DEFAULT_ERROR_DURATION_MS = 5000;

export function useActionFeedback() {
  const toast = useToastStore();

  function success(message: string, duration?: number) {
    toast.success(message, duration);
  }

  function successKey(key: string, params?: Record<string, unknown>, duration?: number) {
    success(t(key, params), duration);
  }

  function error(message: string, duration = DEFAULT_ERROR_DURATION_MS) {
    toast.error(message, duration);
  }

  function errorKey(key: string, params?: Record<string, unknown>, duration = DEFAULT_ERROR_DURATION_MS) {
    error(t(key, params), duration);
  }

  function fromError(err: unknown, fallbackKey: string) {
    const fallback = t(fallbackKey);
    if (!(err instanceof Error) || !err.message.trim()) {
      error(fallback);
      return;
    }
    error(err.message);
  }

  return {
    success,
    successKey,
    error,
    errorKey,
    fromError,
  };
}
