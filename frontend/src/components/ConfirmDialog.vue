<script setup lang="ts">
const visible = defineModel<boolean>({ default: false });

const props = defineProps<{
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  loading?: boolean;
}>();

const emit = defineEmits<{
  confirm: [];
  cancel: [];
}>();

function dismiss() {
  if (props.loading) {
    return;
  }
  visible.value = false;
  emit("cancel");
}

function confirm() {
  if (props.loading) {
    return;
  }
  emit("confirm");
}
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="visible"
        class="modal-backdrop"
        role="presentation"
        @click.self="dismiss"
      >
        <section
          class="modal-panel confirm-dialog-panel"
          role="alertdialog"
          aria-modal="true"
          :aria-labelledby="title ? 'confirm-dialog-title' : undefined"
          :aria-describedby="message ? 'confirm-dialog-message' : undefined"
          @click.stop
        >
          <header class="modal-header">
            <h2 id="confirm-dialog-title" class="modal-title">{{ title }}</h2>
          </header>

          <div class="modal-body">
            <p id="confirm-dialog-message" class="confirm-dialog-message">{{ message }}</p>
          </div>

          <footer class="modal-footer">
            <button
              class="btn-ghost px-4 py-2 text-sm"
              type="button"
              :disabled="loading"
              @click="dismiss"
            >
              {{ cancelLabel || $t("common.cancel") }}
            </button>
            <button
              class="px-4 py-2 text-sm"
              :class="danger ? 'btn-danger' : 'btn-primary'"
              type="button"
              :disabled="loading"
              @click="confirm"
            >
              {{ loading ? $t("common.saving") : confirmLabel || $t("common.confirm") }}
            </button>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>
