import { t } from "@/i18n";

import type { TaskLinkType, TaskType } from "./types";

const PRIORITY_LABEL_KEYS: Record<string, string> = {
  high: "board.priorityHigh",
  normal: "board.priorityNormal",
  low: "board.priorityLow",
};

const TASK_TYPE_LABEL_KEYS: Record<TaskType, string> = {
  epic: "board.taskTypeEpic",
  story: "board.taskTypeStory",
  task: "board.taskTypeTask",
  bug: "board.taskTypeBug",
};

const LINK_TYPE_OUTGOING_KEYS: Record<TaskLinkType, string> = {
  relates: "board.linkRelates",
  blocks: "board.linkBlocks",
  duplicates: "board.linkDuplicates",
};

const LINK_TYPE_INCOMING_KEYS: Record<TaskLinkType, string> = {
  relates: "board.linkRelatesIncoming",
  blocks: "board.linkBlockedBy",
  duplicates: "board.linkDuplicatesIncoming",
};

const SYSTEM_TYPE_LABEL_KEYS: Record<string, string> = {
  backlog: "board.systemBacklog",
  planned: "board.systemTodo",
  in_progress: "board.systemInProgress",
  blocked: "board.systemBlocked",
  review: "board.systemReview",
  ready: "board.systemReady",
  done: "board.systemDone",
};

export function priorityLabel(value: string): string {
  const key = PRIORITY_LABEL_KEYS[value];
  return key ? t(key) : value;
}

export function taskTypeLabel(value: TaskType | string): string {
  const key = TASK_TYPE_LABEL_KEYS[value as TaskType];
  return key ? t(key) : value;
}

export function linkTypeLabel(
  linkType: TaskLinkType | string,
  direction: "outgoing" | "incoming",
): string {
  const keys = direction === "incoming" ? LINK_TYPE_INCOMING_KEYS : LINK_TYPE_OUTGOING_KEYS;
  const key = keys[linkType as TaskLinkType];
  return key ? t(key) : linkType;
}

export const TASK_TYPE_OPTIONS: TaskType[] = ["epic", "story", "task", "bug"];
export const LINK_TYPE_OPTIONS: TaskLinkType[] = ["relates", "blocks", "duplicates"];

export function systemTypeLabel(value: string): string {
  const key = SYSTEM_TYPE_LABEL_KEYS[value];
  return key ? t(key) : value;
}
