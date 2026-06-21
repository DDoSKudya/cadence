import { readApiError } from "@/lib/api-error";
import { apiFetch } from "@/shared/api/http";

import type { SettingsColumn } from "./types";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    throw new Error(await readApiError(response, fallback));
  }
  return response.json() as Promise<T>;
}

export async function fetchColumns(): Promise<SettingsColumn[]> {
  const response = await apiFetch("/api/v1/columns/");
  return parseJson(response, "Не удалось загрузить колонки");
}

export async function reorderColumns(columnIds: number[]): Promise<SettingsColumn[]> {
  const response = await apiFetch("/api/v1/columns/reorder/", {
    method: "POST",
    body: JSON.stringify({ column_ids: columnIds }),
  });
  return parseJson(response, "Не удалось изменить порядок");
}

export interface ColumnCreatePayload {
  name: string;
  color: string;
}

export interface ColumnUpdatePayload {
  name: string;
  color: string;
  wip_limit: number | null;
}

export async function createColumn(payload: ColumnCreatePayload): Promise<SettingsColumn> {
  const response = await apiFetch("/api/v1/columns/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return parseJson(response, "Не удалось создать колонку");
}

export async function updateColumn(
  columnId: number,
  payload: ColumnUpdatePayload,
): Promise<SettingsColumn> {
  const response = await apiFetch(`/api/v1/columns/${columnId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return parseJson(response, "Не удалось сохранить колонку");
}

export class ColumnInUseError extends Error {
  constructor() {
    super("В колонке есть задачи. Сначала перенесите их.");
    this.name = "ColumnInUseError";
  }
}

export async function deleteColumn(columnId: number): Promise<void> {
  const response = await apiFetch(`/api/v1/columns/${columnId}/`, {
    method: "DELETE",
  });
  if (response.status === 409) {
    throw new ColumnInUseError();
  }
  if (!response.ok) {
    throw new Error(await readApiError(response, "Не удалось убрать колонку"));
  }
}
