import { readApiError } from "@/lib/api-error";
import { t } from "@/i18n";
import { apiFetch } from "@/shared/api/http";

export type ServiceStatus = "ok" | "degraded" | "down";

export interface ServiceHealth {
  id: string;
  status: ServiceStatus;
  latency_ms: number;
  detail: string;
}

export interface PlatformStatus {
  checked_at: string;
  server_time: string;
  timezone: string;
  overall_status: ServiceStatus;
  services: ServiceHealth[];
}

export type ServiceLogSource = "process" | "health" | "jobs" | "file";

export interface ServiceLogEntry {
  logged_at: string;
  level: string;
  message: string;
  source: ServiceLogSource;
  job_id?: number | null;
}

export interface ServiceLogsResponse {
  service_id: string;
  entries: ServiceLogEntry[];
  has_file: boolean;
}

export async function fetchPlatformStatus(): Promise<PlatformStatus> {
  const response = await apiFetch("/api/v1/platform/status/");
  if (!response.ok) {
    throw new Error(await readApiError(response, t("errors.loadSettings")));
  }
  return response.json() as Promise<PlatformStatus>;
}

export async function fetchServiceLogs(
  serviceId: string,
  options?: { limit?: number },
): Promise<ServiceLogsResponse> {
  const params = new URLSearchParams();
  if (options?.limit) {
    params.set("limit", String(options.limit));
  }
  const query = params.toString();
  const path = `/api/v1/platform/services/${encodeURIComponent(serviceId)}/logs/${query ? `?${query}` : ""}`;
  const response = await apiFetch(path);
  if (!response.ok) {
    throw new Error(await readApiError(response, t("settings.project.logs.loadFailed")));
  }
  return response.json() as Promise<ServiceLogsResponse>;
}
