import { useEffect } from "react";

import { useI18n } from "../i18n/useI18n.js";

export default function WizardModal({
  title,
  step,
  totalSteps,
  onClose,
  children,
  navActions,
  submitActions,
  error,
}) {
  const { t } = useI18n();

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="wizard-overlay" onClick={onClose}>
      <section className="wizard-shell" onClick={(e) => e.stopPropagation()}>
        <header className="wizard-header">
          <h3>
            {title} — {t("common.step")} {step}/{totalSteps}
          </h3>
          <button type="button" className="ghost" onClick={onClose}>
            {t("common.close")}
          </button>
        </header>

        <div className="wizard-body">{children}</div>

        {error ? <p className="error-text wizard-error">{error}</p> : null}

        <footer className="wizard-footer">
          <div className="wizard-nav">{navActions}</div>
          <div className="wizard-submit">{submitActions}</div>
        </footer>
      </section>
    </div>
  );
}
