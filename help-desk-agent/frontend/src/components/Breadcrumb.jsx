import { Link } from "react-router-dom";

export default function Breadcrumb({ items }) {
  return (
    <nav className="breadcrumb">
      {items.map((item, index) => (
        <span key={item.label}>
          {index > 0 ? <span className="breadcrumb-sep">/</span> : null}
          {item.to ? (
            <Link to={item.to} className="breadcrumb-link">
              {item.label}
            </Link>
          ) : (
            <span className="breadcrumb-current">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
