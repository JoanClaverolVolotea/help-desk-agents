import { useEffect } from "react";

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
            {title} — Step {step}/{totalSteps}
          </h3>
          <button type="button" className="ghost" onClick={onClose}>
            Close
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
