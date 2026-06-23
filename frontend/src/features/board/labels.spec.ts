import { describe, expect, it } from "vitest";

import { priorityLabel, systemTypeLabel } from "./labels";

describe("board labels EC", () => {
  it.each([
    ["high", "High"],
    ["normal", "Normal"],
    ["low", "Low"],
  ])("ec_priority_label_valid: %s", (value, label) => {
    expect(priorityLabel(value)).toBe(label);
  });

  it("ec_priority_label_unknown_returns_value", () => {
    expect(priorityLabel("urgent")).toBe("urgent");
  });

  it.each([
    ["backlog", "Backlog"],
    ["done", "Done"],
  ])("ec_system_type_label_valid: %s", (value, label) => {
    expect(systemTypeLabel(value)).toBe(label);
  });

  it("ec_system_type_label_unknown_returns_value", () => {
    expect(systemTypeLabel("custom")).toBe("custom");
  });
});
