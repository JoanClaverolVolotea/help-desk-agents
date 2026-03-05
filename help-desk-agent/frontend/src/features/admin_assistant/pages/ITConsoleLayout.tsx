import { useState } from "react";
import { Link, Outlet } from "react-router-dom";

import ITAssistantPanel from "../components/ITAssistantPanel";
import SectionTabs from "../components/SectionTabs";
import { useI18n } from "../../../shared/i18n/useI18n";

export default function ITConsoleLayout(): JSX.Element {
  const { t } = useI18n();
  const [isAssistantOpen, setIsAssistantOpen] = useState(true);
  const itTabs = [
    { to: "/it/dashboard", label: t("itConsole.tabDashboard") },
    { to: "/it/admin/categories", label: t("itConsole.tabCategories") },
    { to: "/it/admin/use-cases", label: t("itConsole.tabRunbooks") },
    { to: "/it/admin/tickets", label: t("itConsole.tabTickets") },
  ];

  return (
    <div className="app-shell it-console-shell">
      <header className="header it-console-header">
        <div>
          <div className="header-brand">
            <img src="/company-logo.webp" alt="Company logo" className="header-logo" />
            <h1>{t("itConsole.title")}</h1>
          </div>
          <p>{t("itConsole.description")}</p>
          <div className="it-operating-model">
            <Link to="/it/dashboard">{t("itConsole.modelStep1")}</Link>
            <Link to="/it/admin/categories">{t("itConsole.modelStep2")}</Link>
            <Link to="/it/admin/use-cases">{t("itConsole.modelStep3")}</Link>
            <Link to="/it/admin/tickets">{t("itConsole.modelStep4")}</Link>
          </div>
        </div>
        <Link to="/" className="tab tab-link it-back-link">
          {t("common.backToRoleSelection")}
        </Link>
      </header>

      <SectionTabs items={itTabs} className="it-console-tabs" />
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
