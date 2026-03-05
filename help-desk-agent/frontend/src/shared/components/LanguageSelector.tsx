import { useI18n } from "../i18n/useI18n";

export default function LanguageSelector(): JSX.Element {
  const { language, setLanguage, t } = useI18n();

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
    </div>
  );
}
