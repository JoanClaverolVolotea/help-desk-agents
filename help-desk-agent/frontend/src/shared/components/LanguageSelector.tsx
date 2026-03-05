import { useEffect, useState } from "react";

import { useI18n } from "../i18n/useI18n";

export default function LanguageSelector(): JSX.Element {
  const { language, setLanguage, t } = useI18n();
  const [themeMode, setThemeMode] = useState<"brand" | "lite">(() => {
    if (typeof window === "undefined") {
      return "brand";
    }
    return window.localStorage.getItem("helpdesk-theme") === "lite" ? "lite" : "brand";
  });

  useEffect(() => {
    document.body.classList.toggle("theme-lite", themeMode === "lite");
    window.localStorage.setItem("helpdesk-theme", themeMode);
  }, [themeMode]);

  return (
    <div className="language-selector-shell" aria-label={t("language.selectorLabel")}>
      <button
        type="button"
        className={`language-button ${language === "en" ? "active" : ""}`}
        onClick={() => setLanguage("en")}
        aria-pressed={language === "en"}
        title={t("language.english")}
      >
        {t("language.shortEnglish")}
      </button>
      <button
        type="button"
        className={`language-button ${language === "es" ? "active" : ""}`}
        onClick={() => setLanguage("es")}
        aria-pressed={language === "es"}
        title={t("language.spanish")}
      >
        {t("language.shortSpanish")}
      </button>
      <span className="theme-toggle-divider" aria-hidden="true" />
      <button
        type="button"
        className={`language-button theme-button ${themeMode === "brand" ? "active" : ""}`}
        onClick={() => setThemeMode("brand")}
        aria-pressed={themeMode === "brand"}
        title={t("language.themeLabel")}
      >
        {t("language.themeBrand")}
      </button>
      <button
        type="button"
        className={`language-button theme-button ${themeMode === "lite" ? "active" : ""}`}
        onClick={() => setThemeMode("lite")}
        aria-pressed={themeMode === "lite"}
        title={t("language.themeLabel")}
      >
        {t("language.themeLite")}
      </button>
    </div>
  );
}
