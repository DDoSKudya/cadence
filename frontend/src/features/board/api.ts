import { readApiError } from "@/lib/api-error";
import { t } from "@/i18n";
import { apiFetch } from "@/shared/api/http";

import type {
  BoardResponse,
  BoardTask,
  Tag,
  TaskCreatePayload,
  TaskDetail,
  TaskUpdatePayload,
} from "./types";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    throw new Error(await readApiError(response, fallback));
  }
  return response.json() as Promise<T>;
}

export async function fetchBoard(weekKey: string): Promise<BoardResponse> {
  const response = await apiFetch(`/api/v1/board/?week=${encodeURIComponent(weekKey)}`);
  return parseJson(response, t("board.loadBoardFailed"));
}

export async function fetchTask(taskId: number): Promise<TaskDetail> {
  const response = await apiFetch(`/api/v1/tasks/${taskId}/`);
  return parseJson(response, t("board.loadFailed"));
}

export async function fetchTags(): Promise<Tag[]> {
  const response = await apiFetch("/api/v1/tags/");
  return parseJson(response, t("errors.loadTags"));
}

export async function createTask(payload: TaskCreatePayload): Promise<BoardTask> {
  const response = await apiFetch("/api/v1/tasks/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return parseJson(response, t("board.createFailed"));
}

export async function updateTask(taskId: number, payload: TaskUpdatePayload) {
  const response = await apiFetch(`/api/v1/tasks/${taskId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return parseJson<TaskDetail>(response, t("board.saveFailed"));
}

export async function moveTask(
  taskId: number,
  targetColumnId: number,
  targetPosition: number,
) {
  const response = await apiFetch(`/api/v1/tasks/${taskId}/move/`, {
    method: "POST",
    body: JSON.stringify({
      target_column_id: targetColumnId,
      target_position: targetPosition,
    }),
  });
  return parseJson<BoardTask>(response, t("board.moveFailed"));
}

export async function closeTask(taskId: number, completionNote = "", evidenceUrl?: string) {
  const response = await apiFetch(`/api/v1/tasks/${taskId}/close/`, {
    method: "POST",
    body: JSON.stringify({
      completion_note: completionNote,
      evidence_url: evidenceUrl ?? null,
    }),
  });
  return parseJson<TaskDetail>(response, t("board.closeFailed"));
}
