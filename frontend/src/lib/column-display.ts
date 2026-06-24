import { t } from "@/i18n";

const LOCKED_COLUMN_LABEL_KEYS: Record<string, string> = {
  backlog: "board.systemBacklog",
  planned: "board.systemTodo",
  in_progress: "board.systemInProgress",
  blocked: "board.systemBlocked",
  review: "board.systemReview",
  ready: "board.systemReady",
  done: "board.systemDone",
};

export function columnDisplayName(column: {
  name: string;
  system_type: string;
  is_locked?: boolean;
}): string {
  if (column.is_locked) {
    const key = LOCKED_COLUMN_LABEL_KEYS[column.system_type];
    if (key) {
      return t(key);
    }
  }
  return column.name;
}

export function boardDisplayName(board: {
  name: string;
  is_default?: boolean;
}): string {
  if (board.is_default) {
    return t("board.defaultName");
  }
  return board.name;
}
