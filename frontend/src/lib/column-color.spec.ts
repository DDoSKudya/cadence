import { describe, expect, it } from "vitest";

import {
  colorSwatchClass,
  colorToHex,
  columnDotStyle,
  isHexColor,
} from "./column-color";

describe("column-color EC", () => {
  it.each([
    ["#AABBCC", true, "ec_hex_uppercase"],
    ["#aabbcc", true, "ec_hex_lowercase"],
    ["blue", false, "ec_preset_name"],
    ["#abc", false, "ec_short_hex"],
  ])("ec_is_hex_color: %s", (value, expected) => {
    expect(isHexColor(value)).toBe(expected);
  });

  it("ec_color_to_hex_preserves_hex", () => {
    expect(colorToHex("#AABBCC")).toBe("#aabbcc");
  });

  it("ec_color_to_hex_maps_preset", () => {
    expect(colorToHex("blue")).toBe("#3b82f6");
  });

  it("ec_color_to_hex_unknown_falls_back_to_slate", () => {
    expect(colorToHex("unknown")).toBe("#64748b");
  });

  it("ec_color_swatch_class_hex_returns_empty", () => {
    expect(colorSwatchClass("#112233")).toBe("");
  });

  it("ec_color_swatch_class_preset_returns_class", () => {
    expect(colorSwatchClass("teal")).toBe("color-swatch-teal");
  });

  it("ec_column_dot_style_uses_resolved_hex", () => {
    expect(columnDotStyle("red")).toEqual({ background: "#ef4444" });
  });
});
