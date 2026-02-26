import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { DEFAULT_LANGUAGE, LANGUAGE_STORAGE_KEY, MESSAGES, SUPPORTED_LANGUAGES } from "./messages";
import type { I18nContextValue, LanguageCode, MessageVariables } from "../types";

type MessageDictionary = Record<string, unknown>;

function getMessageValue(dictionary: MessageDictionary | undefined, key: string): unknown {
  if (!dictionary) {
    return undefined;
  }

  return key.split(".").reduce<unknown>((acc, part) => {
    if (
      typeof acc === "object" &&
      acc !== null &&
      Object.prototype.hasOwnProperty.call(acc, part)
    ) {
      return (acc as MessageDictionary)[part];
    }
    return undefined;
  }, dictionary);
}

function interpolateMessage(template: string, vars?: MessageVariables): string {
  if (!vars) {
    return template;
  }

  return template.replace(/\{(\w+)\}/g, (fullMatch, token) => {
    if (Object.prototype.hasOwnProperty.call(vars, token)) {
      return String(vars[token]);
    }
    return fullMatch;
  });
}

function initialLanguage(): LanguageCode {
  if (typeof window === "undefined") {
    return DEFAULT_LANGUAGE;
  }

  const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (stored && SUPPORTED_LANGUAGES.includes(stored as LanguageCode)) {
    return stored as LanguageCode;
  }

  return DEFAULT_LANGUAGE;
}

const LanguageContext = createContext<I18nContextValue>({
  language: DEFAULT_LANGUAGE,
  setLanguage: () => {},
  t: (key) => key,
});

interface LanguageProviderProps {
  children: ReactNode;
}

export function LanguageProvider({ children }: LanguageProviderProps): JSX.Element {
  const [language, setLanguageState] = useState<LanguageCode>(initialLanguage);

  const setLanguage = useCallback((nextLanguage: LanguageCode) => {
    if (!SUPPORTED_LANGUAGES.includes(nextLanguage)) {
      return;
    }

    setLanguageState(nextLanguage);

    if (typeof window !== "undefined") {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLanguage);
    }
  }, []);

  const t = useCallback(
    (key: string, vars?: MessageVariables) => {
      const current = getMessageValue(MESSAGES[language], key);
      const fallback = getMessageValue(MESSAGES[DEFAULT_LANGUAGE], key);
      const resolved = typeof current === "string" ? current : typeof fallback === "string" ? fallback : key;
      return interpolateMessage(resolved, vars);
    },
    [language],
  );

  const value = useMemo<I18nContextValue>(
    () => ({
      language,
      setLanguage,
      t,
    }),
    [language, setLanguage, t],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguageContext(): I18nContextValue {
  return useContext(LanguageContext);
}
