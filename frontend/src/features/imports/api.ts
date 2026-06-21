import { readApiError } from "@/lib/api-error";
import { apiFetch } from "@/shared/api/http";

export interface ImportLog {
  id: number;
  filename: string;
  original_path: string;
  checksum: string;
  idempotency_key: string | null;
  schema_version: string;
  source_label: string;
  status: string;
  tasks_created: number;
  error_message: string;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    throw new Error(await readApiError(response, fallback));
  }
  return response.json() as Promise<T>;
}

export async function fetchImports(): Promise<ImportLog[]> {
  const response = await apiFetch("/api/v1/imports/");
  return parseJson(response, "Не удалось загрузить импорты");
}

export async function scanImports(): Promise<{ processed: number }> {
  const response = await apiFetch("/api/v1/imports/scan/", { method: "POST" });
  return parseJson(response, "Не удалось запустить сканирование");
}

export async function retryImport(importId: number): Promise<ImportLog> {
  const response = await apiFetch(`/api/v1/imports/${importId}/retry/`, {
    method: "POST",
  });
  return parseJson(response, "Не удалось повторить импорт");
}
