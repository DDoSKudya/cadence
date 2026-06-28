import { t } from "@/i18n";

const STATUS_SLUG_ALIASES: Record<string, string> = {
  open: "open",
  ready_on_develop: "ready_on_develop",
  process: "process",
  testing: "testing",
  done: "done",
  cancel: "cancel",
};

const STATUS_NAME_TO_SLUG: Record<string, string> = {
  Open: "open",
  "Ready on develop": "ready_on_develop",
  "In progress": "process",
  "In process": "process",
  Process: "process",
  Testing: "testing",
  Done: "done",
  Cancel: "cancel",
};

const COLUMN_SYSTEM_TYPE_KEYS: Record<string, string> = {
  backlog: "board.systemBacklog",
  planned: "board.systemTodo",
  in_progress: "board.systemInProgress",
  blocked: "board.systemBlocked",
  review: "board.systemReview",
  ready: "board.systemReady",
  done: "board.systemDone",
};

const COLUMN_NAME_TO_SYSTEM_TYPE: Record<string, string> = {
  Backlog: "backlog",
  Planned: "planned",
  "Work in progress": "in_progress",
  "In progress": "in_progress",
  Ready: "ready",
  Done: "done",
};

const TASK_FIELD_KEYS: Record<string, string> = {
  title: "common.title",
  description: "common.description",
  due_at: "board.dueDate",
};

function translateByKey(key: string, fallback: string): string {
  const translated = t(key);
  return translated === key ? fallback : translated;
}

export function translateStatusLabel(
  slugOrName: string | null | undefined,
  explicitSlug?: string | null,
): string {
  const slug =
    explicitSlug?.trim() ||
    STATUS_SLUG_ALIASES[slugOrName ?? ""] ||
    STATUS_NAME_TO_SLUG[slugOrName ?? ""];
  if (slug) {
    return translateByKey(`workflow.status.${slug}`, slugOrName ?? slug);
  }
  return slugOrName?.trim() || "";
}

export function statusDisplayName(status: {
  name: string;
  slug?: string | null;
}): string {
  return translateStatusLabel(status.name, status.slug);
}

export function translateColumnLabel(
  nameOrType: string | null | undefined,
  explicitSystemType?: string | null,
): string {
  const systemType = explicitSystemType?.trim() || COLUMN_NAME_TO_SYSTEM_TYPE[nameOrType ?? ""];
  if (systemType && COLUMN_SYSTEM_TYPE_KEYS[systemType]) {
    return translateByKey(COLUMN_SYSTEM_TYPE_KEYS[systemType], nameOrType ?? systemType);
  }
  if (nameOrType && COLUMN_SYSTEM_TYPE_KEYS[nameOrType]) {
    return translateByKey(COLUMN_SYSTEM_TYPE_KEYS[nameOrType], nameOrType);
  }
  return nameOrType?.trim() || "";
}

export function translateTaskFieldLabel(field: string): string {
  const key = TASK_FIELD_KEYS[field];
  if (!key) {
    return field;
  }
  return translateByKey(key, field);
}

export function translateTaskFieldList(fields: string[]): string {
  return fields.map(translateTaskFieldLabel).join(", ");
}
