import { describe, expect, it } from "vitest";

import {
  actorLabel,
  columnStatusLabel,
  eventTone,
  eventTypeLabel,
  sourceLabel,
  systemTypeDotStyle,
} from "./labels";

describe("archive labels EC", () => {
  it("ec_known_event_type_label", () => {
    expect(eventTypeLabel("closed")).toBe("Task closed");
  });

  it("ec_unknown_event_type_returns_value", () => {
    expect(eventTypeLabel("custom")).toBe("custom");
  });

  it("ec_event_tone_known_and_default", () => {
    expect(eventTone("closed")).toBe("closed");
    expect(eventTone("custom")).toBe("neutral");
  });

  it("ec_actor_and_source_labels", () => {
    expect(actorLabel("telegram")).toBe("Telegram");
    expect(sourceLabel("json_import")).toBe("JSON import");
    expect(actorLabel("other")).toBe("other");
  });

  it("ec_column_status_prefers_name_over_system_type", () => {
    expect(columnStatusLabel("planned", "My plan")).toBe("My plan");
    expect(columnStatusLabel("planned", "")).toBe("To do");
  });

  it("ec_system_type_dot_style_known_and_default", () => {
    expect(systemTypeDotStyle("done")).toEqual({ background: "#22c55e" });
    expect(systemTypeDotStyle("custom")).toEqual({ background: "#64748b" });
  });
});
