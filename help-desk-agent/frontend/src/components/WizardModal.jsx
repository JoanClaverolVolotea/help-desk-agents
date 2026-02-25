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
  return (
    <section className="wizard-shell">
      <header className="wizard-header">
        <h3>
          {title} - Paso {step}/{totalSteps}
        </h3>
        <button type="button" className="ghost" onClick={onClose}>
          Cerrar
        </button>
      </header>

      <div className="wizard-body">{children}</div>

      <footer className="wizard-footer">
        <div className="wizard-nav">{navActions}</div>
        <div className="wizard-submit">{submitActions}</div>
      </footer>

      {error ? <p className="error-text wizard-error">{error}</p> : null}
    </section>
  );
}
