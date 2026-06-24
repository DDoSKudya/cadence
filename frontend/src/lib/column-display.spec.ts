import { describe, expect, it } from "vitest";

import { boardDisplayName, columnDisplayName } from "@/lib/column-display";

describe("column display localization", () => {
  it("shows localized labels for locked default columns", () => {
    expect(
      columnDisplayName({
        name: "Бэклог",
        system_type: "backlog",
        is_locked: true,
      }),
    ).toBe("Backlog");
    expect(
      columnDisplayName({
        name: "В работе",
        system_type: "in_progress",
        is_locked: true,
      }),
    ).toBe("In progress");
    expect(
      columnDisplayName({
        name: "Готово",
        system_type: "ready",
        is_locked: true,
      }),
    ).toBe("Ready");
  });

  it("keeps custom names for editable columns", () => {
    expect(
      columnDisplayName({
        name: "QA",
        system_type: "backlog",
        is_locked: false,
      }),
    ).toBe("QA");
  });

  it("localizes the default board title", () => {
    expect(boardDisplayName({ name: "Главная", is_default: true })).toBe("Main");
    expect(boardDisplayName({ name: "Team board", is_default: false })).toBe("Team board");
  });
});
