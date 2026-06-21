<script setup lang="ts">
import { useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();

async function logout() {
  await auth.logout();
  await router.push("/login");
}
</script>

<template>
  <main class="grid min-h-screen place-items-center bg-slate-50 p-8">
    <section class="max-w-2xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
      <div class="flex items-center justify-between gap-4">
        <p class="text-sm font-semibold uppercase tracking-wide text-blue-600">Cadence</p>
        <div class="flex items-center gap-4">
          <button
            class="text-sm font-medium text-slate-500 hover:text-slate-900"
            type="button"
            @click="router.push('/settings/columns')"
          >
            Колонки
          </button>
          <button
            class="text-sm font-medium text-slate-500 hover:text-slate-900"
            type="button"
            @click="logout"
          >
            Выйти
          </button>
        </div>
      </div>
      <h1 class="mt-3 text-4xl font-semibold text-slate-900">Personal weekly task rhythm</h1>
      <p class="mt-4 text-lg leading-7 text-slate-600">
        Привет, {{ auth.user?.username }}. Application shell is ready. Kanban, imports,
        jobs, Telegram, archive, and analytics will arrive in the planned stages.
      </p>
    </section>
  </main>
</template>
