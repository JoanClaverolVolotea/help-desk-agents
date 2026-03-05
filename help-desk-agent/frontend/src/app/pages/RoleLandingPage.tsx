import { Link } from "react-router-dom";

import { useI18n } from "../../shared/i18n/useI18n";

export default function RoleLandingPage(): JSX.Element {
  const { t } = useI18n();

  return (
    <div className="app-shell role-landing-shell">
      <section className="role-landing-hero">
        <img src="/company-logo.webp" alt="Company logo" className="role-landing-logo" />
        <div className="role-landing-icon">✈</div>
        <h1>{t("roleLanding.title")}</h1>
        <p>{t("roleLanding.subtitle")}</p>
      </section>

      <section className="role-landing-grid">
        <Link to="/user" className="role-card user-portal-card">
          <span className="role-card-icon">💬</span>
          <h2>{t("roleLanding.userPortalTitle")}</h2>
          <p>{t("roleLanding.userPortalDescription")}</p>
          <span className="role-card-cta">{t("roleLanding.userPortalCta")} -&gt;</span>
        </Link>

        <Link to="/it" className="role-card it-console-card">
          <span className="role-card-icon">⚙️</span>
          <h2>{t("roleLanding.itConsoleTitle")}</h2>
          <p>{t("roleLanding.itConsoleDescription")}</p>
          <span className="role-card-cta">{t("roleLanding.itConsoleCta")} -&gt;</span>
        </Link>
      </section>
    </div>
  );
}
