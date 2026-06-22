import { readApiError } from "@/lib/api-error";
import { apiFetch } from "@/shared/api/http";

export type TelegramRecipientKind = "user" | "group";

export interface TelegramRecipient {
  chat_id: string;
  label: string;
  kind: TelegramRecipientKind;
}

export interface NotificationSettingsForm {
  telegram_enabled: boolean;
  telegram_bot_token_set: boolean;
  telegram_bot_username: string;
  telegram_recipients: TelegramRecipient[];
  telegram_bot_check_ok: boolean | null;
  telegram_bot_check_message: string;
  telegram_bot_checked_at: string | null;
  default_reminder_interval_minutes: number;
  stale_in_progress_minutes: number;
  stale_planned_minutes: number;
  quiet_hours_start: string;
  quiet_hours_end: string;
}

export interface TelegramBotCheckResult {
  ok: boolean;
  message: string;
  checked_at: string;
  bot_username: string | null;
}

export interface NotificationSettingsUpdate {
  telegram_enabled?: boolean;
  telegram_bot_token?: string;
  telegram_bot_username?: string;
  telegram_recipients?: TelegramRecipient[];
  default_reminder_interval_minutes?: number;
  stale_in_progress_minutes?: number;
  stale_planned_minutes?: number;
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
}

const DEFAULT_SETTINGS: NotificationSettingsForm = {
  telegram_enabled: false,
  telegram_bot_token_set: false,
  telegram_bot_username: "",
  telegram_recipients: [],
  telegram_bot_check_ok: null,
  telegram_bot_check_message: "",
  telegram_bot_checked_at: null,
  default_reminder_interval_minutes: 1440,
  stale_in_progress_minutes: 4320,
  stale_planned_minutes: 10080,
  quiet_hours_start: "",
  quiet_hours_end: "",
};

function normalizeRecipient(raw: unknown): TelegramRecipient | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const item = raw as Record<string, unknown>;
  const chatId = String(item.chat_id ?? "").trim();
  if (!chatId) {
    return null;
  }
  const kind = item.kind === "group" ? "group" : "user";
  return {
    chat_id: chatId,
    label: String(item.label ?? "").trim(),
    kind,
  };
}

export function isNotificationSettingsApiSupported(raw: unknown): boolean {
  if (!raw || typeof raw !== "object") {
    return false;
  }
  const data = raw as Record<string, unknown>;
  return "telegram_recipients" in data && "telegram_bot_token_set" in data;
}

export function normalizeNotificationSettings(raw: unknown): NotificationSettingsForm {
  if (!raw || typeof raw !== "object") {
    return { ...DEFAULT_SETTINGS, telegram_recipients: [] };
  }

  const data = raw as Record<string, unknown>;
  const recipientsRaw = Array.isArray(data.telegram_recipients) ? data.telegram_recipients : [];
  const recipients = recipientsRaw
    .map(normalizeRecipient)
    .filter((item): item is TelegramRecipient => item !== null);

  return {
    telegram_enabled: Boolean(data.telegram_enabled),
    telegram_bot_token_set: Boolean(data.telegram_bot_token_set),
    telegram_bot_username: String(data.telegram_bot_username ?? ""),
    telegram_recipients: recipients,
    telegram_bot_check_ok:
      data.telegram_bot_check_ok === null || data.telegram_bot_check_ok === undefined
        ? null
        : Boolean(data.telegram_bot_check_ok),
    telegram_bot_check_message: String(data.telegram_bot_check_message ?? ""),
    telegram_bot_checked_at: data.telegram_bot_checked_at
      ? String(data.telegram_bot_checked_at)
      : null,
    default_reminder_interval_minutes: Number(
      data.default_reminder_interval_minutes ?? DEFAULT_SETTINGS.default_reminder_interval_minutes,
    ),
    stale_in_progress_minutes: Number(
      data.stale_in_progress_minutes ?? DEFAULT_SETTINGS.stale_in_progress_minutes,
    ),
    stale_planned_minutes: Number(
      data.stale_planned_minutes ?? DEFAULT_SETTINGS.stale_planned_minutes,
    ),
    quiet_hours_start: data.quiet_hours_start ? String(data.quiet_hours_start).slice(0, 5) : "",
    quiet_hours_end: data.quiet_hours_end ? String(data.quiet_hours_end).slice(0, 5) : "",
  };
}

