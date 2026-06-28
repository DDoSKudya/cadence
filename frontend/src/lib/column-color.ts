import { t } from "@/i18n";

export interface ColumnColorOption {
  value: string;
  label: string;
}

const COLUMN_COLOR_VALUES = [
  "slate",
  "blue",
  "indigo",
  "teal",
  "green",
  "amber",
  "orange",
  "red",
];

export function columnColorOptions(): ColumnColorOption[] {
  return COLUMN_COLOR_VALUES.map((value) => ({
    value,
    label: t(`colors.${value}`),
  }));
}

const PRESET_HEX: Record<string, string> = {
  slate: "#64748b",
  blue: "#3b82f6",
  indigo: "#6366f1",
  teal: "#14b8a6",
  green: "#22c55e",
  amber: "#f59e0b",
  orange: "#f97316",
  red: "#ef4444",
};

export function isHexColor(color: string): boolean {
  return /^#[0-9a-f]{6}$/i.test(color.trim());
}

export function colorToHex(color: string): string {
  if (isHexColor(color)) {
    return color.trim().toLowerCase();
  }
  return PRESET_HEX[color.trim().toLowerCase()] ?? PRESET_HEX.slate;
}

export function colorSwatchClass(color: string): string {
  if (isHexColor(color)) {
    return "";
  }
  const key = color.trim().toLowerCase();
  return PRESET_HEX[key] ? `color-swatch-${key}` : "color-swatch-slate";
}

export function columnDotStyle(color: string): Record<string, string> {
  return { background: colorToHex(color) };
}

export function columnHeaderStyle(color: string): Record<string, string> {
  return { borderTopColor: colorToHex(color) };
}

export function columnCountStyle(color: string): Record<string, string> {
  const hex = colorToHex(color);
  return {
    color: hex,
    background: `color-mix(in srgb, ${hex} 16%, white)`,
  };
}

export function columnPreviewLaneStyle(color: string): Record<string, string> {
  return { borderTopColor: colorToHex(color) };
}

export function tagChipStyle(color: string): Record<string, string> {
  const hex = colorToHex(color);
  return {
    "--tag-chip-border": `color-mix(in srgb, ${hex} 38%, white)`,
    "--tag-chip-bg": `color-mix(in srgb, ${hex} 14%, white)`,
    "--tag-chip-text": `color-mix(in srgb, ${hex} 72%, #1e293b)`,
  };
}
