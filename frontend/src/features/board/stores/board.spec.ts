import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as boardApi from "@/features/board/api";
import { useBoardStore } from "@/features/board/stores/board";

vi.mock("@/features/board/api", () => ({
  fetchBoard: vi.fn(),
  fetchTags: vi.fn(),
  createTask: vi.fn(),
  moveTask: vi.fn(),
  fetchTask: vi.fn(),
  updateTask: vi.fn(),
  closeTask: vi.fn(),
}));

describe("useBoardStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.resetAllMocks();
  });

  it("loads board data", async () => {
    vi.mocked(boardApi.fetchBoard).mockResolvedValue({
      board: { id: 1, name: "Главная" },
      week: { iso_year: 2026, iso_week: 6 },
      columns: [
        {
          id: 1,
          name: "Бэклог",
          system_type: "backlog",
          position: 0,
          color: "slate",
          wip_limit: null,
          tasks: [],
        },
      ],
    });

    const board = useBoardStore();
    await board.loadBoard();

    expect(board.boardName).toBe("Главная");
    expect(board.columns).toHaveLength(1);
    expect(board.loading).toBe(false);
  });

  it("filters tasks by search query", async () => {
    vi.mocked(boardApi.fetchBoard).mockResolvedValue({
      board: { id: 1, name: "Главная" },
      week: { iso_year: 2026, iso_week: 6 },
      columns: [
        {
          id: 1,
          name: "Бэклог",
          system_type: "backlog",
          position: 0,
          color: "slate",
          wip_limit: null,
          tasks: [
            {
              id: 10,
              title: "Alpha",
              priority: "normal",
              position: 0,
              column_id: 1,
              week_id: null,
              due_at: null,
              source: "ui",
              tags: [],
            },
            {
              id: 11,
              title: "Beta",
              priority: "high",
              position: 1,
              column_id: 1,
              week_id: null,
              due_at: null,
              source: "ui",
              tags: [],
            },
          ],
        },
      ],
    });

    const board = useBoardStore();
    await board.loadBoard();
    board.searchQuery = "alp";

    expect(board.visibleTasks(1).map((task) => task.title)).toEqual(["Alpha"]);
    expect(board.filtersActive).toBe(true);
  });
});
