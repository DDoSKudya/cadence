import { beforeEach, describe, expect, it } from "vitest";

import { setI18nLocale } from "@/i18n";
import {
  translateColumnLabel,
  translateStatusLabel,
  translateTaskFieldList,
} from "@/lib/workflow-labels";

describe("workflow-labels", () => {
  beforeEach(() => {
    setI18nLocale("ru");
  });

  it("translates_status_by_slug", () => {
    expect(translateStatusLabel("Open", "open")).toBe("Открыта");
    expect(translateStatusLabel("Ready on develop", "ready_on_develop")).toBe("Готова к работе");
  });

  it("translates_column_by_system_type", () => {
    expect(translateColumnLabel("Work in progress", "in_progress")).toBe("В работе");
  });

  it("translates_task_fields", () => {
    expect(translateTaskFieldList(["description", "evidence_url"])).toContain("Описание");
  });
});
