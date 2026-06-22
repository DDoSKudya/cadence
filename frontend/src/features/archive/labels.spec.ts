import { describe, expect, it } from "vitest";

import { actorLabel, eventTypeLabel, sourceLabel } from "./labels";

describe("archive labels", () => {
  it("maps event types to Russian labels", () => {
    expect(eventTypeLabel("closed")).toBe("Закрыта");
    expect(eventTypeLabel("notification_sent")).toBe("Уведомление");
    expect(eventTypeLabel("unknown")).toBe("unknown");
  });

  it("maps actors and sources", () => {
    expect(actorLabel("system")).toBe("Система");
    expect(sourceLabel("json_import")).toBe("JSON");
  });
});
