<script setup lang="ts">
import { storeToRefs } from "pinia";
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  InformationCircleIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline";

import { useToastStore } from "@/stores/toast";

const toast = useToastStore();
const { items } = storeToRefs(toast);
</script>

<template>
  <Teleport to="body">
    <div class="toast-host" aria-live="polite" aria-relevant="additions text">
      <TransitionGroup name="toast" tag="div" class="toast-stack">
        <article
          v-for="item in items"
          :key="item.id"
          class="toast"
          :class="`toast-${item.type}`"
          role="status"
        >
          <span class="toast-icon-wrap" aria-hidden="true">
            <CheckCircleIcon v-if="item.type === 'success'" class="toast-icon" />
            <ExclamationCircleIcon v-else-if="item.type === 'error'" class="toast-icon" />
            <ExclamationCircleIcon v-else-if="item.type === 'warning'" class="toast-icon" />
            <InformationCircleIcon v-else class="toast-icon" />
          </span>
          <p class="toast-message">{{ item.message }}</p>
          <button
            class="toast-close"
            type="button"
            :aria-label="$t('common.close')"
            @click="toast.remove(item.id)"
          >
            <XMarkIcon class="toast-close-icon" />
          </button>
        </article>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
