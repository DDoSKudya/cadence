import { describe, expect, it } from "vitest";

import { isTerminalBoardColumn } from "@/features/board/columns";

describe("board columns", () => {
  it("detects_last_column_as_terminal", () => {
    const columns = [
      { id: 1, position: 0 },
      { id: 2, position: 1 },
      { id: 3, position: 2 },
    ];
    expect(isTerminalBoardColumn(3, columns)).toBe(true);
    expect(isTerminalBoardColumn(1, columns)).toBe(false);
  });
});
