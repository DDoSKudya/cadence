import { describe, expect, it } from "vitest";

import { formatDateTime, formatDateTimeLong } from "./datetime";

describe("datetime", () => {
  it("formats compact datetime with year", () => {
    const formatted = formatDateTime("2024-06-22T04:44:00Z");
    expect(formatted).toMatch(/2024/);
    expect(formatted).toMatch(/22/);
    expect(formatted).toMatch(/июн/i);
  });

  it("formats long datetime with year", () => {
    const formatted = formatDateTimeLong("2024-06-22T04:44:00Z");
    expect(formatted).toMatch(/2024/);
    expect(formatted).toMatch(/июн/i);
  });

  it("returns dash for empty values", () => {
    expect(formatDateTime(null)).toBe("—");
    expect(formatDateTime("")).toBe("—");
  });
});
