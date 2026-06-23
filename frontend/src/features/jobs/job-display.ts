import type { BackgroundJob } from "@/features/jobs/api";
import { t } from "@/i18n";

const JOB_TYPE_KEYS: Record<string, string> = {
  json_inbox_scan: "jobs.typeJsonInboxScan",
  json_import_file: "jobs.typeJsonImportFile",
  notification_scan: "jobs.typeNotificationScan",
  telegram_send: "jobs.typeTelegramSend",
  telegram_callback: "jobs.typeTelegramCallback",
  analytics_export: "jobs.typeAnalyticsExport",
};

const STATUS_KEYS: Record<string, string> = {
  pending: "jobs.statusPending",
  processing: "jobs.statusProcessing",
  succeeded: "jobs.statusSucceeded",
  failed: "jobs.statusFailed",
  cancelled: "jobs.statusCancelled",
};

export function jobTypeLabel(jobType: string): string {
  const key = JOB_TYPE_KEYS[jobType];
  return key ? t(key) : jobType;
}

export function jobStatusLabel(status: string): string {
  const key = STATUS_KEYS[status];
  return key ? t(key) : status;
}

export function hasJson(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && Object.keys(value as object).length > 0;
}

export function formatJobJson(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2);
}

export function jobDurationLabel(job: BackgroundJob): string {
  if (!job.started_at || !job.finished_at) {
    return "";
  }
  const ms = new Date(job.finished_at).getTime() - new Date(job.started_at).getTime();
  if (ms < 1000) {
    return t("jobs.secondsShort", { count: Math.round(ms / 1000) || 1 });
  }
  if (ms < 60_000) {
    return t("jobs.secondsShort", { count: Math.round(ms / 1000) });
  }
  return t("jobs.minutesShort", { count: Math.round(ms / 60_000) });
}

export function jobRunStepState(
  job: BackgroundJob,
  step: "created" | "started" | "finished",
): "done" | "active" | "idle" {
  if (step === "created") {
    return job.created_at ? "done" : "idle";
  }
  if (step === "started") {
    if (job.started_at) {
      return "done";
    }
    return job.status === "pending" ? "idle" : "active";
  }
  if (job.finished_at) {
    return "done";
  }
  if (job.started_at && (job.status === "processing" || job.status === "pending")) {
    return "active";
  }
  return "idle";
}

export function jobResultInsights(job: BackgroundJob): Array<{ label: string; value: string }> {
  const result = job.result;
  if (!hasJson(result)) {
    return [];
  }
  const insights: Array<{ label: string; value: string }> = [];
  if (typeof result.processed === "number") {
    insights.push({ label: t("jobs.files"), value: String(result.processed) });
  }
  if (typeof result.tasks_created === "number") {
    insights.push({ label: t("jobs.tasks"), value: String(result.tasks_created) });
  }
  if (result.skipped) {
    insights.push({ label: t("jobs.duplicate"), value: t("jobs.skipped") });
  }
  return insights;
}
