import type { ServiceLogEntry } from "@/features/settings/platform-api";

export function serviceLogLevelClass(level: string) {
  const normalized = level.toLowerCase();
  if (normalized === "error" || normalized === "critical") {
    return "error";
  }
  if (normalized === "warning") {
    return "warning";
  }
  if (normalized === "debug") {
    return "debug";
  }
  return "info";
}

export function resolveServiceLogTimestamp(entry: ServiceLogEntry) {
  if (entry.logged_at) {
    return entry.logged_at;
  }

  const bracket = entry.message.match(/^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]/);
  if (bracket) {
    return bracket[1];
  }

  const plain = entry.message.match(/^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})/);
  if (plain) {
    return plain[1];
  }

  return "";
}

export function formatServiceLogTime(value: string) {
  if (!value) {
    return "—";
  }

  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(,\d{3})?$/.test(value)) {
    return value.slice(11, 19);
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatServiceLogFullTime(value: string) {
  if (!value) {
    return "—";
  }

  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}$/.test(value)) {
    return value.replace(",", ".");
  }

  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)) {
    return value;
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

export function formatServiceLogMetaLine(
  entry: ServiceLogEntry,
  sourceLabel: string,
): string {
  const timestamp = resolveServiceLogTimestamp(entry);
  const parts: string[] = [formatServiceLogTime(timestamp)];

  if (entry.job_id) {
    parts.push(`#${entry.job_id}`);
  }

  parts.push(sourceLabel);
  return parts.join(" · ");
}

export function parseWorkerJobLogMessage(message: string) {
  const match = message.match(/^Job #(\d+) ([\w_]+)(?: (.+))?$/);
  if (!match) {
    return null;
  }

  const [, id, jobType, tail] = match;
  let status = "info";
  if (tail?.startsWith("failed")) {
    status = "failed";
  } else if (tail?.startsWith("succeeded")) {
    status = "succeeded";
  } else if (tail?.startsWith("processing")) {
    status = "processing";
  } else if (tail?.startsWith("pending")) {
    status = "pending";
  } else if (tail?.startsWith("cancelled")) {
    status = "cancelled";
  }

  return { id: Number(id), jobType, status };
}

export function stripServiceLogFilePrefix(message: string) {
  const stripped = message.replace(
    /^(?:\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]|\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \w+ /,
    "",
  );
  if (stripped !== message) {
    return stripped;
  }

  const separator = message.indexOf(": ");
  if (separator >= 0) {
    return message.slice(separator + 2);
  }

  return message;
}
