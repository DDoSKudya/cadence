import { describe, expect, it } from "vitest";

import { readApiError } from "./api-error";

function jsonResponse(body: unknown, status = 400): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("readApiError EC", () => {
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
});
