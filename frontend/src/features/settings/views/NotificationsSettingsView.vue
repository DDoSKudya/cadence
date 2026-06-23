<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import {
  ArrowPathIcon,
  BellAlertIcon,
  ChatBubbleLeftRightIcon,
  ChevronDownIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  PlusIcon,
  TrashIcon,
  UserGroupIcon,
  UserIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";

import {
  applyTelegramBotCheck,
  checkTelegramBot,
  cloneNotificationSettings,
  commitDraftRecipient,
  fetchNotificationSettings,
  hasDraftRecipient,
  saveNotificationSettings,
  snapshotNotificationSettings,
  type NotificationSettingsForm,
  type NotificationSettingsUpdate,
  type TelegramRecipient,
} from "@/features/settings/project-api";
import { formatDateTime } from "@/lib/datetime";
import { useToastStore } from "@/stores/toast";

const { t } = useI18n();
const toast = useToastStore();
const loading = ref(true);
const loadFailed = ref(false);
const saving = ref(false);
const botChecking = ref(false);
const error = ref("");
const form = ref<NotificationSettingsForm | null>(null);
const savedForm = ref<NotificationSettingsForm | null>(null);
const botTokenInput = ref("");
const openTelegram = ref(false);
const recipientPanelOpen = ref(false);

const emptyDraftRecipient = (): TelegramRecipient => ({
  chat_id: "",
  label: "",
  kind: "user",
});

const draftRecipient = ref<TelegramRecipient>(emptyDraftRecipient());

const isDirty = computed(() => {
  if (!form.value || !savedForm.value) {
    return false;
  }
  if (botTokenInput.value.trim() || hasDraftRecipient(draftRecipient.value)) {
    return true;
  }
  return snapshotNotificationSettings(form.value) !== snapshotNotificationSettings(savedForm.value);
});

const headerMeta = computed(() => {
  if (!form.value) {
    return t("settings.notificationRules");
  }
  const quiet =
    form.value.quiet_hours_start && form.value.quiet_hours_end
      ? `${t("settings.quietHours").toLowerCase()} ${form.value.quiet_hours_start}–${form.value.quiet_hours_end}`
      : t("settings.quietHint");
  return `${formatDuration(form.value.default_reminder_interval_minutes)} · ${quiet}`;
});

const telegramSummary = computed(() => {
  if (!form.value) {
    return "";
  }
  const status = form.value.telegram_enabled ? t("settings.enabledShort") : t("settings.disabledShort");
  const bot = form.value.telegram_bot_username.trim() || (form.value.telegram_bot_token_set ? t("settings.botOk") : t("common.notConfigured"));
  const count = t("settings.recipientCount", form.value.telegram_recipients.length);
  return t("settings.summary", {
    status,
    bot,
    count,
  });
});

const hasBotToken = computed(() => {
  if (!form.value) {
    return false;
  }
  return form.value.telegram_bot_token_set || Boolean(botTokenInput.value.trim());
});

const telegramSetupIssues = computed(() => {
  if (!form.value?.telegram_enabled) {
    return [] as string[];
  }
  const issues: string[] = [];
  if (!hasBotToken.value) {
    issues.push(t("settings.setupNoToken"));
  }
  if (form.value.telegram_recipients.length === 0) {
    issues.push(t("settings.setupNoRecipients"));
  }
  return issues;
});

const telegramSetupWarning = computed(() => telegramSetupIssues.value.join(" · "));

const botHealth = computed(() => {
  const empty = { label: "", class: "", title: "" };
  if (!form.value?.telegram_enabled) {
    return empty;
  }

  if (botChecking.value) {
    return { label: t("settings.botCheckPending"), class: "notify-bot-status-pending", title: "" };
  }

  if (telegramSetupIssues.value.length > 0) {
    return {
      label: t("settings.botSetup"),
      class: "notify-bot-status-warn",
      title: telegramSetupWarning.value,
    };
  }

  const parts: string[] = [];
  if (form.value.telegram_bot_check_message) {
    parts.push(form.value.telegram_bot_check_message);
  }
  if (form.value.telegram_bot_checked_at) {
    parts.push(t("settings.botCheckTime", { value: formatDateTime(form.value.telegram_bot_checked_at) }));
  }
  const title = parts.join("\n");

  if (form.value.telegram_bot_check_ok === true) {
    return { label: t("settings.botOk"), class: "notify-bot-status-ok", title };
  }
  if (form.value.telegram_bot_check_ok === false) {
    return { label: t("settings.botError"), class: "notify-bot-status-error", title };
  }
  return { label: t("settings.botUnchecked"), class: "notify-bot-status-idle", title };
});

function formatDuration(minutes: number): string {
  if (!Number.isFinite(minutes) || minutes <= 0) {
    return "—";
  }
  if (minutes % 1440 === 0) {
    const days = minutes / 1440;
    return t("common.days", days);
  }
  if (minutes % 60 === 0) {
    const hours = minutes / 60;
    return t("common.hours", hours);
  }
  return t("common.minutes", minutes);
}

async function runBotCheck(options: { silent?: boolean } = {}) {
  if (!form.value?.telegram_enabled || botChecking.value) {
    return;
  }
  if (!hasBotToken.value) {
    return;
  }

  botChecking.value = true;
  if (!options.silent) {
    error.value = "";
  }

  try {
    const token = botTokenInput.value.trim() || undefined;
    const result = await checkTelegramBot(token);
    form.value = applyTelegramBotCheck(form.value, result);
    if (savedForm.value && !isDirty.value) {
      savedForm.value = cloneNotificationSettings(form.value);
    }
  } catch (checkError) {
    if (!options.silent) {
      error.value =
        checkError instanceof Error ? checkError.message : t("errors.checkBot");
    }
  } finally {
    botChecking.value = false;
  }
}

async function loadSettings() {
  loading.value = true;
  loadFailed.value = false;
  error.value = "";
  try {
    const data = await fetchNotificationSettings();
    form.value = data;
    savedForm.value = cloneNotificationSettings(data);
    botTokenInput.value = "";
    if (data.telegram_enabled && data.telegram_bot_token_set) {
      void runBotCheck({ silent: true });
    }
  } catch (loadError) {
    loadFailed.value = true;
    form.value = null;
    savedForm.value = null;
    error.value =
      loadError instanceof Error ? loadError.message : t("errors.loadSettings");
  } finally {
    loading.value = false;
  }
}

function applyDraftRecipient(options: { openOnError?: boolean } = {}): boolean {
  if (!form.value || !hasDraftRecipient(draftRecipient.value)) {
    return true;
  }

  const result = commitDraftRecipient(form.value, draftRecipient.value);
  if (result.error) {
    error.value = result.error;
    if (options.openOnError) {
      openRecipientPanel();
    }
    return false;
  }

  form.value = result.form;
  draftRecipient.value = result.draft;
  error.value = "";
  return true;
}

function openRecipientPanel() {
  openTelegram.value = true;
  error.value = "";
  recipientPanelOpen.value = true;
}

function closeRecipientPanel() {
  recipientPanelOpen.value = false;
  draftRecipient.value = emptyDraftRecipient();
}

function submitRecipient() {
  if (!form.value) {
    return;
  }

  if (!draftRecipient.value.chat_id.trim()) {
    error.value = t("settings.chatIdRequired");
    return;
  }

  const result = commitDraftRecipient(form.value, draftRecipient.value);
  if (result.error) {
    error.value = result.error;
    return;
  }

  form.value = result.form;
  draftRecipient.value = result.draft;
  error.value = "";
  recipientPanelOpen.value = false;
}

function removeRecipient(index: number) {
  form.value?.telegram_recipients.splice(index, 1);
}

function discardChanges() {
  if (!savedForm.value) {
    return;
  }
  form.value = cloneNotificationSettings(savedForm.value);
  botTokenInput.value = "";
  draftRecipient.value = emptyDraftRecipient();
  recipientPanelOpen.value = false;
  error.value = "";
}

async function saveSettings() {
  if (!form.value) {
    return;
  }

  if (!applyDraftRecipient({ openOnError: true })) {
    return;
  }

  saving.value = true;
  error.value = "";

  const payload: NotificationSettingsUpdate = {
    telegram_enabled: form.value.telegram_enabled,
    telegram_bot_username: form.value.telegram_bot_username.trim(),
    telegram_recipients: form.value.telegram_recipients,
    default_reminder_interval_minutes: form.value.default_reminder_interval_minutes,
    stale_in_progress_minutes: form.value.stale_in_progress_minutes,
    stale_planned_minutes: form.value.stale_planned_minutes,
    quiet_hours_start: form.value.quiet_hours_start || null,
    quiet_hours_end: form.value.quiet_hours_end || null,
  };

  if (botTokenInput.value.trim()) {
    payload.telegram_bot_token = botTokenInput.value.trim();
  }

  try {
    const updated = await saveNotificationSettings(payload);
    form.value = updated;
    savedForm.value = cloneNotificationSettings(updated);
    botTokenInput.value = "";
    toast.success(t("common.saved"));
  } catch (saveError) {
    error.value =
      saveError instanceof Error ? saveError.message : t("errors.saveSettings");
  } finally {
    saving.value = false;
  }
}

watch(
  () => form.value?.telegram_enabled,
  (enabled) => {
    if (enabled) {
      if (telegramSetupIssues.value.length > 0) {
        openTelegram.value = true;
      }
      void runBotCheck({ silent: true });
    }
  },
);

watch(hasBotToken, (hasToken) => {
  if (hasToken && form.value?.telegram_enabled) {
    void runBotCheck({ silent: true });
  }
});

onMounted(loadSettings);
</script>

<template>
  <div class="settings-page">
    <div class="board-shell settings-board-shell">
      <header class="board-toolbar shrink-0">
        <div class="board-toolbar-info">
          <h1 class="page-title">{{ $t("settings.notificationsTitle") }}</h1>
          <p class="page-meta">{{ headerMeta }}</p>
        </div>

        <div v-if="isDirty && form" class="board-toolbar-actions">
          <button class="btn-ghost px-4 py-2 text-sm" type="button" :disabled="saving" @click="discardChanges">
            {{ $t("common.cancel") }}
          </button>
          <button
            class="btn-primary px-4 py-2 text-sm disabled:opacity-60"
            type="button"
            :disabled="saving"
            @click="saveSettings"
          >
            {{ saving ? $t("common.saving") : $t("common.save") }}
          </button>
        </div>
      </header>

      <p v-if="error" class="alert-error mx-4 mt-3 shrink-0">{{ error }}</p>

      <div v-if="loading" class="settings-body settings-body-center">
        <div class="loading-state">
          <span class="loading-spinner" aria-hidden="true" />
          <p class="text-sm text-(--color-text-secondary)">{{ $t("common.loading") }}</p>
        </div>
      </div>

      <div v-else-if="loadFailed" class="settings-body settings-body-center">
        <div class="jobs-empty">
          <span class="jobs-empty-icon">
            <BellAlertIcon class="size-7" />
          </span>
          <p class="jobs-empty-title">{{ $t("errors.loadSettings") }}</p>
          <button class="btn btn-secondary mt-2" type="button" @click="loadSettings">
            <ArrowPathIcon class="icon-sm" />
            {{ $t("common.retry") }}
          </button>
        </div>
      </div>

      <div v-else-if="form" class="settings-body settings-body-split">
        <div class="notify-split">
          <section class="settings-panel notify-rules-panel">
            <header class="settings-panel-header">
              <div class="notify-panel-head">
                <span class="notify-fold-icon notify-fold-icon-rules">
                  <ClockIcon />
                </span>
                <div>
                  <p class="drawer-eyebrow">{{ $t("settings.notificationsTitle") }}</p>
                  <h2 class="settings-panel-title">{{ $t("settings.notificationRules") }}</h2>
                </div>
              </div>
            </header>

            <div class="settings-panel-body">
              <form class="task-form notify-rules-form">
                <label class="form-field">
                  <span class="form-label">{{ $t("settings.reminderInterval") }}</span>
                  <input
                    v-model.number="form.default_reminder_interval_minutes"
                    class="field px-3 py-2"
                    type="number"
                    min="5"
                    step="5"
                  />
                  <span class="notify-field-hint">≈ {{ formatDuration(form.default_reminder_interval_minutes) }}</span>
                </label>

                <label class="form-field">
                  <span class="form-label">{{ $t("settings.staleInProgress") }}</span>
                  <input
                    v-model.number="form.stale_in_progress_minutes"
                    class="field px-3 py-2"
                    type="number"
                    min="5"
                    step="5"
                  />
                  <span class="notify-field-hint">{{ formatDuration(form.stale_in_progress_minutes) }}</span>
                </label>

                <label class="form-field">
                  <span class="form-label">{{ $t("settings.stalePlanned") }}</span>
                  <input
                    v-model.number="form.stale_planned_minutes"
                    class="field px-3 py-2"
                    type="number"
                    min="5"
                    step="5"
                  />
                  <span class="notify-field-hint">{{ formatDuration(form.stale_planned_minutes) }}</span>
                </label>

                <div class="notify-rules-quiet">
                  <p class="jobs-filter-label">{{ $t("settings.quietHours") }}</p>
                  <div class="notify-rules-quiet-fields">
                    <label class="form-field">
                      <span class="form-label">{{ $t("settings.quietFrom") }}</span>
                      <input v-model="form.quiet_hours_start" class="field px-3 py-2" type="time" />
                    </label>
                    <label class="form-field">
                      <span class="form-label">{{ $t("settings.quietTo") }}</span>
                      <input v-model="form.quiet_hours_end" class="field px-3 py-2" type="time" />
                    </label>
                  </div>
                  <p class="notify-field-hint">{{ $t("settings.quietHint") }}</p>
                </div>
              </form>
            </div>
          </section>

          <div class="notify-channels-column">
            <section class="notify-fold notify-channel-fold" :class="{ 'notify-fold-open': openTelegram }">
              <button type="button" class="notify-fold-trigger" @click="openTelegram = !openTelegram">
                <span class="notify-fold-icon notify-fold-icon-telegram">
                  <ChatBubbleLeftRightIcon />
                </span>
                <span class="notify-fold-text">
                  <span class="notify-fold-title-row">
                    <span class="notify-fold-title">Telegram</span>
                    <ExclamationTriangleIcon
                      v-if="telegramSetupIssues.length"
                      class="notify-setup-warn"
                      :title="telegramSetupWarning"
                    />
                  </span>
                  <span class="notify-fold-summary">{{ telegramSummary }}</span>
                </span>
                <span
                  v-if="form.telegram_enabled"
                  class="notify-bot-status"
                  :class="botHealth.class"
                  :title="botHealth.title"
                >
                  {{ botHealth.label }}
                  <span
                    v-if="form.telegram_bot_checked_at && !telegramSetupIssues.length"
                    class="notify-bot-status-time"
                  >
                    {{ formatDateTime(form.telegram_bot_checked_at) }}
                  </span>
                </span>
                <label class="notify-switch" :title="$t('common.enabled')" @click.stop>
                  <input v-model="form.telegram_enabled" type="checkbox" />
                  <span class="notify-switch-track" aria-hidden="true">
                    <span class="notify-switch-thumb" />
                  </span>
                </label>
                <ChevronDownIcon class="notify-fold-chevron" />
              </button>

              <div v-show="openTelegram" class="notify-fold-body notify-channel-body">
                <p v-if="telegramSetupIssues.length" class="notify-setup-alert">
                  <ExclamationTriangleIcon />
                  {{ telegramSetupWarning }}
                </p>

                <form class="task-form notify-channel-form">
                  <label class="form-field">
                    <span class="form-label">{{ $t("settings.botToken") }}</span>
                    <input
                      v-model="botTokenInput"
                      class="field px-3 py-2 notify-token-field"
                      type="text"
                      :placeholder="
                        form.telegram_bot_token_set
                          ? $t('settings.tokenSavedPlaceholder')
                          : $t('settings.tokenPlaceholder')
                      "
                      autocomplete="off"
                      spellcheck="false"
                    />
                  </label>
                  <label class="form-field">
                    <span class="form-label">@username</span>
                    <input
                      v-model="form.telegram_bot_username"
                      class="field px-3 py-2"
                      type="text"
                      placeholder="@my_bot"
                    />
                  </label>
                </form>

                <div class="notify-recipients-block">
                  <div class="notify-recipients-head">
                    <div class="notify-recipients-head-copy">
                      <span class="form-label">{{ $t("settings.recipients") }}</span>
                      <span class="notify-field-hint">@userinfobot · @getidsbot</span>
                    </div>
                    <button
                      class="btn btn-secondary notify-recipients-add-btn"
                      type="button"
                      @click="openRecipientPanel"
                    >
                      <PlusIcon class="icon-sm" />
                      {{ $t("settings.addRecipient") }}
                    </button>
                  </div>

                  <ul v-if="form.telegram_recipients.length" class="notify-recipient-list">
                    <li
                      v-for="(item, index) in form.telegram_recipients"
                      :key="item.chat_id"
                      class="notify-recipient-item"
                    >
                      <span
                        class="notify-recipient-badge"
                        :class="
                          item.kind === 'group'
                            ? 'notify-recipient-badge-group'
                            : 'notify-recipient-badge-user'
                        "
                      >
                        <UserGroupIcon v-if="item.kind === 'group'" />
                        <UserIcon v-else />
                      </span>
                      <div class="notify-recipient-main">
                        <span class="notify-recipient-name">{{ item.label || item.chat_id }}</span>
                        <span class="notify-recipient-meta">{{ item.chat_id }}</span>
                      </div>
                      <button
                        class="icon-btn notify-icon-btn"
                        type="button"
                        :title="$t('common.delete')"
                        @click="removeRecipient(index)"
                      >
                        <TrashIcon class="icon-sm" />
                      </button>
                    </li>
                  </ul>
                  <p v-else class="notify-recipient-empty">{{ $t("settings.noRecipients") }}</p>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <Transition name="slide-panel">
        <div
          v-if="recipientPanelOpen && form"
          class="drawer-backdrop"
          @click.self="closeRecipientPanel"
        >
          <aside
            class="drawer-panel drawer-panel-narrow"
            role="dialog"
            aria-labelledby="recipient-drawer-title"
            aria-modal="true"
          >
            <header class="drawer-header">
              <div>
                <p class="drawer-eyebrow">Telegram</p>
                <h2 id="recipient-drawer-title" class="drawer-title">
                  {{ $t("settings.newRecipient") }}
                </h2>
              </div>
              <button class="icon-btn" type="button" @click="closeRecipientPanel">
                <XMarkIcon class="icon-sm" />
              </button>
            </header>

            <div class="drawer-body">
              <p v-if="error" class="alert-error">{{ error }}</p>

              <form class="task-form" @submit.prevent="submitRecipient">
                <label class="form-field">
                  <span class="form-label">{{ $t("common.type") }}</span>
                  <select v-model="draftRecipient.kind" class="field px-3 py-2">
                    <option value="user">{{ $t("settings.recipientTypeUser") }}</option>
                    <option value="group">{{ $t("settings.recipientTypeGroup") }}</option>
                  </select>
                </label>

                <label class="form-field">
                  <span class="form-label">{{ $t("common.name") }}</span>
                  <input
                    v-model="draftRecipient.label"
                    class="field px-3 py-2"
                    type="text"
                    :placeholder="$t('settings.recipientNamePlaceholder')"
                  />
                </label>

                <label class="form-field">
                  <span class="form-label">{{ $t("settings.chatId") }}</span>
                  <input
                    v-model="draftRecipient.chat_id"
                    class="field px-3 py-2"
                    type="text"
                    placeholder="-1001234567890"
                    required
                  />
                  <span class="notify-field-hint">{{ $t("settings.chatIdHint") }}</span>
                </label>
              </form>
            </div>

            <footer class="drawer-footer">
              <button class="btn-primary px-4 py-2 text-sm" type="button" @click="submitRecipient">
                {{ $t("settings.addRecipient") }}
              </button>
            </footer>
          </aside>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>
