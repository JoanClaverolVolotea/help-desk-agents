import { Link, Outlet } from "react-router-dom";

import SectionTabs from "../components/SectionTabs.jsx";

const IT_TABS = [
  { to: "/it/admin/categories", label: "Routing Policies / Categorias" },
  { to: "/it/admin/tickets", label: "Tickets Registry" },
  { to: "/it/admin/use-cases", label: "Runbooks / Casos de uso" },
  { to: "/it/assistant", label: "Tech Assistant" },
];

export default function ITConsoleLayout() {
  return (
    <div className="app-shell it-console-shell">
      <header className="header it-console-header">
        <div>
          <h1>IT Console / Consola IT</h1>
          <p>Operations workspace for policy-driven routing and deterministic runbook execution.</p>
          <div className="it-operating-model">
            <span>1. Ticket intake</span>
            <span>2. Routing policy (category)</span>
            <span>3. Runbook (use case)</span>
            <span>4. Deterministic execution + registry</span>
          </div>
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
