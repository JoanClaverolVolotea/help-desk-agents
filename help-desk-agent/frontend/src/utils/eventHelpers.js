export const INTERNAL_EVENT_KINDS = new Set(["tool_call", "tool_output", "handoff", "info"]);

export function normalizeEntryKind(value) {
  if (typeof value !== "string" || value.trim() === "") {
    return "info";
  }
  return value;
}

export function normalizeEntryText(value) {
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

export function isInternalEntryKind(kind) {
  return INTERNAL_EVENT_KINDS.has(normalizeEntryKind(kind));
}
