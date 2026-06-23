import { t } from "@/i18n";

const PRIORITY_LABEL_KEYS: Record<string, string> = {
  high: "board.priorityHigh",
  normal: "board.priorityNormal",
  low: "board.priorityLow",
};

const SYSTEM_TYPE_LABEL_KEYS: Record<string, string> = {
  backlog: "board.systemBacklog",
  planned: "board.systemTodo",
  in_progress: "board.systemInProgress",
  blocked: "board.systemBlocked",
  review: "board.systemReview",
  done: "board.systemDone",
};

export function priorityLabel(value: string): string {
  const key = PRIORITY_LABEL_KEYS[value];
  return key ? t(key) : value;
}

export function systemTypeLabel(value: string): string {
  const key = SYSTEM_TYPE_LABEL_KEYS[value];
  return key ? t(key) : value;
}
