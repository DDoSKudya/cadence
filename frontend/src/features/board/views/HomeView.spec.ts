import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "@/stores/auth";

import HomeView from "./HomeView.vue";

vi.mock("vue-router", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

describe("HomeView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    const auth = useAuthStore();
    auth.user = {
      id: 1,
      username: "owner",
      email: "owner@example.com",
      first_name: "",
      last_name: "",
      is_staff: true,
    };
    auth.loaded = true;
  });

  it("renders the shell title", () => {
    const wrapper = mount(HomeView);

    expect(wrapper.text()).toContain("Cadence");
    expect(wrapper.text()).toContain("Personal weekly task rhythm");
  });
});
