<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { ArrowRightEndOnRectangleIcon, Squares2X2Icon } from "@heroicons/vue/24/outline";

import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const auth = useAuthStore();

const username = ref("");
const password = ref("");
const error = ref("");
const isSubmitting = ref(false);

async function submit() {
  error.value = "";
  isSubmitting.value = true;

  try {
    await auth.login(username.value, password.value);
    await router.push("/");
  } catch {
    error.value = "Неверный логин или пароль";
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<template>
  <main class="login-shell">
    <form class="login-panel" @submit.prevent="submit">
      <div class="mb-6">
        <div class="mb-4 flex items-center gap-3">
          <span class="sidebar-mark">
            <Squares2X2Icon class="icon-md text-white" />
          </span>
          <div>
            <div class="sidebar-title">Cadence</div>
            <div class="sidebar-subtitle">Недельный ритм</div>
          </div>
        </div>
        <h1 class="text-xl font-semibold text-[var(--color-text)]">Вход</h1>
        <p class="mt-1 text-sm text-[var(--color-text-secondary)]">
          Личная канбан-доска для недельного ритма.
        </p>
      </div>

      <label class="block text-sm text-[var(--color-text-secondary)]">
        Логин
        <input
          v-model="username"
          class="field mt-1.5 px-3 py-2"
          autocomplete="username"
          required
          type="text"
        />
      </label>

      <label class="mt-3 block text-sm text-[var(--color-text-secondary)]">
        Пароль
        <input
          v-model="password"
          class="field mt-1.5 px-3 py-2"
          autocomplete="current-password"
          required
          type="password"
        />
      </label>

      <p v-if="error" class="alert-error mt-4">
        {{ error }}
      </p>

      <button
        class="btn-primary mt-5 w-full px-4 py-2.5 disabled:opacity-60"
        :disabled="isSubmitting"
        type="submit"
      >
        <ArrowRightEndOnRectangleIcon class="icon-sm" />
        Войти
      </button>
    </form>
  </main>
</template>
