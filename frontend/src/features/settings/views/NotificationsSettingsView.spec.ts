import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createI18n } from "vue-i18n";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { en } from "@/i18n/locales/en";
import NotificationsSettingsView from "@/features/settings/views/NotificationsSettingsView.vue";
import type { NotificationSettingsForm } from "@/features/settings/project-api";

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

vi.mock("@/features/settings/project-api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/features/settings/project-api")>();
  return {
    ...actual,
    fetchNotificationSettings: vi.fn(),
    checkTelegramBot: vi.fn(),
  };
});

import * as projectApi from "@/features/settings/project-api";

function mountView() {
  const pinia = createPinia();
  setActivePinia(pinia);

  const i18n = createI18n({
    legacy: false,
    locale: "en",
    messages: { en },
  });

  return mount(NotificationsSettingsView, {
    global: {
      plugins: [pinia, i18n],
    },
  });
}

describe("NotificationsSettingsView", () => {
  beforeEach(() => {
    vi.mocked(projectApi.fetchNotificationSettings).mockReset();
    vi.mocked(projectApi.checkTelegramBot).mockReset();
  });

  it("renders rules panel after settings load", async () => {
    vi.mocked(projectApi.fetchNotificationSettings).mockResolvedValue(baseForm);

    const wrapper = mountView();
    await flushPromises();

    expect(wrapper.find(".notify-rules-panel").exists()).toBe(true);
    expect(wrapper.find(".notify-channel-fold").exists()).toBe(true);
    expect(wrapper.text()).toContain("Rules");
  });

  it("shows retry state when load fails", async () => {
    vi.mocked(projectApi.fetchNotificationSettings).mockRejectedValue(new Error("network"));

    const wrapper = mountView();
    await flushPromises();

    expect(wrapper.find(".jobs-empty").exists()).toBe(true);
    expect(wrapper.text()).toContain("network");
  });

  it("opens recipient drawer from add button", async () => {
    vi.mocked(projectApi.fetchNotificationSettings).mockResolvedValue(baseForm);

    const wrapper = mountView();
    await flushPromises();

    await wrapper.get(".notify-fold-trigger").trigger("click");
    await wrapper.get(".notify-recipients-add-btn").trigger("click");
    await flushPromises();

    expect(document.querySelector(".drawer-panel")).toBeTruthy();
    expect(document.body.textContent).toContain("New recipient");
  });
});