function emptyDraftRecipient(): TelegramRecipient {
  return { chat_id: "", label: "", kind: "user" };
}

export function commitDraftRecipient(
  form: NotificationSettingsForm,
  draft: TelegramRecipient,
): { form: NotificationSettingsForm; draft: TelegramRecipient; error: string | null } {
  const chatId = draft.chat_id.trim();
  if (!chatId) {
    return { form, draft, error: null };
  }

  if (form.telegram_recipients.some((item) => item.chat_id === chatId)) {
    return { form, draft, error: "Такой chat ID уже добавлен" };
  }

  const next = cloneForm(form);
  next.telegram_recipients.push({
    chat_id: chatId,
    label: draft.label.trim() || chatId,
    kind: draft.kind === "group" ? "group" : "user",
  });

  return {
    form: next,
    draft: emptyDraftRecipient(),
    error: null,
  };
}

export function hasDraftRecipient(draft: TelegramRecipient): boolean {
  return Boolean(draft.chat_id.trim());
}

function cloneForm(source: NotificationSettingsForm): NotificationSettingsForm {
  const recipients = Array.isArray(source.telegram_recipients) ? source.telegram_recipients : [];
  return {
    ...source,
    telegram_recipients: recipients.map((item) => ({ ...item })),
  };
}

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    throw new Error(await readApiError(response, fallback));
  }
  return response.json() as Promise<T>;
}

export async function fetchNotificationSettings(): Promise<NotificationSettingsForm> {
  const response = await apiFetch("/api/v1/settings/");
  const raw = await parseJson<unknown>(response, "Не удалось загрузить настройки");
  if (!isNotificationSettingsApiSupported(raw)) {
    throw new Error(
      "Backend не обновлён — перезапустите сервер (docker compose restart backend)",
    );
  }
  return cloneForm(normalizeNotificationSettings(raw));
}

export async function checkTelegramBot(token?: string): Promise<TelegramBotCheckResult> {
  const payload = token?.trim() ? { telegram_bot_token: token.trim() } : {};
  const response = await apiFetch("/api/v1/settings/telegram/check/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return parseJson<TelegramBotCheckResult>(response, "Не удалось проверить бота");
}

export function applyTelegramBotCheck(
  form: NotificationSettingsForm,
  result: TelegramBotCheckResult,
): NotificationSettingsForm {
  const next = cloneForm(form);
  next.telegram_bot_check_ok = result.ok;
  next.telegram_bot_check_message = result.message;
  next.telegram_bot_checked_at = result.checked_at;
  if (result.ok && result.bot_username && !next.telegram_bot_username.trim()) {
    next.telegram_bot_username = `@${result.bot_username}`;
  }
  return next;
}

export async function saveNotificationSettings(
  payload: NotificationSettingsUpdate,
): Promise<NotificationSettingsForm> {
  const response = await apiFetch("/api/v1/settings/", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  const raw = await parseJson<unknown>(response, "Не удалось сохранить настройки");
  if (!isNotificationSettingsApiSupported(raw)) {
    throw new Error(
      "Данные Telegram не сохранились — backend не обновлён. Перезапустите: docker compose restart backend",
    );
  }
  const saved = cloneForm(normalizeNotificationSettings(raw));
  if (payload.telegram_bot_token?.trim() && !saved.telegram_bot_token_set) {
    throw new Error("Токен бота не сохранился — проверьте backend");
  }
  if (
    payload.telegram_recipients &&
    payload.telegram_recipients.length > 0 &&
    saved.telegram_recipients.length === 0
  ) {
    throw new Error("Получатели не сохранились — проверьте backend");
  }
  return saved;
}

export function cloneNotificationSettings(
  source: NotificationSettingsForm,
): NotificationSettingsForm {
  return cloneForm(source);
}

export function snapshotNotificationSettings(form: NotificationSettingsForm): string {
  return JSON.stringify({
    telegram_enabled: form.telegram_enabled,
    telegram_bot_username: form.telegram_bot_username.trim(),
    telegram_recipients: form.telegram_recipients,
    default_reminder_interval_minutes: form.default_reminder_interval_minutes,
    stale_in_progress_minutes: form.stale_in_progress_minutes,
    stale_planned_minutes: form.stale_planned_minutes,
    quiet_hours_start: form.quiet_hours_start || null,
    quiet_hours_end: form.quiet_hours_end || null,
  });
}
