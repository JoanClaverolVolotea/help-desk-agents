export type LanguageCode = "en" | "es";

export type MessageVariables = Record<string, string | number>;

export type TranslateFunction = (key: string, vars?: MessageVariables) => string;

export interface I18nContextValue {
  language: LanguageCode;
  setLanguage: (nextLanguage: LanguageCode) => void;
  t: TranslateFunction;
}
