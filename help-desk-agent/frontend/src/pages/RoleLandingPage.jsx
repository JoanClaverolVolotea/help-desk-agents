import { Link } from "react-router-dom";

import { useI18n } from "../i18n/useI18n.js";

export default function RoleLandingPage() {
  const { t } = useI18n();

  return (
    <div className="app-shell role-landing-shell">
      <section className="role-landing-hero">
        <div className="role-landing-icon">?</div>
        <h1>{t("roleLanding.title")}</h1>
        <p>
          {t("roleLanding.subtitle")}
        </p>
      </section>

      <section className="role-landing-grid">
        <Link to="/user" className="role-card user-portal-card">
          <span className="role-card-icon">💬</span>
          <h2>{t("roleLanding.userPortalTitle")}</h2>
          <p>
            {t("roleLanding.userPortalDescription")}
          </p>
          <span className="role-card-cta">{t("roleLanding.userPortalCta")} →</span>
        </Link>

        <Link to="/it" className="role-card it-console-card">
          <span className="role-card-icon">⚙️</span>
          <h2>{t("roleLanding.itConsoleTitle")}</h2>
          <p>
            {t("roleLanding.itConsoleDescription")}
          </p>
          <span className="role-card-cta">{t("roleLanding.itConsoleCta")} →</span>
        </Link>
      </section>
    </div>
  );
}
