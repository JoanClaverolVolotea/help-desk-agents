import type { FormEvent, KeyboardEvent } from "react";

interface ComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
  onReset?: () => void | Promise<void>;
  placeholder: string;
  disabled: boolean;
  submitLabel: string;
  sendingLabel: string;
  resetLabel?: string;
  rows?: number;
  className?: string;
}

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
}: ComposerProps): JSX.Element {
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
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
