<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

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
  <main class="grid min-h-screen place-items-center bg-slate-50 p-6">
    <form
      class="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
      @submit.prevent="submit"
    >
      <p class="text-sm font-semibold uppercase tracking-wide text-blue-600">Cadence</p>
      <h1 class="mt-2 text-2xl font-semibold text-slate-900">Вход</h1>

      <label class="mt-6 block text-sm font-medium text-slate-700">
        Логин
        <input
          v-model="username"
          class="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-blue-500"
          autocomplete="username"
          required
          type="text"
        />
      </label>

      <label class="mt-4 block text-sm font-medium text-slate-700">
        Пароль
        <input
          v-model="password"
          class="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-blue-500"
          autocomplete="current-password"
          required
          type="password"
        />
      </label>

      <p v-if="error" class="mt-4 text-sm text-red-600">{{ error }}</p>

      <button
        class="mt-6 w-full rounded-lg bg-blue-600 px-4 py-2 font-medium text-white disabled:opacity-60"
        :disabled="isSubmitting"
        type="submit"
      >
        Войти
      </button>
    </form>
  </main>
</template>
