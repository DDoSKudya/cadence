import { describe, expect, it } from "vitest";

import { fromLocalInput, toLocalInput } from "./task-form";

describe("task-form EC", () => {
  it("ec_to_local_input_null_returns_empty", () => {
    expect(toLocalInput(null)).toBe("");
  });

  it("ec_to_local_input_iso_returns_datetime_local_slice", () => {
    const value = toLocalInput("2024-06-15T10:30:00.000Z");
    expect(value).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/);
  });

  it("ec_from_local_input_empty_returns_null", () => {
    expect(fromLocalInput("")).toBeNull();
    expect(fromLocalInput("   ")).toBeNull();
  });

  it("ec_from_local_input_value_returns_iso", () => {
    const iso = fromLocalInput("2024-06-15T10:30");
    expect(iso).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
  });
});
