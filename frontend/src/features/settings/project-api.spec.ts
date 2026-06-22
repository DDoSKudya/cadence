import { describe, expect, it } from "vitest";

import {
  commitDraftRecipient,
  isNotificationSettingsApiSupported,
  normalizeNotificationSettings,
} from "@/features/settings/project-api";

describe("normalizeNotificationSettings", () => {
  it("returns defaults for empty payload", () => {
    const result = normalizeNotificationSettings(null);
    expect(result.telegram_recipients).toEqual([]);
    expect(result.telegram_enabled).toBe(false);
    expect(result.default_reminder_interval_minutes).toBe(1440);
  });

  it("ignores invalid recipients and keeps valid ones", () => {
    const result = normalizeNotificationSettings({
      telegram_recipients: [
        { chat_id: "111", label: "Me", kind: "user" },
        { chat_id: "", label: "Skip" },
        { chat_id: "222", label: "Team", kind: "group" },
      ],
    });
    expect(result.telegram_recipients).toHaveLength(2);
    expect(result.telegram_recipients[1]?.kind).toBe("group");
  });

  it("detects legacy settings API without telegram fields", () => {
    expect(
      isNotificationSettingsApiSupported({
        telegram_enabled: true,
        default_reminder_interval_minutes: 1440,
      }),
    ).toBe(false);
  });

  it("accepts current settings API shape", () => {
    expect(
      isNotificationSettingsApiSupported({
        telegram_recipients: [],
        telegram_bot_token_set: false,
      }),
    ).toBe(true);
  });
});

describe("commitDraftRecipient", () => {
  const baseForm = normalizeNotificationSettings({
    telegram_recipients: [],
    telegram_bot_token_set: false,
  });

  it("adds draft recipient to form", () => {
    const result = commitDraftRecipient(baseForm, {
      chat_id: "12345",
      label: "Я",
      kind: "user",
    });
    expect(result.error).toBeNull();
    expect(result.form.telegram_recipients).toEqual([
      { chat_id: "12345", label: "Я", kind: "user" },
    ]);
    expect(result.draft.chat_id).toBe("");
  });

  it("uses chat_id as label when label is empty", () => {
    const result = commitDraftRecipient(baseForm, {
      chat_id: "-100999",
      label: "",
      kind: "group",
    });
    expect(result.form.telegram_recipients[0]).toEqual({
      chat_id: "-100999",
      label: "-100999",
      kind: "group",
    });
  });

  it("returns error for duplicate chat_id", () => {
    const form = {
      ...baseForm,
      telegram_recipients: [{ chat_id: "12345", label: "Me", kind: "user" as const }],
    };
    const result = commitDraftRecipient(form, {
      chat_id: "12345",
      label: "Dup",
      kind: "user",
    });
    expect(result.error).toBe("Такой chat ID уже добавлен");
  });
});
