import { useEffect } from "react";
import type { ReactNode } from "react";

import { useI18n } from "../i18n/useI18n";

interface WizardModalProps {
  title: string;
  step: number;
  totalSteps: number;
  onClose: () => void;
  children: ReactNode;
  navActions: ReactNode;
  submitActions: ReactNode;
  error: string;
}

export default function WizardModal({
  title,
  step,
  totalSteps,
  onClose,
  children,
  navActions,
  submitActions,
  error,
}: WizardModalProps): JSX.Element {
  const { t } = useI18n();

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="wizard-overlay" onClick={onClose}>
      <section className="wizard-shell" onClick={(event) => event.stopPropagation()}>
        <header className="wizard-header">
          <h3>
            {title} - {t("common.step")} {step}/{totalSteps}
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
