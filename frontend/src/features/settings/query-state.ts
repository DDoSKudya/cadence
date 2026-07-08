export function readAllowedQueryValue<T extends string>(
  value: unknown,
  allowed: readonly T[],
): T | null {
  return typeof value === "string" && allowed.includes(value as T) ? (value as T) : null;
}

export function replaceSettingsQueryParam(
  query: Record<string, unknown>,
  key: string,
  value: string | null,
): Record<string, string> {
  const next: Record<string, string> = {};
  for (const [entryKey, entryValue] of Object.entries(query)) {
    if (entryKey === key || typeof entryValue !== "string") {
      continue;
    }
    next[entryKey] = entryValue;
  }
  if (value) {
    next[key] = value;
  }
  return next;
}
