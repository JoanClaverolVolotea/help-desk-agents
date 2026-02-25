import { useLanguageContext } from "./LanguageContext.jsx";

export function useI18n() {
  return useLanguageContext();
}
