import { readApiError } from "@/lib/api-error";
import { t } from "@/i18n";
import { getI18nLocale } from "@/i18n";
import { expectJson } from "@/shared/api/json";
import { apiFetch } from "@/shared/api/http";

import type {
  AnalyticsExportJob,
  AnalyticsFilters,
  AnalyticsSummary,
  ArchiveAnalytics,
  BreakdownItem,
  CycleTimeData,
  ExportFormat,
  ExportPreviewResponse,
  ExportType,
  NotificationMetrics,
  TaskFlowData,
  WeeklyTrendItem,
} from "./types";

function buildQuery(filters: AnalyticsFilters, extra: Record<string, string> = {}): string {
  const params = new URLSearchParams();
  if (filters.week) {
    params.set("week", filters.week);
  }
  if (filters.from) {
    params.set("from", filters.from);
  }
  if (filters.to) {
    params.set("to", filters.to);
  }
  if (filters.tag) {
    params.set("tag", filters.tag);
  }
  if (filters.source) {
    params.set("source", filters.source);
  }
  for (const [key, value] of Object.entries(extra)) {
    params.set(key, value);
  }
  return params.toString();
}

export async function fetchAnalyticsSummary(filters: AnalyticsFilters): Promise<AnalyticsSummary> {
  const query = buildQuery(filters);
  const response = await apiFetch(
    query ? `/api/v1/analytics/summary/?${query}` : "/api/v1/analytics/summary/",
  );
  return expectJson(response, t("errors.loadSummary"));
}

export async function fetchWeeklyTrend(
  filters: AnalyticsFilters,
  weeks = 12,
): Promise<{ items: WeeklyTrendItem[] }> {
  const query = buildQuery(filters, { weeks: String(weeks) });
  const response = await apiFetch(`/api/v1/analytics/weekly-trend/?${query}`);
  return expectJson(response, t("errors.loadTrend"));
}

export async function fetchBreakdown(
  filters: AnalyticsFilters,
  groupBy: "tag" | "column" | "source",
): Promise<{ group_by: string; items: BreakdownItem[] }> {
  const query = buildQuery(filters, { group_by: groupBy });
  const response = await apiFetch(`/api/v1/analytics/breakdown/?${query}`);
  return expectJson(response, t("errors.loadBreakdown"));
}

export async function fetchCycleTime(filters: AnalyticsFilters): Promise<CycleTimeData> {
  const query = buildQuery(filters);
  const response = await apiFetch(
    query ? `/api/v1/analytics/cycle-time/?${query}` : "/api/v1/analytics/cycle-time/",
  );
  return expectJson(response, t("errors.loadCycleTime"));
}

export async function fetchNotificationMetrics(
  filters: AnalyticsFilters,
): Promise<NotificationMetrics> {
  const query = buildQuery(filters);
  const response = await apiFetch(
    query
      ? `/api/v1/analytics/notifications/?${query}`
      : "/api/v1/analytics/notifications/",
  );
  return expectJson(response, t("errors.loadNotificationMetrics"));
}

export async function fetchTaskFlow(filters: AnalyticsFilters): Promise<TaskFlowData> {
  const query = buildQuery(filters);
  const response = await apiFetch(
    query ? `/api/v1/analytics/task-flow/?${query}` : "/api/v1/analytics/task-flow/",
  );
  return expectJson(response, t("errors.loadFlow"));
}

export async function fetchArchiveAnalytics(filters: AnalyticsFilters): Promise<ArchiveAnalytics> {
  const query = buildQuery(filters);
  const response = await apiFetch(
    query ? `/api/v1/analytics/archive/?${query}` : "/api/v1/analytics/archive/",
  );
  return expectJson(response, t("errors.loadArchiveAnalytics"));
}

export async function fetchExportPreview(
  exportType: ExportType,
  filters: AnalyticsFilters,
): Promise<ExportPreviewResponse> {
  const params = new URLSearchParams(buildQuery(filters));
  params.set("export_type", exportType);
  params.set("locale", getI18nLocale());
  const response = await apiFetch(`/api/v1/analytics/exports/preview/?${params.toString()}`);
  return expectJson(response, t("errors.loadExportPreview"));
}

export async function createAnalyticsExport(payload: {
  export_type: ExportType;
  file_format: ExportFormat;
  filters?: Record<string, unknown>;
}): Promise<AnalyticsExportJob> {
  const response = await apiFetch("/api/v1/analytics/exports/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return expectJson(response, t("analytics.exportFailed"));
}

export async function fetchAnalyticsExport(exportId: number): Promise<AnalyticsExportJob> {
  const response = await apiFetch(`/api/v1/analytics/exports/${exportId}/`);
  return expectJson(response, t("errors.loadExport"));
}

export async function downloadAnalyticsExport(exportId: number): Promise<void> {
  const response = await apiFetch(`/api/v1/analytics/exports/${exportId}/download/`);
  if (!response.ok) {
    throw new Error(await readApiError(response, t("analytics.downloadFailed")));
  }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^"]+)"?/i.exec(disposition);
  const filename = match?.[1] ?? `analytics-export-${exportId}`;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
