import { describe, expect, it } from "vitest";

import { parseImportFile, priorityLabel } from "./parse-import";

function jsonFile(name: string, payload: unknown): File {
  return new File([JSON.stringify(payload)], name, { type: "application/json" });
}

const validPayload = {
  schema_version: "1.0",
  idempotency_key: "key-1",
  source: "mentor",
  tasks: [{ title: "Task", column: "planned", priority: "high", tags: ["a"] }],
};

describe("parseImportFile EC", () => {
  it("ec_valid_json_returns_valid_preview", async () => {
    const result = await parseImportFile(jsonFile("ok.json", validPayload));
    expect(result.status).toBe("valid");
    if (result.status === "valid") {
      expect(result.idempotencyKey).toBe("key-1");
      expect(result.tasks).toHaveLength(1);
    }
  });

  it.each([
    ["not json", "ec_invalid_json"],
    [
      JSON.stringify({ schema_version: "2.0", idempotency_key: "k", tasks: [{}] }),
      "ec_unsupported_schema",
    ],
    [
      JSON.stringify({ schema_version: "1.0", tasks: [{ title: "x" }] }),
      "ec_missing_idempotency_key",
    ],
    [
      JSON.stringify({ schema_version: "1.0", idempotency_key: "k", tasks: [] }),
      "ec_empty_tasks",
    ],
    [
      JSON.stringify({
        schema_version: "1.0",
        idempotency_key: "a".repeat(181),
        tasks: [{ title: "x" }],
      }),
      "ec_idempotency_key_too_long",
    ],
    [
      JSON.stringify({
        schema_version: "1.0",
        idempotency_key: "k",
        tasks: [{ title: "" }],
      }),
      "ec_missing_title",
    ],
    [
      JSON.stringify({
        schema_version: "1.0",
        idempotency_key: "k",
        tasks: [{ title: "x", priority: "urgent" }],
      }),
      "ec_invalid_priority",
    ],
    [
      JSON.stringify({
        schema_version: "1.0",
        idempotency_key: "k",
        week: "2024-W99",
        tasks: [{ title: "x" }],
      }),
      "ec_invalid_week",
    ],
  ])("ec_invalid_import_returns_error: %s", async (content) => {
    const file =
      content === "not json"
        ? new File(["not-json"], "bad.json", { type: "application/json" })
        : new File([content], "bad.json", { type: "application/json" });
    const result = await parseImportFile(file);
    expect(result.status).toBe("invalid");
  });

  it("ec_priority_label_known_and_unknown", () => {
    expect(priorityLabel("high")).toBe("High");
    expect(priorityLabel("custom")).toBe("custom");
  });
});
