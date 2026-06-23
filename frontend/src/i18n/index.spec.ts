import { beforeEach, describe, expect, it } from "vitest";

import { i18n, setI18nLocale, t } from "@/i18n";

describe("i18n EC", () => {
  beforeEach(() => {
    setI18nLocale("en");
  });

  it("ec_defaults_to_english", () => {
    expect(i18n.global.locale.value).toBe("en");
    expect(t("nav.board")).toBe("Board");
  });

  it("ec_switches_to_russian", () => {
    setI18nLocale("ru");
    expect(t("nav.board")).toBe("Доска");
  });

  it("ec_plural_english_uses_two_forms", () => {
    expect(t("board.taskCount", 1)).toBe("1 task");
    expect(t("board.taskCount", 5)).toBe("5 tasks");
  });

  it("ec_plural_russian_uses_three_forms", () => {
    setI18nLocale("ru");
    expect(t("board.taskCount", 1)).toBe("1 задача");
    expect(t("board.taskCount", 2)).toBe("2 задачи");
    expect(t("board.taskCount", 5)).toBe("5 задач");
  });

  it("ec_named_interpolation", () => {
    expect(t("board.wipLimit", { count: 3 })).toBe("WIP 3");
  });
});
