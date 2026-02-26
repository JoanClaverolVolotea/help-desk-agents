import { useLanguageContext } from "./LanguageContext";

export function useI18n() {
  return useLanguageContext();
}
