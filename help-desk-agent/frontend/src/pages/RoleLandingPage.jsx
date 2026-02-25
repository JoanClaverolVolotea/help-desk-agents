import { Link } from "react-router-dom";

export default function RoleLandingPage() {
  return (
    <div className="app-shell role-landing-shell">
      <header className="header role-landing-header">
        <h1>Help Desk Agent</h1>
        <p>
          Choose your workspace. Elige tu espacio de trabajo.
        </p>
      </header>

      <section className="role-landing-grid">
        <Link to="/user" className="role-card user-portal-card">
          <h2>User Portal / Portal Usuario</h2>
          <p>
            Open a ticket quickly with a guided form and get help in one conversation.
            Abre un ticket rapido con un formulario guiado.
          </p>
          <span className="role-card-cta">Go to User Portal</span>
        </Link>

        <Link to="/it/admin/categories" className="role-card it-console-card">
          <h2>IT Console / Consola IT</h2>
          <p>
            Manage categories, use-cases, and the technical assistant for operational workflows.
            Gestiona operaciones del help desk.
          </p>
          <span className="role-card-cta">Open IT Console</span>
        </Link>
      </section>
    </div>
  );
}
