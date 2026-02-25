import { NavLink } from "react-router-dom";

export default function SectionTabs({ items, className = "" }) {
  return (
    <nav className={`tab-row section-tabs ${className}`.trim()}>
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) => (isActive ? "tab active tab-link" : "tab tab-link")}
          end={item.end}
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
