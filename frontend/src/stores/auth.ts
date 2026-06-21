import { defineStore } from "pinia";

import { apiFetch } from "@/shared/api/http";

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
}

interface AuthState {
  user: User | null;
  loaded: boolean;
}

export const useAuthStore = defineStore("auth", {
  state: (): AuthState => ({
    user: null,
    loaded: false,
  }),
  actions: {
    async loadMe() {
      const response = await apiFetch("/api/v1/auth/me/");
      this.user = response.ok ? await response.json() : null;
      this.loaded = true;
    },
    async login(username: string, password: string) {
      const response = await apiFetch("/api/v1/auth/login/", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        throw new Error("Invalid username or password.");
      }

      const data = await response.json();
      this.user = data.user;
      this.loaded = true;
    },
    async logout() {
      await apiFetch("/api/v1/auth/logout/", { method: "POST" });
      this.user = null;
      this.loaded = true;
    },
  },
});
