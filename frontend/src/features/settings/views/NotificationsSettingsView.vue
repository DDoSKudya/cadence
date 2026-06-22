<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
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
import { pluralRu } from "@/lib/plural";

const loading = ref(true);
const loadFailed = ref(false);
const saving = ref(false);
const botChecking = ref(false);
const error = ref("");
const notice = ref("");
const form = ref<NotificationSettingsForm | null>(null);
const savedForm = ref<NotificationSettingsForm | null>(null);
const botTokenInput = ref("");
const openTelegram = ref(false);

const draftRecipient = ref<TelegramRecipient>({
  chat_id: "",
  label: "",
  kind: "user",
});

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
    return "Правила и каналы доставки";
  }
  const quiet =
    form.value.quiet_hours_start && form.value.quiet_hours_end
      ? `тихие часы ${form.value.quiet_hours_start}–${form.value.quiet_hours_end}`
      : "без тихих часов";
  return `${formatDuration(form.value.default_reminder_interval_minutes)} · ${quiet}`;
});

const telegramSummary = computed(() => {
  if (!form.value) {
    return "";
  }
  const status = form.value.telegram_enabled ? "вкл." : "выкл.";
  const bot = form.value.telegram_bot_username.trim() || (form.value.telegram_bot_token_set ? "бот ok" : "бот не задан");
  const count = pluralRu(
    form.value.telegram_recipients.length,
    "получатель",
    "получателя",
    "получателей",
  );
  return `${status} · ${bot} · ${count}`;
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
    issues.push("не указан токен бота");
  }
  if (form.value.telegram_recipients.length === 0) {
    issues.push("нет получателей");
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
    return { label: "Проверка…", class: "notify-bot-status-pending", title: "" };
  }

  if (telegramSetupIssues.value.length > 0) {
    return {
      label: "Настройка",
      class: "notify-bot-status-warn",
      title: telegramSetupWarning.value,
    };
  }

  const parts: string[] = [];
  if (form.value.telegram_bot_check_message) {
    parts.push(form.value.telegram_bot_check_message);
  }
  if (form.value.telegram_bot_checked_at) {
    parts.push(`Проверка: ${formatCheckTime(form.value.telegram_bot_checked_at)}`);
  }
  const title = parts.join("\n");

  if (form.value.telegram_bot_check_ok === true) {
    return { label: "Бот OK", class: "notify-bot-status-ok", title };
  }
  if (form.value.telegram_bot_check_ok === false) {
    return { label: "Ошибка", class: "notify-bot-status-error", title };
  }
  return { label: "Не проверен", class: "notify-bot-status-idle", title };
});

function formatCheckTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(minutes: number): string {
  if (!Number.isFinite(minutes) || minutes <= 0) {
    return "—";
  }
  if (minutes % 1440 === 0) {
    const days = minutes / 1440;
    return pluralRu(days, "день", "дня", "дней");
  }
  if (minutes % 60 === 0) {
    const hours = minutes / 60;
    return pluralRu(hours, "час", "часа", "часов");
  }
  return pluralRu(minutes, "минута", "минуты", "минут");
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
        checkError instanceof Error ? checkError.message : "Не удалось проверить бота";
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
      loadError instanceof Error ? loadError.message : "Не удалось загрузить настройки";
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
      openTelegram.value = true;
    }
    return false;
  }

  form.value = result.form;
  draftRecipient.value = result.draft;
  error.value = "";
  return true;
}

function addRecipient() {
  applyDraftRecipient();
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
  draftRecipient.value = { chat_id: "", label: "", kind: "user" };
  error.value = "";
  notice.value = "";
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
  notice.value = "";

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
    notice.value = "Сохранено";
  } catch (saveError) {
    error.value =
      saveError instanceof Error ? saveError.message : "Не удалось сохранить";
  } finally {
    saving.value = false;
  }
}

