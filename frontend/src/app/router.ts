import { createRouter, createWebHistory } from "vue-router";

import HomeView from "@/features/board/views/HomeView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
    },
  ],
});
