import { readApiError } from "@/lib/api-error";
import { t } from "@/i18n";
import { apiFetch } from "@/shared/api/http";

export interface BackgroundJob {
  id: number;
  job_type: string;
  status: string;
  payload: Record<string, unknown>;
  result: Record<string, unknown>;
  attempts: number;
  max_attempts: number;
  scheduled_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  last_error: string;
  celery_task_id: string;
  created_at: string;
  updated_at: string;
}

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    throw new Error(await readApiError(response, fallback));
  }
  return response.json() as Promise<T>;
}

export async function fetchJob(jobId: number): Promise<BackgroundJob> {
  const response = await apiFetch(`/api/v1/jobs/${jobId}/`);
  return parseJson(response, t("jobs.loadFailed"));
}

export async function retryJob(jobId: number): Promise<BackgroundJob> {
  const response = await apiFetch(`/api/v1/jobs/${jobId}/retry/`, { method: "POST" });
  return parseJson(response, t("errors.retryJob"));
}

export async function cancelJob(jobId: number): Promise<BackgroundJob> {
  const response = await apiFetch(`/api/v1/jobs/${jobId}/cancel/`, { method: "POST" });
  return parseJson(response, t("errors.cancelJob"));
}
