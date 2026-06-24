import type { BoardLimits } from "@/features/settings/constants";
import type { ColumnMeta } from "@/shared/types/column";

export type SettingsColumn = ColumnMeta;

export interface BoardScheme {
  slug: string;
  name: string;
  description: string;
  is_locked: boolean;
}

export interface ColumnsListResponse {
  scheme: BoardScheme | null;
  columns: SettingsColumn[];
  limits: BoardLimits;
}

export interface BoardSchemesResponse {
  schemes: BoardScheme[];
  limits: BoardLimits;
}
