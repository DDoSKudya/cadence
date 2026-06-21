export async function readApiError(response: Response, fallback: string): Promise<string> {
  try {
    const data = await response.json();
    if (typeof data === "string" && data.trim()) {
      return data;
    }
    if (data && typeof data === "object") {
      const record = data as Record<string, unknown>;
      if (typeof record.detail === "string" && record.detail.trim()) {
        return record.detail;
      }
      const firstField = Object.values(record).find(
        (value) => Array.isArray(value) && typeof value[0] === "string",
      ) as string[] | undefined;
      if (firstField?.[0]) {
        return firstField[0];
      }
    }
  } catch {
    return fallback;
  }
  return fallback;
}
