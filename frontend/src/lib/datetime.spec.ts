import { describe, expect, it } from "vitest";

import { formatDateTime, formatDateTimeLong } from "./datetime";

describe("datetime EC", () => {
  it.each([
    [null, "ec_null_value"],
    [undefined, "ec_undefined_value"],
    ["", "ec_empty_string"],
  ])("ec_missing_datetime_returns_dash: %s", (value, _caseId) => {
    expect(formatDateTime(value)).toBe("—");
    expect(formatDateTimeLong(value)).toBe("—");
  });

  it("ec_invalid_datetime_returns_original", () => {
    expect(formatDateTime("not-a-date")).toBe("not-a-date");
  });

  it("ec_valid_iso_datetime_formats_active_locale", () => {
    const formatted = formatDateTime("2024-06-15T10:30:00Z");
    expect(formatted).toContain("2024");
    expect(formatted).not.toBe("—");
  });
});
