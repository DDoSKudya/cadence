import { createRouter, createWebHistory } from "vue-router";

import LoginView from "@/features/auth/views/LoginView.vue";
import HomeView from "@/features/board/views/HomeView.vue";
import ColumnsSettingsView from "@/features/settings/views/ColumnsSettingsView.vue";
import { useAuthStore } from "@/stores/auth";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
      meta: { requiresAuth: true },
    },
    {
      path: "/settings/columns",
      name: "settings-columns",
      component: ColumnsSettingsView,
      meta: { requiresAuth: true },
    },
    {
      path: "/login",
      name: "login",
      component: LoginView,
    },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();

  if (!auth.loaded) {
    await auth.loadMe();
  }

  if (to.meta.requiresAuth && !auth.user) {
    return { name: "login" };
  }

  if (to.name === "login" && auth.user) {
    return { name: "home" };
  }

  return true;
});
