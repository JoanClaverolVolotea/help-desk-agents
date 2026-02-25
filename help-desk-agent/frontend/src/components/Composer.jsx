export default function Composer({
  value,
  onChange,
  onSubmit,
  onReset,
  placeholder,
  disabled,
  submitLabel,
  sendingLabel,
  resetLabel,
  rows = 4,
  className = "",
}) {
  const onKeyDown = (event) => {
    if (event.key === "Enter" && event.ctrlKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  };

  return (
    <form className={`composer ${className}`.trim()} onSubmit={onSubmit}>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        rows={rows}
        disabled={disabled}
      />
      <div className="composer-actions">
        {onReset ? (
          <button type="button" className="ghost" onClick={onReset} disabled={disabled}>
            {resetLabel}
          </button>
        ) : null}
        <button type="submit" className="primary" disabled={disabled}>
          {disabled ? sendingLabel : submitLabel}
        </button>
      </div>
    </form>
  );
}
