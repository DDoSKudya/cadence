import { describe, expect, it } from "vitest";

import type { BackgroundJob } from "@/features/jobs/api";
import {
  formatJobJson,
  hasJson,
  jobDurationLabel,
  jobResultInsights,
  jobRunStepState,
  jobStatusLabel,
  jobTypeLabel,
} from "@/features/jobs/job-display";

function job(overrides: Partial<BackgroundJob> = {}): BackgroundJob {
  return {
    id: 1,
    job_type: "json_inbox_scan",
    status: "pending",
    payload: {},
    result: {},
    attempts: 0,
    max_attempts: 3,
    scheduled_at: null,
    started_at: null,
    finished_at: null,
    last_error: "",
    celery_task_id: "",
    created_at: "2026-06-01T10:00:00Z",
    updated_at: "2026-06-01T10:00:00Z",
    ...overrides,
  };
}

describe("job-display EC", () => {
  it.each([
    ["json_inbox_scan", "Inbox"],
    ["json_import_file", "Import"],
    ["unknown_type", "unknown_type"],
  ])("ec_job_type_label: %s", (jobType, expected) => {
    expect(jobTypeLabel(jobType)).toBe(expected);
  });

  it.each([
    ["pending", "Pending"],
    ["processing", "Processing"],
    ["succeeded", "Done"],
    ["failed", "Failed"],
    ["cancelled", "Cancelled"],
    ["custom", "custom"],
  ])("ec_job_status_label: %s", (status, expected) => {
    expect(jobStatusLabel(status)).toBe(expected);
  });

  it.each([
    [{}, false],
    [{ files: 1 }, true],
    [null, false],
  ] as const)("ec_has_json", (value, expected) => {
    expect(hasJson(value)).toBe(expected);
  });

  it("ec_format_job_json_pretty_prints", () => {
    expect(formatJobJson({ processed: 2 })).toBe('{\n  "processed": 2\n}');
  });

  it("ec_job_duration_empty_without_timestamps", () => {
    expect(jobDurationLabel(job())).toBe("");
  });

  it("ec_job_duration_seconds_short", () => {
    const value = jobDurationLabel(
      job({
        started_at: "2026-06-01T10:00:00Z",
        finished_at: "2026-06-01T10:00:05Z",
      }),
    );
    expect(value).toBe("5s");
  });

  it.each([
    ["created", "done"],
    ["finished", "active"],
  ] as const)("ec_job_run_step_state: %s", (step, expected) => {
    const activeJob = job({
      status: "processing",
      started_at: "2026-06-01T10:00:01Z",
    });
    expect(jobRunStepState(activeJob, step)).toBe(expected);
  });

  it("ec_job_run_step_started_idle_while_pending", () => {
    expect(jobRunStepState(job({ status: "pending" }), "started")).toBe("idle");
  });

  it("ec_job_result_insights_from_counters", () => {
    const insights = jobResultInsights(
      job({
        result: { processed: 3, tasks_created: 2, skipped: true },
      }),
    );
    expect(insights).toEqual([
      { label: "Files", value: "3" },
      { label: "Tasks", value: "2" },
      { label: "Duplicate", value: "skipped" },
    ]);
  });
});
