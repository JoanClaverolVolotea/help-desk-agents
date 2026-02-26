import type { LanguageCode } from "../../types";

import { ADMIN_ASSISTANT_MESSAGES } from "./admin_assistant";
import { COMMON_MESSAGES } from "./common";
import { USER_ASSISTANT_MESSAGES } from "./user_assistant";

export const DEFAULT_LANGUAGE: LanguageCode = "en";
export const LANGUAGE_STORAGE_KEY = "helpdesk_ui_lang";
export const SUPPORTED_LANGUAGES: LanguageCode[] = ["en", "es"];

export const MESSAGES: Record<LanguageCode, Record<string, unknown>> = {
  en: {
    ...COMMON_MESSAGES.en,
    ...USER_ASSISTANT_MESSAGES.en,
    ...ADMIN_ASSISTANT_MESSAGES.en,
  },
  es: {
    ...COMMON_MESSAGES.es,
    ...USER_ASSISTANT_MESSAGES.es,
    ...ADMIN_ASSISTANT_MESSAGES.es,
  },
};
