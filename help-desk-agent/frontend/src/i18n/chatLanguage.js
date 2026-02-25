const LANGUAGE_HINTS = {
  en: "Respond only in English.",
  es: "Responde solo en español.",
};

export function withLanguageHint(message, language) {
  const normalizedMessage = typeof message === "string" ? message.trim() : "";
  if (!normalizedMessage) {
    return "";
  }

  const hint = LANGUAGE_HINTS[language] ?? LANGUAGE_HINTS.en;
  return `[LANGUAGE_HINT: ${hint}]\n\n${normalizedMessage}`;
}
