import { readApiError } from "@/lib/api-error";
import { t } from "@/i18n";
import { apiFetch } from "@/shared/api/http";

export interface SettingsTag {
  id: number;
  name: string;
  slug: string;
  color: string;
  is_active: boolean;
  created_at: string;
}

export interface TagCreatePayload {
  name: string;
  color?: string;
}

export interface TagUpdatePayload {
  name?: string;
  color?: string;
}

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    throw new Error(await readApiError(response, fallback));
  }
  return response.json() as Promise<T>;
}

export async function fetchSettingsTags(): Promise<SettingsTag[]> {
  const response = await apiFetch("/api/v1/tags/");
  return parseJson(response, t("errors.loadTags"));
}

export async function createSettingsTag(payload: TagCreatePayload): Promise<SettingsTag> {
  const response = await apiFetch("/api/v1/tags/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return parseJson(response, t("errors.saveTag"));
}

export async function updateSettingsTag(
  tagId: number,
  payload: TagUpdatePayload,
): Promise<SettingsTag> {
  const response = await apiFetch(`/api/v1/tags/${tagId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return parseJson(response, t("errors.saveTag"));
}

export async function deleteSettingsTag(tagId: number): Promise<void> {
  const response = await apiFetch(`/api/v1/tags/${tagId}/`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(await readApiError(response, t("errors.deleteTag")));
  }
}
