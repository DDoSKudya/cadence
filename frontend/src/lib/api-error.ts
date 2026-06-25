import { t } from "@/i18n";
import {
  translateColumnLabel,
  translateStatusLabel,
  translateTaskFieldList,
} from "@/lib/workflow-labels";

type ApiErrorRecord = Record<string, unknown>;

const DETAIL_CODE_MAP: Record<string, string> = {
  "Task status transition is not allowed.": "status_transition_not_allowed",
  "Task cannot be moved to this column with the current status.":
    "status_column_move_not_allowed",
  "Transition from this column is not allowed.": "transition_not_allowed",
  "Task in a terminal status cannot be moved.": "status_terminal",
  "This status can only be assigned when a task is created.": "status_creation_only",
  "Task is missing required fields for this status change.": "status_required_fields",
  "Archived task cannot be updated.": "task_archived",
  "Archived task cannot be moved.": "task_archived",
  "Task is already closed.": "task_already_closed",
};

function translateApiErrorCode(record: ApiErrorRecord): string | null {
  const code =
    (typeof record.code === "string" ? record.code : null) ||
    (typeof record.detail === "string" ? DETAIL_CODE_MAP[record.detail] : null);
  if (!code) {
    return null;
  }

  const key = `errors.api.${code}`;
  const missingFields = Array.isArray(record.missing_fields)
    ? record.missing_fields.filter((field): field is string => typeof field === "string")
    : [];
  const fromStatus = translateStatusLabel(
    typeof record.from_status === "string" ? record.from_status : "",
    typeof record.from_status_slug === "string" ? record.from_status_slug : null,
  );
  const toStatus = translateStatusLabel(
    typeof record.to_status === "string" ? record.to_status : "",
    typeof record.to_status_slug === "string" ? record.to_status_slug : null,
  );
  const toColumn = translateColumnLabel(
    typeof record.to_column === "string" ? record.to_column : "",
    typeof record.to_column_type === "string" ? record.to_column_type : null,
  );

  const translated = t(key, {
    fields: translateTaskFieldList(missingFields),
    from: fromStatus,
    to: toStatus,
    column: toColumn,
  });
  if (translated !== key) {
    return translated;
  }
  return null;
}

export function formatApiErrorBody(data: unknown, fallback: string): string {
  if (typeof data === "string" && data.trim()) {
    const mapped = DETAIL_CODE_MAP[data];
    if (mapped) {
      const translated = translateApiErrorCode({ code: mapped, detail: data });
      if (translated) {
        return translated;
      }
    }
    return data;
  }
  if (!data || typeof data !== "object") {
    return fallback;
  }

  const record = data as ApiErrorRecord;
  const translated = translateApiErrorCode(record);
  if (translated) {
    return translated;
  }

  if (typeof record.detail === "string" && record.detail.trim()) {
    return record.detail;
  }

  const firstField = Object.values(record).find(
    (value) => Array.isArray(value) && typeof value[0] === "string",
  ) as string[] | undefined;
  if (firstField?.[0]) {
    return firstField[0];
  }

  return fallback;
}

export async function readApiError(response: Response, fallback: string): Promise<string> {
  try {
    const data = await response.json();
    return formatApiErrorBody(data, fallback);
  } catch {
    return fallback;
  }
}
