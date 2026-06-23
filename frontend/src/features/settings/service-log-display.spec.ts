import { describe, expect, it } from "vitest";

import type { ServiceLogEntry } from "@/features/settings/platform-api";
import {
  formatServiceLogFullTime,
  formatServiceLogMetaLine,
  formatServiceLogTime,
  parseWorkerJobLogMessage,
  resolveServiceLogTimestamp,
  serviceLogLevelClass,
  stripServiceLogFilePrefix,
} from "@/features/settings/service-log-display";

function entry(overrides: Partial<ServiceLogEntry> = {}): ServiceLogEntry {
  return {
    logged_at: "",
    level: "INFO",
    message: "plain message",
    source: "process",
    ...overrides,
  };
}

describe("service-log-display EC", () => {
  it.each([
    ["INFO", "info"],
    ["WARNING", "warning"],
    ["ERROR", "error"],
    ["CRITICAL", "error"],
    ["DEBUG", "debug"],
  ])("ec_level_class: %s", (level, expected) => {
    expect(serviceLogLevelClass(level)).toBe(expected);
  });

  it("ec_resolve_timestamp_prefers_logged_at", () => {
    expect(
      resolveServiceLogTimestamp(
        entry({ logged_at: "2026-06-01T10:00:00Z", message: "[2026-06-01 12:00:00] INFO" }),
      ),
    ).toBe("2026-06-01T10:00:00Z");
  });

  it.each([
    ["[2026-06-01 12:00:00] INFO msg", "2026-06-01 12:00:00"],
    ["2026-06-01 12:00:00,123 INFO msg", "2026-06-01 12:00:00,123"],
    ["no timestamp", ""],
  ])("ec_resolve_timestamp_from_message: %s", (message, expected) => {
    expect(resolveServiceLogTimestamp(entry({ message, logged_at: "" }))).toBe(expected);
  });

  it.each([
    ["2026-06-01 12:00:00,123", "12:00:00"],
    ["", "—"],
  ])("ec_format_service_log_time: %s", (value, expected) => {
    expect(formatServiceLogTime(value)).toBe(expected);
  });

  it("ec_format_meta_line_joins_time_source_and_job", () => {
    expect(
      formatServiceLogMetaLine(
        entry({
          logged_at: "2026-06-01 12:00:00,123",
          source: "health",
          job_id: 7,
        }),
        "Проверка",
      ),
    ).toBe("12:00:00 · #7 · Проверка");

    expect(
      formatServiceLogMetaLine(
        entry({ logged_at: "", message: "2026-06-23 16:56:06,123 INFO msg", source: "file" }),
        "Файл",
      ),
    ).toBe("16:56:06 · Файл");
  });

  it("ec_format_full_time_replaces_comma", () => {
    expect(formatServiceLogFullTime("2026-06-01 12:00:00,123")).toBe("2026-06-01 12:00:00.123");
  });

  it.each([
    ["Job #7 json_inbox_scan succeeded", { id: 7, jobType: "json_inbox_scan", status: "succeeded" }],
    ["Job #3 json_import_file failed: boom", { id: 3, jobType: "json_import_file", status: "failed" }],
    ["Job #1 notification_scan processing (attempt 1/3)", { id: 1, jobType: "notification_scan", status: "processing" }],
    ["not a job line", null],
  ])("ec_parse_worker_job_message: %s", (message, expected) => {
    expect(parseWorkerJobLogMessage(message)).toEqual(expected);
  });

  it("ec_strip_file_prefix", () => {
    const message = "2026-06-01 12:00:00,123 INFO Health check: ok";
    expect(stripServiceLogFilePrefix(message)).toBe("Health check: ok");
  });
});
