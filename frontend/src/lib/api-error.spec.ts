import { beforeEach, describe, expect, it } from "vitest";

import { setI18nLocale } from "@/i18n";
import { formatApiErrorBody, readApiError } from "./api-error";

function jsonResponse(body: unknown, status = 400): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("readApiError EC", () => {
  beforeEach(() => {
    setI18nLocale("ru");
  });

  it("ec_detail_string_returned", async () => {
    const message = await readApiError(jsonResponse({ detail: "Forbidden" }), "fallback");
    expect(message).toBe("Forbidden");
  });

  it("ec_field_error_array_returned", async () => {
    const message = await readApiError(
      jsonResponse({ title: ["This field is required."] }),
      "fallback",
    );
    expect(message).toBe("This field is required.");
  });

  it("ec_plain_string_body_returned", async () => {
    const message = await readApiError(new Response('"Bad"', { status: 400 }), "fallback");
    expect(message).toBe("Bad");
  });

  it("ec_invalid_json_returns_fallback", async () => {
    const message = await readApiError(new Response("not json", { status: 500 }), "fallback");
    expect(message).toBe("fallback");
  });

  it("ec_empty_object_returns_fallback", async () => {
    const message = await readApiError(jsonResponse({}), "fallback");
    expect(message).toBe("fallback");
  });

  it("ec_translates_known_error_code", () => {
    const message = formatApiErrorBody(
      {
        code: "status_required_fields",
        missing_fields: ["description"],
        detail: "Task is missing required fields for this status change.",
      },
      "fallback",
    );
    expect(message).toContain("Описание");
    expect(message).not.toBe("fallback");
  });

  it("ec_translates_column_move_error_with_slugs", () => {
    const message = formatApiErrorBody(
      {
        code: "status_column_move_not_allowed",
        from_status: "Open",
        from_status_slug: "open",
        to_column: "Work in progress",
        to_column_type: "in_progress",
        detail: "Task cannot be moved to this column with the current status.",
      },
      "fallback",
    );
    expect(message).toContain("Открыта");
    expect(message).toContain("В работе");
    expect(message).not.toBe("fallback");
  });

  it("ec_translates_required_fields", () => {
    const message = formatApiErrorBody(
      {
        code: "status_required_fields",
        missing_fields: ["description"],
        detail: "Task is missing required fields for this status change.",
      },
      "fallback",
    );
    expect(message).toContain("Описание");
    expect(message).not.toBe("fallback");
  });
});
