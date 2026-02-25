import { Link } from "react-router-dom";

export default function RoleLandingPage() {
  return (
    <div className="app-shell role-landing-shell">
      <section className="role-landing-hero">
        <div className="role-landing-icon">?</div>
        <h1>Help Desk Agent</h1>
        <p>
          AI-powered IT support — choose your workspace to get started.
        </p>
        <p className="role-landing-subtitle">
          Soporte IT impulsado por IA — elige tu espacio de trabajo.
        </p>
      </section>

      <section className="role-landing-grid">
        <Link to="/user" className="role-card user-portal-card">
          <span className="role-card-icon">💬</span>
          <h2>User Portal</h2>
          <p className="role-card-es">Portal Usuario</p>
          <p>
            Describe your issue in a conversation and get help right away.
          </p>
          <span className="role-card-cta">Go to User Portal →</span>
        </Link>

        <Link to="/it" className="role-card it-console-card">
          <span className="role-card-icon">⚙️</span>
          <h2>IT Console</h2>
          <p className="role-card-es">Consola IT</p>
          <p>
            Manage how issues are categorized, handled, and tracked.
          </p>
          <span className="role-card-cta">Open IT Console →</span>
        </Link>
      </section>
    </div>
  );
}
