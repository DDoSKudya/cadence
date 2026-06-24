export const MAX_BOARD_SCHEMES = 4;
export const MAX_BOARD_COLUMNS = 7;
export const MAX_TASK_STATUSES = 20;

export interface BoardLimits {
  max_schemes: number;
  max_columns: number;
  max_task_statuses: number;
}

export const DEFAULT_BOARD_LIMITS: BoardLimits = {
  max_schemes: MAX_BOARD_SCHEMES,
  max_columns: MAX_BOARD_COLUMNS,
  max_task_statuses: MAX_TASK_STATUSES,
};

export const TIMEZONE_OPTIONS = [
  "UTC",
  "Europe/London",
  "Europe/Berlin",
  "Europe/Moscow",
  "Asia/Tbilisi",
  "Asia/Almaty",
  "Asia/Yekaterinburg",
  "Asia/Novosibirsk",
  "America/New_York",
  "America/Chicago",
  "America/Los_Angeles",
] as const;

export const COLUMN_SYSTEM_TYPES = [
  "backlog",
  "planned",
  "in_progress",
  "blocked",
  "review",
  "ready",
  "done",
] as const;

export type ColumnSystemType = (typeof COLUMN_SYSTEM_TYPES)[number];
