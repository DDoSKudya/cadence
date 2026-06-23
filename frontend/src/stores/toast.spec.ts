import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useToastStore } from "@/stores/toast";

describe("toast store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  it("queues and auto-dismisses success toasts", () => {
    const toast = useToastStore();

    toast.success("Saved");
    expect(toast.items).toHaveLength(1);
    expect(toast.items[0]?.message).toBe("Saved");

    vi.advanceTimersByTime(2800);
    expect(toast.items).toHaveLength(0);
  });

  it("ignores empty messages", () => {
    const toast = useToastStore();

    toast.success("   ");
    expect(toast.items).toHaveLength(0);
  });
});
