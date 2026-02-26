import type { ReactNode } from "react";

interface StatusItem {
  label: string;
  value: ReactNode;
}

interface StatusRowProps {
  items: StatusItem[];
  className?: string;
}

export default function StatusRow({ items, className = "" }: StatusRowProps): JSX.Element {
  return (
    <section className={`status-row ${className}`.trim()}>
      {items.map((item) => (
        <div key={item.label}>
          <span className="label">{item.label}</span>
          <strong>{item.value}</strong>
        </div>
      ))}
    </section>
  );
}
