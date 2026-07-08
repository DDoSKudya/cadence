import { readApiError } from "@/lib/api-error";
import { t } from "@/i18n";
import { expectJson } from "@/shared/api/json";
import { apiFetch } from "@/shared/api/http";

import type { BoardScheme, BoardSchemesResponse, ColumnsListResponse, SettingsColumn } from "./types";
import type { ColumnWorkflow } from "./workflow";
import type { TaskStatusGraph } from "./task-status-graph";

export async function fetchBoardSchemes(): Promise<BoardSchemesResponse> {
  const response = await apiFetch("/api/v1/board/schemes/");
  return expectJson(response, t("errors.loadSchemes"));
}

export interface SchemeSwitchResult {
  scheme: BoardScheme | null;
  columns: SettingsColumn[];
  workflow: ColumnWorkflow;
  status_graph: TaskStatusGraph;
}

export interface SchemeCreatePayload {
  name: string;
  description?: string;
  switch?: boolean;
  confirm?: boolean;
}

export async function createBoardScheme(
  payload: SchemeCreatePayload,
): Promise<SchemeSwitchResult | BoardScheme> {
  const response = await apiFetch("/api/v1/board/schemes/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return expectJson(response, t("errors.createScheme"));
}

export async function switchBoardScheme(slug: string): Promise<SchemeSwitchResult> {
  const response = await apiFetch("/api/v1/board/schemes/switch/", {
    method: "POST",
    body: JSON.stringify({ slug, confirm: true }),
  });
  return expectJson(response, t("errors.switchScheme"));
}

export async function deleteBoardScheme(slug: string): Promise<void> {
  const response = await apiFetch(`/api/v1/board/schemes/${slug}/`, {
    method: "DELETE",
    body: JSON.stringify({ confirm: true }),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response, t("errors.deleteScheme")));
  }
}

export async function fetchColumns(): Promise<ColumnsListResponse> {
  const response = await apiFetch("/api/v1/columns/");
  return expectJson(response, t("errors.loadColumns"));
}

export async function reorderColumns(columnIds: number[]): Promise<SettingsColumn[]> {
  const response = await apiFetch("/api/v1/columns/reorder/", {
    method: "POST",
    body: JSON.stringify({ column_ids: columnIds }),
  });
  return expectJson(response, t("errors.reorderColumns"));
}

export interface ColumnCreatePayload {
  name: string;
  color: string;
  system_type?: string;
}

export interface ColumnUpdatePayload {
  name: string;
  color: string;
  wip_limit: number | null;
  system_type?: string;
  task_status_ids?: number[];
}

export async function createColumn(payload: ColumnCreatePayload): Promise<SettingsColumn> {
  const response = await apiFetch("/api/v1/columns/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return expectJson(response, t("errors.createColumn"));
}

export async function updateColumn(
  columnId: number,
  payload: ColumnUpdatePayload,
): Promise<SettingsColumn> {
  const response = await apiFetch(`/api/v1/columns/${columnId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return expectJson(response, t("errors.saveColumn"));
}

export class ColumnInUseError extends Error {
  constructor() {
    super(t("errors.columnHasTasks"));
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
    throw new Error(await readApiError(response, t("errors.deleteColumn")));
  }
}

export async function fetchColumnWorkflow(): Promise<ColumnWorkflow> {
  const response = await apiFetch("/api/v1/columns/workflow/");
  return expectJson(response, t("errors.loadWorkflow"));
}

export async function saveColumnWorkflow(
  transitions: ColumnWorkflow["transitions"],
): Promise<ColumnWorkflow> {
  const response = await apiFetch("/api/v1/columns/workflow/", {
    method: "PUT",
    body: JSON.stringify({ transitions }),
  });
  return expectJson(response, t("errors.saveWorkflow"));
}

export async function fetchTaskStatusGraph(): Promise<TaskStatusGraph> {
  const response = await apiFetch("/api/v1/task-statuses/");
  return expectJson(response, t("errors.loadStatusWorkflow"));
}

export async function saveTaskStatusGraph(payload: {
  statuses: TaskStatusGraph["statuses"];
  transitions: TaskStatusGraph["transitions"];
}): Promise<TaskStatusGraph> {
  const response = await apiFetch("/api/v1/task-statuses/", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  return expectJson(response, t("errors.saveStatusWorkflow"));
}

export async function saveTaskStatusLayout(
  statuses: Array<{ id: number; layout_x: number; layout_y: number }>,
): Promise<TaskStatusGraph> {
  const response = await apiFetch("/api/v1/task-statuses/", {
    method: "PATCH",
    body: JSON.stringify({ statuses }),
  });
  return expectJson(response, t("errors.saveStatusWorkflow"));
}
