import { readApiError } from "@/lib/api-error";
import { t } from "@/i18n";
import { apiFetch } from "@/shared/api/http";

import type {
  ArchiveFilters,
  ArchiveListResponse,
  ArchiveTaskDetail,
} from "./types";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    throw new Error(await readApiError(response, fallback));
  }
  return response.json() as Promise<T>;
}

function buildQuery(filters: ArchiveFilters): string {
  const params = new URLSearchParams();
  if (filters.week) {
    params.set("week", filters.week);
  }
  if (filters.tag) {
    params.set("tag", filters.tag);
  }
  if (filters.source) {
    params.set("source", filters.source);
  }
  if (filters.search) {
    params.set("search", filters.search);
  }
  if (filters.closed_from) {
    params.set("closed_from", filters.closed_from);
  }
  if (filters.closed_to) {
    params.set("closed_to", filters.closed_to);
  }
  params.set("page", String(filters.page ?? 1));
  params.set("page_size", String(filters.page_size ?? 20));
  return params.toString();
}

export async function fetchArchiveTasks(
  filters: ArchiveFilters = {},
): Promise<ArchiveListResponse> {
  const query = buildQuery(filters);
  const response = await apiFetch(`/api/v1/archive/tasks/?${query}`);
  return parseJson(response, t("archive.loadFailed"));
}

export async function fetchArchiveTask(taskId: number): Promise<ArchiveTaskDetail> {
  const response = await apiFetch(`/api/v1/archive/tasks/${taskId}/`);
  return parseJson(response, t("board.loadFailed"));
}

export async function reopenArchiveTask(taskId: number): Promise<void> {
  const response = await apiFetch(`/api/v1/tasks/${taskId}/reopen/`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await readApiError(response, t("errors.reopenTask")));
  }
}
