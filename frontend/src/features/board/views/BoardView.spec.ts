import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BoardView from "./BoardView.vue";

vi.mock("@/features/board/components/BoardCreateTask.vue", () => ({
  default: { template: "<div />" },
}));
vi.mock("@/features/board/components/BoardImportJson.vue", () => ({
  default: { template: "<div />" },
}));
vi.mock("@/features/board/components/BoardColumn.vue", () => ({
  default: { template: "<div />", props: ["column"] },
}));
vi.mock("@/features/board/components/BoardFilters.vue", () => ({
  default: { template: "<div />" },
}));
vi.mock("@/features/board/components/TaskPanel.vue", () => ({
  default: { template: "<div />" },
}));
vi.mock("@/features/board/components/WeekSwitcher.vue", () => ({
  default: { template: "<div />" },
}));

vi.mock("@/features/board/api", () => ({
  fetchBoard: vi.fn().mockResolvedValue({
    board: { id: 1, name: "Главная" },
    week: { id: 3, iso_year: 2026, iso_week: 6 },
    columns: [],
  }),
  fetchTags: vi.fn().mockResolvedValue([]),
}));

describe("BoardView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("renders board heading", async () => {
    const wrapper = mount(BoardView);
    await wrapper.vm.$nextTick();
    await Promise.resolve();

    expect(wrapper.text()).toContain("Главная");
    expect(wrapper.text()).toContain("колонок");
  });
});
