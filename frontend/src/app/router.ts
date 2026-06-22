import { createRouter, createWebHistory } from "vue-router";

import AppLayout from "@/components/layout/AppLayout.vue";
import LoginView from "@/features/auth/views/LoginView.vue";
import BoardView from "@/features/board/views/BoardView.vue";
import ColumnsSettingsView from "@/features/settings/views/ColumnsSettingsView.vue";
import NotificationsSettingsView from "@/features/settings/views/NotificationsSettingsView.vue";
import JobsView from "@/features/jobs/views/JobsView.vue";
import { useAuthStore } from "@/stores/auth";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: LoginView,
    },
    {
      path: "/",
      component: AppLayout,
      meta: { requiresAuth: true },
      children: [
        {
          path: "",
          redirect: { name: "board" },
        },
        {
          path: "board",
          name: "board",
          component: BoardView,
        },
        {
          path: "settings/columns",
          name: "settings-columns",
          component: ColumnsSettingsView,
        },
        {
          path: "settings/notifications",
          name: "settings-notifications",
          component: NotificationsSettingsView,
        },
        {
          path: "settings/telegram",
          redirect: { name: "settings-notifications" },
        },
        {
          path: "jobs",
          name: "jobs",
          component: JobsView,
        },
      ],
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
    return { name: "board" };
  }

  return true;
});
