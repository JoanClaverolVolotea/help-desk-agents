export default function StatusRow({ items, className = "" }) {
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
