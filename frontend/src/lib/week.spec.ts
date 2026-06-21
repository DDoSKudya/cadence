import { describe, expect, it } from "vitest";

import { formatWeekKey, getCurrentWeekKey, parseWeekKey, shiftWeekKey, weekLabel } from "./week";

describe("week", () => {
  it("formats and parses week keys", () => {
    const key = formatWeekKey({ isoYear: 2026, isoWeek: 5 });
    expect(key).toBe("2026-W05");
    expect(parseWeekKey(key)).toEqual({ isoYear: 2026, isoWeek: 5 });
  });

  it("shifts weeks", () => {
    expect(shiftWeekKey("2026-W05", 1)).toBe("2026-W06");
    expect(shiftWeekKey("2026-W01", -1)).toBe("2025-W52");
  });

  it("builds readable labels", () => {
    expect(weekLabel("2026-W05")).toBe("2026 · W05");
  });

  it("derives current week key from date", () => {
    expect(getCurrentWeekKey(new Date("2026-02-02T12:00:00"))).toBe("2026-W06");
  });
});
