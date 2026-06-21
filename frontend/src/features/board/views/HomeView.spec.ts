import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HomeView from "./HomeView.vue";

describe("HomeView", () => {
  it("renders the shell title", () => {
    const wrapper = mount(HomeView);

    expect(wrapper.text()).toContain("Cadence");
    expect(wrapper.text()).toContain("Personal weekly task rhythm");
  });
});
