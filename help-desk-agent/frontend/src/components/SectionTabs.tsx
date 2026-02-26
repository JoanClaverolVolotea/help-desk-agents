import { NavLink } from "react-router-dom";
import type { To } from "react-router-dom";

interface SectionTabItem {
  to: To;
  label: string;
  end?: boolean;
}

interface SectionTabsProps {
  items: SectionTabItem[];
  className?: string;
}

export default function SectionTabs({ items, className = "" }: SectionTabsProps): JSX.Element {
  return (
    <nav className={`tab-row section-tabs ${className}`.trim()}>
      {items.map((item) => (
        <NavLink
          key={String(item.to)}
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
