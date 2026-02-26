const INTERNAL_EVENT_KIND_VALUES = ["tool_call", "tool_output", "handoff", "info"] as const;

export const INTERNAL_EVENT_KINDS: ReadonlySet<string> = new Set(INTERNAL_EVENT_KIND_VALUES);

export function normalizeEntryKind(value: unknown): string {
  if (typeof value !== "string" || value.trim() === "") {
    return "info";
  }
  return value;
}

export function normalizeEntryText(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  if (value === null || value === undefined) {
    return "";
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function isInternalEntryKind(kind: unknown): boolean {
  return INTERNAL_EVENT_KINDS.has(normalizeEntryKind(kind));
}
