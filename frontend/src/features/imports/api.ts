import { readApiError } from "@/lib/api-error";
import { t } from "@/i18n";
import { apiFetch } from "@/shared/api/http";

export interface ImportLog {
  id: number;
  filename: string;
  status: string;
  tasks_created: number;
  error_message: string;
}

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    throw new Error(await readApiError(response, fallback));
  }
  return response.json() as Promise<T>;
}

export async function uploadImport(file: File): Promise<ImportLog> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiFetch("/api/v1/imports/upload/", {
    method: "POST",
    body: formData,
  });
  return parseJson(response, t("errors.importFile"));
}
