import { Link, Outlet } from "react-router-dom";

import SectionTabs from "../components/SectionTabs.jsx";

const IT_TABS = [
  { to: "/it/admin/categories", label: "Categorias / Categories" },
  { to: "/it/admin/use-cases", label: "Casos de uso / Use cases" },
  { to: "/it/assistant", label: "Tech Assistant" },
];

export default function ITConsoleLayout() {
  return (
    <div className="app-shell it-console-shell">
      <header className="header it-console-header">
        <div>
          <h1>IT Console / Consola IT</h1>
          <p>Operations workspace for category/use-case lifecycle and assistant support.</p>
        </div>
        <Link to="/" className="tab tab-link it-back-link">
          Back to role selection
        </Link>
      </header>

      <SectionTabs items={IT_TABS} className="it-console-tabs" />
      <Outlet />
    </div>
  );
}
