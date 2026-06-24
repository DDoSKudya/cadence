import { describe, expect, it } from "vitest";

import { statusNodeKey } from "@/features/settings/task-status-graph";

describe("task-status-graph helpers", () => {
  it("uses numeric id as node key", () => {
    expect(statusNodeKey({ id: 42, client_key: "tmp-1" })).toBe("42");
  });

  it("falls back to client key for unsaved nodes", () => {
    expect(statusNodeKey({ id: null, client_key: "tmp-1" })).toBe("tmp-1");
  });

  it("returns empty string when neither id nor client key is set", () => {
    expect(statusNodeKey({ id: null })).toBe("");
  });
});
