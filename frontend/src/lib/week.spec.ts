import { describe, expect, it } from "vitest";

import {
  formatWeekKey,
  getCurrentWeekKey,
  parseWeekKey,
  shiftWeekKey,
  weekLabel,
} from "./week";

describe("week EC", () => {
  it("ec_valid_week_key_parses", () => {
    expect(parseWeekKey("2024-W09")).toEqual({ isoYear: 2024, isoWeek: 9 });
  });

  it.each([
    ["", "ec_empty_string"],
    ["2024-W00", "ec_week_zero"],
    ["bad", "ec_non_matching"],
    ["2024-W99", "ec_invalid_week_number"],
  ])("ec_invalid_week_key_rejects: %s", (value) => {
    expect(() => parseWeekKey(value)).toThrow("Invalid week key");
  });

  it("ec_format_week_key_zero_pads_week", () => {
    expect(formatWeekKey({ isoYear: 2024, isoWeek: 3 })).toBe("2024-W03");
  });

  it("ec_shift_week_key_positive_delta", () => {
    expect(shiftWeekKey("2024-W10", 1)).toBe("2024-W11");
  });

  it("ec_shift_week_key_negative_delta", () => {
    expect(shiftWeekKey("2024-W10", -1)).toBe("2024-W09");
  });

  it("ec_get_current_week_key_returns_iso_format", () => {
    expect(getCurrentWeekKey(new Date("2024-03-04T12:00:00Z"))).toMatch(/^\d{4}-W\d{2}$/);
  });

  it("ec_week_label_formats_display", () => {
    expect(weekLabel("2024-W09")).toBe("2024 · W09");
  });
});
