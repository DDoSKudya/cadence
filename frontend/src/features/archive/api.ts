import { readApiError } from "@/lib/api-error";
import { t } from "@/i18n";
import { expectJson } from "@/shared/api/json";
import { apiFetch } from "@/shared/api/http";

import type {
  ArchiveFilters,
  ArchiveListResponse,
  ArchiveTaskDetail,
} from "./types";

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
  return expectJson(response, t("archive.loadFailed"));
}

export async function fetchArchiveTask(taskId: number): Promise<ArchiveTaskDetail> {
  const response = await apiFetch(`/api/v1/archive/tasks/${taskId}/`);
  return expectJson(response, t("board.loadFailed"));
}

export async function reopenArchiveTask(taskId: number): Promise<void> {
  const response = await apiFetch(`/api/v1/tasks/${taskId}/reopen/`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(await readApiError(response, t("errors.reopenTask")));
  }
}
