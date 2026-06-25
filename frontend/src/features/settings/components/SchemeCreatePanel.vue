<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import { PlusIcon } from "@heroicons/vue/24/outline";

import ConfirmDialog from "@/components/ConfirmDialog.vue";
import { useActionFeedback } from "@/composables/useActionFeedback";
import { createBoardScheme } from "@/features/settings/api";

const props = defineProps<{
  disabled?: boolean;
  disabledTitle?: string;
}>();

const emit = defineEmits<{
  created: [];
  cancel: [];
}>();

const { t } = useI18n();
const feedback = useActionFeedback();
const name = ref("");
const description = ref("");
const saving = ref(false);
const formError = ref("");
const confirmOpen = ref(false);

function requestSubmit() {
  if (props.disabled) {
    return;
  }
  const trimmed = name.value.trim();
  if (!trimmed) {
    formError.value = t("settings.schemeNameRequired");
    return;
  }
  formError.value = "";
  confirmOpen.value = true;
}

async function confirmCreate() {
  const trimmed = name.value.trim();
  if (!trimmed) {
    return;
  }

  saving.value = true;
  formError.value = "";
  try {
    await createBoardScheme({
      name: trimmed,
      description: description.value.trim(),
      switch: false,
    });
    confirmOpen.value = false;
    feedback.successKey("toast.schemeCreated");
    emit("created");
  } catch (createError) {
    feedback.fromError(createError, "errors.createScheme");
    confirmOpen.value = false;
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <section class="columns-scheme-create" role="region" :aria-label="$t('settings.newScheme')">
    <h3 class="columns-scheme-create-title">{{ $t("settings.newScheme") }}</h3>
    <p class="columns-scheme-create-hint">{{ $t("settings.schemeCreateHint") }}</p>

    <Transition name="scheme-alert-slide">
      <p v-if="formError" key="form-error" class="alert-error">{{ formError }}</p>
    </Transition>

    <form class="columns-scheme-create-form" @submit.prevent="requestSubmit">
      <label class="form-field">
        <span class="form-label">{{ $t("common.name") }}</span>
        <input
          v-model="name"
          class="field px-3 py-2"
          :placeholder="$t('settings.schemeNamePlaceholder')"
          required
          type="text"
        />
      </label>

      <label class="form-field">
        <span class="form-label">{{ $t("settings.schemeDescription") }}</span>
        <textarea
          v-model="description"
          class="field px-3 py-2"
          :placeholder="$t('settings.schemeDescriptionPlaceholder')"
          rows="2"
        />
      </label>

      <div class="columns-scheme-create-actions">
        <button class="btn-ghost px-3 py-1.5 text-sm" type="button" @click="emit('cancel')">
          {{ $t("common.cancel") }}
        </button>
        <button
          class="btn-primary px-3 py-1.5 text-sm disabled:opacity-60"
          type="submit"
          :disabled="saving || disabled"
          :title="disabled ? disabledTitle : undefined"
        >
          <PlusIcon class="icon-sm" />
          {{ saving ? $t("common.saving") : $t("settings.createScheme") }}
        </button>
      </div>
    </form>
  </section>

  <ConfirmDialog
    v-model="confirmOpen"
    :title="$t('settings.schemeCreateConfirmTitle')"
    :message="$t('settings.schemeCreateConfirm', { name: name.trim() })"
    :confirm-label="$t('settings.createScheme')"
    :loading="saving"
    danger
    @confirm="confirmCreate"
  />
</template>