watch(notice, (value) => {
  if (value) {
    window.setTimeout(() => {
      notice.value = "";
    }, 2500);
  }
});

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
          <h1 class="page-title">Оповещение</h1>
          <p class="page-meta">{{ headerMeta }}</p>
        </div>

        <div v-if="isDirty && form" class="board-toolbar-actions">
          <button class="btn-ghost px-4 py-2 text-sm" type="button" :disabled="saving" @click="discardChanges">
            Отменить
          </button>
          <button
            class="btn-primary px-4 py-2 text-sm disabled:opacity-60"
            type="button"
            :disabled="saving"
            @click="saveSettings"
          >
            {{ saving ? "Сохранение…" : "Сохранить" }}
          </button>
        </div>
      </header>

      <p v-if="error" class="alert-error mx-4 mt-3 shrink-0">{{ error }}</p>
      <p v-else-if="notice" class="alert-notice mx-4 mt-3 shrink-0">{{ notice }}</p>

      <div v-if="loading" class="settings-body settings-body-center">
        <div class="loading-state">
          <span class="loading-spinner" aria-hidden="true" />
          <p class="text-sm text-[var(--color-text-secondary)]">Загрузка…</p>
        </div>
      </div>

      <div v-else-if="loadFailed" class="settings-body settings-body-center">
        <div class="jobs-empty">
          <span class="jobs-empty-icon">
            <BellAlertIcon class="size-7" />
          </span>
          <p class="jobs-empty-title">Не удалось загрузить настройки</p>
          <button class="btn btn-secondary mt-2" type="button" @click="loadSettings">
            <ArrowPathIcon class="icon-sm" />
            Повторить
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
                  <p class="drawer-eyebrow">Напоминания</p>
                  <h2 class="settings-panel-title">Правила</h2>
                </div>
              </div>
            </header>

            <div class="settings-panel-body">
              <form class="task-form notify-rules-form">
                <label class="form-field">
                  <span class="form-label">Интервал, мин</span>
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
                  <span class="form-label">Долго в работе, мин</span>
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
                  <span class="form-label">Долго в плане, мин</span>
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
                  <p class="jobs-filter-label">Тихие часы</p>
                  <div class="notify-rules-quiet-fields">
                    <label class="form-field">
                      <span class="form-label">С</span>
                      <input v-model="form.quiet_hours_start" class="field px-3 py-2" type="time" />
                    </label>
                    <label class="form-field">
                      <span class="form-label">До</span>
                      <input v-model="form.quiet_hours_end" class="field px-3 py-2" type="time" />
                    </label>
                  </div>
                  <p class="notify-field-hint">В этот период напоминания не отправляются</p>
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
                    {{ formatCheckTime(form.telegram_bot_checked_at) }}
                  </span>
                </span>
                <label class="notify-switch" title="Включить канал" @click.stop>
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
                    <span class="form-label">Токен бота</span>
                    <input
                      v-model="botTokenInput"
                      class="field px-3 py-2 notify-token-field"
                      type="text"
                      :placeholder="
                        form.telegram_bot_token_set
                          ? 'Токен сохранён — новый для замены'
                          : '1234567890:ABC...'
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
                    <span class="form-label">Получатели</span>
                    <span class="notify-field-hint">@userinfobot · @getidsbot</span>
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
                        <button class="icon-btn notify-icon-btn" type="button" title="Удалить" @click="removeRecipient(index)">
                        <TrashIcon class="icon-sm" />
                      </button>
                    </li>
                  </ul>
                  <p v-else class="notify-recipient-empty">Нет получателей</p>
                  <p v-if="hasDraftRecipient(draftRecipient)" class="notify-field-hint">
                    Новый получатель будет добавлен при сохранении
                  </p>

                  <form class="notify-add-form" @submit.prevent="addRecipient">
                    <label class="form-field">
                      <span class="form-label">Тип</span>
                      <select v-model="draftRecipient.kind" class="field px-3 py-2">
                        <option value="user">Личный чат</option>
                        <option value="group">Группа</option>
                      </select>
                    </label>
                    <label class="form-field">
                      <span class="form-label">Название</span>
                      <input
                        v-model="draftRecipient.label"
                        class="field px-3 py-2"
                        type="text"
                        placeholder="Например: Я"
                      />
                    </label>
                    <label class="form-field notify-add-chat">
                      <span class="form-label">Chat ID</span>
                      <div class="notify-add-chat-row">
                        <input
                          v-model="draftRecipient.chat_id"
                          class="field px-3 py-2"
                          type="text"
                          placeholder="-1001234567890"
                        />
                        <button class="btn btn-secondary notify-add-btn" type="submit" title="Добавить">
                          <PlusIcon />
                        </button>
                      </div>
                    </label>
                  </form>
                </div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
