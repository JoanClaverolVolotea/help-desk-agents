import { createContext, useCallback, useContext, useMemo, useState } from "react";

import { DEFAULT_LANGUAGE, LANGUAGE_STORAGE_KEY, MESSAGES, SUPPORTED_LANGUAGES } from "./messages.js";

function getMessageValue(dictionary, key) {
  if (!dictionary) {
    return undefined;
  }

  return key.split(".").reduce((acc, part) => {
    if (acc && Object.prototype.hasOwnProperty.call(acc, part)) {
      return acc[part];
    }
    return undefined;
  }, dictionary);
}

function interpolateMessage(template, vars) {
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

function initialLanguage() {
  if (typeof window === "undefined") {
    return DEFAULT_LANGUAGE;
  }

  const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
  if (stored && SUPPORTED_LANGUAGES.includes(stored)) {
    return stored;
  }

  return DEFAULT_LANGUAGE;
}

const LanguageContext = createContext({
  language: DEFAULT_LANGUAGE,
  setLanguage: () => {},
  t: (key) => key,
});

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(initialLanguage);

  const setLanguage = useCallback((nextLanguage) => {
    if (!SUPPORTED_LANGUAGES.includes(nextLanguage)) {
      return;
    }

    setLanguageState(nextLanguage);

    if (typeof window !== "undefined") {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, nextLanguage);
    }
  }, []);

  const t = useCallback(
    (key, vars) => {
      const current = getMessageValue(MESSAGES[language], key);
      const fallback = getMessageValue(MESSAGES[DEFAULT_LANGUAGE], key);
      const resolved = typeof current === "string" ? current : typeof fallback === "string" ? fallback : key;
      return interpolateMessage(resolved, vars);
    },
    [language],
  );

  const value = useMemo(
    () => ({
      language,
      setLanguage,
      t,
    }),
    [language, setLanguage, t],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguageContext() {
  return useContext(LanguageContext);
}
