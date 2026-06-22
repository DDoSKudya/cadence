import { systemTypeLabel } from "@/features/board/labels";

const EVENT_LABELS: Record<string, string> = {
  created: "Создана",
  updated: "Обновлена",
  moved: "Перемещена",
  closed: "Закрыта",
  archived: "В архиве",
  reopened: "Возвращена",
  reminder_scheduled: "Напоминание",
  notification_sent: "Уведомление",
  telegram_action: "Telegram",
  imported: "Импорт",
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

const ACTOR_LABELS: Record<string, string> = {
  user: "Пользователь",
  api: "API",
  import: "Импорт",
  telegram: "Telegram",
  system: "Система",
};

const SOURCE_LABELS: Record<string, string> = {
  ui: "UI",
  api: "API",
  json_import: "JSON",
  telegram: "Telegram",
  system: "Система",
};

export function eventTypeLabel(value: string): string {
  return EVENT_LABELS[value] ?? value;
}

export function eventTone(value: string): string {
  return EVENT_TONE[value] ?? "neutral";
}

export function actorLabel(value: string): string {
  return ACTOR_LABELS[value] ?? value;
}

export function sourceLabel(value: string): string {
  return SOURCE_LABELS[value] ?? value;
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
