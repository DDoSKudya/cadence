import { readApiError } from "@/lib/api-error";
import { apiFetch } from "@/shared/api/http";

import type { WeekCloseResult, WeekReviewResponse } from "./types";

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    throw new Error(await readApiError(response, fallback));
  }
  return response.json() as Promise<T>;
}

export async function fetchWeekReview(weekId: number): Promise<WeekReviewResponse> {
  const response = await apiFetch(`/api/v1/weeks/${weekId}/review/`);
  return parseJson(response, "Не удалось загрузить обзор недели");
}

export async function saveWeekReviewNotes(
  weekId: number,
  reviewNotes: string,
): Promise<WeekReviewResponse["week"]> {
  const response = await apiFetch(`/api/v1/weeks/${weekId}/review/`, {
    method: "PATCH",
    body: JSON.stringify({ review_notes: reviewNotes }),
  });
  return parseJson(response, "Не удалось сохранить заметки");
}

export async function closeWeek(
  weekId: number,
  carryOver = true,
): Promise<WeekCloseResult> {
  const response = await apiFetch(`/api/v1/weeks/${weekId}/close/`, {
    method: "POST",
    body: JSON.stringify({ carry_over: carryOver }),
  });
  return parseJson(response, "Не удалось закрыть неделю");
}
