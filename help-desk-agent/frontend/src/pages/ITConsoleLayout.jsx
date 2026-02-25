import { useState } from "react";
import { Link, Outlet } from "react-router-dom";

import ITAssistantPanel from "../components/ITAssistantPanel.jsx";
import SectionTabs from "../components/SectionTabs.jsx";

const IT_TABS = [
  { to: "/it/dashboard", label: "Dashboard" },
  { to: "/it/admin/categories", label: "Categories" },
  { to: "/it/admin/use-cases", label: "Runbooks" },
  { to: "/it/admin/tickets", label: "Tickets" },
];

export default function ITConsoleLayout() {
  const [isAssistantOpen, setIsAssistantOpen] = useState(true);

  return (
    <div className="app-shell it-console-shell">
      <header className="header it-console-header">
        <div>
          <h1>IT Console / Consola IT</h1>
          <p>Operations workspace for managing how issues are categorized, handled, and tracked.</p>
          <div className="it-operating-model">
            <Link to="/it/dashboard">1. Issue received</Link>
            <Link to="/it/admin/categories">2. Categorized</Link>
            <Link to="/it/admin/use-cases">3. Runbook executed</Link>
            <Link to="/it/admin/tickets">4. Ticket recorded</Link>
          </div>
        </div>
        <Link to="/" className="tab tab-link it-back-link">
          Back to role selection
        </Link>
      </header>

      <SectionTabs items={IT_TABS} className="it-console-tabs" />
      <div className={`it-console-workspace ${isAssistantOpen ? "" : "assistant-collapsed"}`.trim()}>
        <main className="it-console-main-pane">
          <Outlet />
        </main>
        <aside id="it-console-assistant-pane" className="it-console-assistant-pane">
          <ITAssistantPanel
            isOpen={isAssistantOpen}
            onToggle={() => setIsAssistantOpen((prev) => !prev)}
          />
        </aside>
      </div>
    </div>
  );
}
