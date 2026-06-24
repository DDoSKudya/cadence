import { createRouter, createWebHistory } from "vue-router";

import AppLayout from "@/components/layout/AppLayout.vue";
import LoginView from "@/features/auth/views/LoginView.vue";
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
          component: () => import("@/features/board/views/BoardView.vue"),
        },
        {
          path: "archive",
          name: "archive",
          component: () => import("@/features/archive/views/ArchiveView.vue"),
        },
        {
          path: "week/:id/review",
          name: "week-review",
          component: () => import("@/features/week-review/views/WeekReviewView.vue"),
        },
        {
          path: "settings/general",
          name: "settings-general",
          component: () => import("@/features/settings/views/GeneralSettingsView.vue"),
        },
        {
          path: "settings/columns",
          name: "settings-columns",
          component: () => import("@/features/settings/views/ColumnsSettingsView.vue"),
        },
        {
          path: "settings/notifications",
          name: "settings-notifications",
          component: () => import("@/features/settings/views/NotificationsSettingsView.vue"),
        },
        {
          path: "settings/telegram",
          redirect: { name: "settings-notifications" },
        },
        {
          path: "analytics",
          name: "analytics",
          component: () => import("@/features/analytics/views/AnalyticsView.vue"),
        },
        {
          path: "jobs",
          redirect: { name: "settings-general", query: { service: "worker" } },
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
