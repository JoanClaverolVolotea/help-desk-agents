import type { LanguageCode } from "../types";

const LANGUAGE_HINTS: Record<LanguageCode, string> = {
  en: "Respond only in English.",
  es: "Responde solo en español.",
};

export function withLanguageHint(message: unknown, language: LanguageCode): string {
  const normalizedMessage = typeof message === "string" ? message.trim() : "";
  if (!normalizedMessage) {
    return "";
  }

  const hint = LANGUAGE_HINTS[language] ?? LANGUAGE_HINTS.en;
  return `[LANGUAGE_HINT: ${hint}]\n\n${normalizedMessage}`;
}
