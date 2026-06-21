import { describe, expect, it } from "vitest";

import { parseImportFile, priorityLabel } from "./parse-import";

function jsonFile(name: string, payload: unknown): File {
  return new File([JSON.stringify(payload)], name, { type: "application/json" });
}

describe("parseImportFile", () => {
  it("parses valid payload", async () => {
    const file = jsonFile("batch.json", {
      schema_version: "1.0",
      idempotency_key: "test-1",
      tasks: [{ title: "Задача", column: "planned", priority: "high", tags: ["a"] }],
    });

    const result = await parseImportFile(file);

    expect(result.status).toBe("valid");
    if (result.status === "valid") {
      expect(result.tasks).toHaveLength(1);
      expect(result.tasks[0]?.title).toBe("Задача");
    }
  });

  it("returns invalid preview for broken json", async () => {
    const file = new File(["{"], "broken.json", { type: "application/json" });

    const result = await parseImportFile(file);

    expect(result.status).toBe("invalid");
    if (result.status === "invalid") {
      expect(result.error).toBe("Некорректный JSON");
    }
  });

  it("returns invalid preview for schema errors without throwing", async () => {
    const file = jsonFile("empty.json", {
      schema_version: "1.0",
      idempotency_key: "x",
      tasks: [],
    });

    const result = await parseImportFile(file);

    expect(result.status).toBe("invalid");
  });
});

describe("priorityLabel", () => {
  it("maps known priorities", () => {
    expect(priorityLabel("high")).toBe("Высокий");
  });
});
