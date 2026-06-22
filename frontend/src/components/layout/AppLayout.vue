<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import {
  ArrowLeftStartOnRectangleIcon,
  BellAlertIcon,
  Cog6ToothIcon,
  QueueListIcon,
  Squares2X2Icon,
  ViewColumnsIcon,
} from "@heroicons/vue/24/outline";

import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();

const displayName = computed(() => {
  const user = auth.user;
  if (!user) {
    return "";
  }
  const fullName = [user.first_name, user.last_name].filter(Boolean).join(" ").trim();
  return fullName || user.username;
});

const initials = computed(() => {
  const user = auth.user;
  if (!user) {
    return "?";
  }
  const parts = [user.first_name, user.last_name].filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0]![0]!}${parts[1]![0]!}`.toUpperCase();
  }
  if (parts.length === 1) {
    return parts[0]!.slice(0, 2).toUpperCase();
  }
  return user.username.slice(0, 2).toUpperCase();
});

async function logout() {
  await auth.logout();
  await router.push("/login");
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="sidebar-brand">
        <span class="sidebar-mark">
          <Squares2X2Icon class="icon-md text-white" />
        </span>
        <div>
          <div class="sidebar-title">Cadence</div>
          <div class="sidebar-subtitle">Недельный ритм</div>
        </div>
      </div>

      <nav class="sidebar-nav">
        <RouterLink active-class="nav-link-active" class="nav-link" to="/board">
          <ViewColumnsIcon class="icon-md" />
          Доска
        </RouterLink>
        <RouterLink active-class="nav-link-active" class="nav-link" to="/settings/columns">
          <Cog6ToothIcon class="icon-md" />
          Колонки
        </RouterLink>
        <RouterLink active-class="nav-link-active" class="nav-link" to="/settings/notifications">
          <BellAlertIcon class="icon-md" />
          Оповещение
        </RouterLink>
        <RouterLink active-class="nav-link-active" class="nav-link" to="/jobs">
          <QueueListIcon class="icon-md" />
          Задачи
        </RouterLink>
      </nav>

      <div v-if="auth.user" class="sidebar-footer">
        <div class="user-card">
          <span class="user-avatar" aria-hidden="true">{{ initials }}</span>
          <div class="user-card-text">
            <span class="user-card-name">{{ displayName }}</span>
            <span class="user-card-meta">@{{ auth.user.username }}</span>
          </div>
          <button
            class="user-card-logout"
            type="button"
            title="Выйти"
            aria-label="Выйти"
            @click="logout"
          >
            <ArrowLeftStartOnRectangleIcon class="icon-sm" />
          </button>
        </div>
      </div>
    </aside>

    <div class="main-area">
      <main class="page">
        <RouterView v-slot="{ Component }">
          <transition mode="out-in" name="page-fade">
            <component :is="Component" />
          </transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>
