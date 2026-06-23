import { describe, expect, it } from "vitest";

import {
  applyTelegramBotCheck,
  cloneNotificationSettings,
  commitDraftRecipient,
  hasDraftRecipient,
  isNotificationSettingsApiSupported,
  normalizeNotificationSettings,
  snapshotNotificationSettings,
  normalizeAppLocale,
  type NotificationSettingsForm,
} from "./project-api";

const baseForm: NotificationSettingsForm = {
  language: "en",
  timezone: "Europe/Moscow",
  json_inbox_enabled: true,
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

describe("project-api EC", () => {
  it("ec_api_supported_detects_required_fields", () => {
    expect(
      isNotificationSettingsApiSupported({
        telegram_recipients: [],
        telegram_bot_token_set: false,
      }),
    ).toBe(true);
    expect(isNotificationSettingsApiSupported({})).toBe(false);
    expect(isNotificationSettingsApiSupported(null)).toBe(false);
  });

  it("ec_normalize_non_object_returns_defaults", () => {
    const normalized = normalizeNotificationSettings(null);
    expect(normalized.language).toBe("en");
    expect(normalized.telegram_enabled).toBe(false);
    expect(normalized.telegram_recipients).toEqual([]);
  });

  it("ec_normalize_filters_invalid_recipients", () => {
    const normalized = normalizeNotificationSettings({
      telegram_recipients: [
        { chat_id: "1", label: "A", kind: "user" },
        { chat_id: "", label: "B", kind: "user" },
        { chat_id: "2", label: "G", kind: "group" },
      ],
      telegram_bot_token_set: true,
    });
    expect(normalized.language).toBe("en");
    expect(normalized.telegram_recipients).toHaveLength(2);
    expect(normalized.telegram_recipients[1]?.kind).toBe("group");
  });

  it("ec_commit_draft_empty_chat_id_no_op", () => {
    const result = commitDraftRecipient(baseForm, { chat_id: "  ", label: "", kind: "user" });
    expect(result.error).toBeNull();
    expect(result.form.telegram_recipients).toHaveLength(0);
  });

  it("ec_commit_draft_duplicate_chat_id_rejected", () => {
    const form: NotificationSettingsForm = {
      ...baseForm,
      telegram_recipients: [{ chat_id: "100", label: "A", kind: "user" }],
    };
    const result = commitDraftRecipient(form, { chat_id: "100", label: "B", kind: "user" });
    expect(result.error).toContain("already added");
  });

  it("ec_commit_draft_valid_recipient_appended", () => {
    const result = commitDraftRecipient(baseForm, {
      chat_id: "200",
      label: "",
      kind: "group",
    });
    expect(result.error).toBeNull();
    expect(result.form.telegram_recipients[0]?.kind).toBe("group");
    expect(result.form.telegram_recipients[0]?.label).toBe("200");
  });

  it("ec_has_draft_recipient_boundary", () => {
    expect(hasDraftRecipient({ chat_id: "", label: "", kind: "user" })).toBe(false);
    expect(hasDraftRecipient({ chat_id: "1", label: "", kind: "user" })).toBe(true);
  });

  it("ec_apply_telegram_bot_check_success_sets_username", () => {
    const next = applyTelegramBotCheck(baseForm, {
      ok: true,
      message: "ok",
      checked_at: "2024-01-01T00:00:00Z",
      bot_username: "cadence_bot",
    });
    expect(next.telegram_bot_check_ok).toBe(true);
    expect(next.telegram_bot_username).toBe("@cadence_bot");
  });

  it("ec_clone_and_snapshot_roundtrip", () => {
    const cloned = cloneNotificationSettings({
      ...baseForm,
      telegram_recipients: [{ chat_id: "1", label: "A", kind: "user" }],
    });
    cloned.telegram_recipients[0]!.label = "Changed";
    expect(baseForm.telegram_recipients).toHaveLength(0);
    const snapshot = snapshotNotificationSettings(cloned);
    expect(snapshot).toContain("telegram_enabled");
    expect(snapshot).toContain("language");
  });

  it("ec_normalize_app_locale_defaults_to_english", () => {
    expect(normalizeAppLocale("ru")).toBe("ru");
    expect(normalizeAppLocale("en")).toBe("en");
    expect(normalizeAppLocale("de")).toBe("en");
  });
});
