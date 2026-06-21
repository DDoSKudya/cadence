import { readApiError } from "@/lib/api-error";
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

export interface JobFilters {
  job_type?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export interface JobListResponse {
  count: number;
  page: number;
  page_size: number;
  results: BackgroundJob[];
}

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    throw new Error(await readApiError(response, fallback));
  }
  return response.json() as Promise<T>;
}

function buildQuery(filters: JobFilters): string {
  const params = new URLSearchParams();
  if (filters.job_type) {
    params.set("job_type", filters.job_type);
  }
  if (filters.status) {
    params.set("status", filters.status);
  }
  params.set("page", String(filters.page ?? 1));
  params.set("page_size", String(filters.page_size ?? 20));
  return params.toString();
}

export async function fetchJobs(filters: JobFilters = {}): Promise<JobListResponse> {
  const query = buildQuery(filters);
  const response = await apiFetch(query ? `/api/v1/jobs/?${query}` : "/api/v1/jobs/");
  const data = await parseJson<JobListResponse | BackgroundJob[]>(
    response,
    "Не удалось загрузить задачи",
  );

  const page = filters.page ?? 1;
  const pageSize = filters.page_size ?? 20;

  if (Array.isArray(data)) {
    const start = (page - 1) * pageSize;
    return {
      count: data.length,
      page,
      page_size: pageSize,
      results: data.slice(start, start + pageSize),
    };
  }

  if (!data || typeof data !== "object") {
    return {
      count: 0,
      page: filters.page ?? 1,
      page_size: filters.page_size ?? 20,
      results: [],
    };
  }

  return {
    count: typeof data.count === "number" ? data.count : 0,
    page: typeof data.page === "number" ? data.page : (filters.page ?? 1),
    page_size: typeof data.page_size === "number" ? data.page_size : (filters.page_size ?? 20),
    results: Array.isArray(data.results) ? data.results : [],
  };
}

export async function fetchJob(jobId: number): Promise<BackgroundJob> {
  const response = await apiFetch(`/api/v1/jobs/${jobId}/`);
  return parseJson(response, "Не удалось загрузить задачу");
}

export async function retryJob(jobId: number): Promise<BackgroundJob> {
  const response = await apiFetch(`/api/v1/jobs/${jobId}/retry/`, { method: "POST" });
  return parseJson(response, "Не удалось повторить задачу");
}

export async function cancelJob(jobId: number): Promise<BackgroundJob> {
  const response = await apiFetch(`/api/v1/jobs/${jobId}/cancel/`, { method: "POST" });
  return parseJson(response, "Не удалось отменить задачу");
}
