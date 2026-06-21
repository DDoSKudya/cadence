import { describe, expect, it } from "vitest";

import {
  colorToHex,
  columnDotStyle,
  columnHeaderStyle,
  isHexColor,
} from "./column-color";

describe("column-color", () => {
  it("resolves preset colors to hex", () => {
    expect(colorToHex("orange")).toBe("#f97316");
    expect(colorToHex("blue")).toBe("#3b82f6");
    expect(colorToHex("unknown")).toBe("#64748b");
  });

  it("normalizes custom hex colors", () => {
    expect(colorToHex("#AABBCC")).toBe("#aabbcc");
    expect(isHexColor("#aabbcc")).toBe(true);
    expect(isHexColor("orange")).toBe(false);
  });

  it("builds inline styles from the same hex source", () => {
    expect(columnDotStyle("orange")).toEqual({ background: "#f97316" });
    expect(columnHeaderStyle("orange")).toEqual({ borderTopColor: "#f97316" });
  });
});
