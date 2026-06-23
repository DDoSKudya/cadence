import { systemTypeLabel } from "@/features/board/labels";
import { t } from "@/i18n";

const EVENT_LABEL_KEYS: Record<string, string> = {
  created: "archive.eventTaskCreated",
  updated: "archive.eventTaskUpdated",
  moved: "archive.eventTaskMoved",
  closed: "archive.eventTaskClosed",
  archived: "archive.eventTaskArchived",
  reopened: "archive.eventTaskReopened",
  reminder_scheduled: "archive.eventReminderScheduled",
  notification_sent: "archive.eventNotificationSent",
  telegram_action: "archive.eventTelegramAction",
  imported: "archive.eventImported",
};

const EVENT_TONE: Record<string, string> = {
  created: "created",
  updated: "neutral",
  moved: "moved",
  closed: "closed",
  archived: "closed",
  reopened: "reopened",
  reminder_scheduled: "reminder",
  notification_sent: "notify",
  telegram_action: "telegram",
  imported: "import",
};

const ACTOR_LABEL_KEYS: Record<string, string> = {
  user: "archive.actorUser",
  import: "imports.title",
  system: "archive.actorSystem",
};

const ACTOR_LITERALS: Record<string, string> = {
  api: "API",
  telegram: "Telegram",
};

const SOURCE_LABEL_KEYS: Record<string, string> = {
  json_import: "archive.sourceJsonImport",
  system: "archive.actorSystem",
};

const SOURCE_LITERALS: Record<string, string> = {
  ui: "UI",
  api: "API",
  telegram: "Telegram",
};

export function eventTypeLabel(value: string): string {
  const key = EVENT_LABEL_KEYS[value];
  return key ? t(key) : value;
}

export function eventTone(value: string): string {
  return EVENT_TONE[value] ?? "neutral";
}

export function actorLabel(value: string): string {
  const literal = ACTOR_LITERALS[value];
  if (literal) {
    return literal;
  }
  const key = ACTOR_LABEL_KEYS[value];
  return key ? t(key) : value;
}

export function sourceLabel(value: string): string {
  const literal = SOURCE_LITERALS[value];
  if (literal) {
    return literal;
  }
  const key = SOURCE_LABEL_KEYS[value];
  return key ? t(key) : value;
}

export function columnStatusLabel(systemType: string, name: string): string {
  if (name.trim()) {
    return name;
  }
  return systemTypeLabel(systemType);
}

const SYSTEM_TYPE_COLORS: Record<string, string> = {
  backlog: "#64748b",
  planned: "#3b82f6",
  in_progress: "#6366f1",
  blocked: "#ef4444",
  review: "#f59e0b",
  done: "#22c55e",
};

export function systemTypeDotStyle(systemType: string): Record<string, string> {
  return { background: SYSTEM_TYPE_COLORS[systemType] ?? "#64748b" };
}
