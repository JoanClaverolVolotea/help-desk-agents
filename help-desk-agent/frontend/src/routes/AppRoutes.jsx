import { Navigate, Route, Routes } from "react-router-dom";

import ITAdminCategoriesPage from "../pages/ITAdminCategoriesPage";
import ITAdminTicketsPage from "../pages/ITAdminTicketsPage";
import ITAdminUseCasesPage from "../pages/ITAdminUseCasesPage";
import ITConsoleLayout from "../pages/ITConsoleLayout";
import ITDashboardPage from "../pages/ITDashboardPage";
import RoleLandingPage from "../pages/RoleLandingPage";
import UserPortalPage from "../pages/UserPortalPage";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<RoleLandingPage />} />
      <Route path="/user" element={<UserPortalPage />} />

      <Route path="/it" element={<ITConsoleLayout />}>
        <Route index element={<Navigate to="/it/dashboard" replace />} />
        <Route path="dashboard" element={<ITDashboardPage />} />
        <Route path="admin/categories" element={<ITAdminCategoriesPage />} />
        <Route path="admin/tickets" element={<ITAdminTicketsPage />} />
        <Route path="admin/use-cases" element={<ITAdminUseCasesPage />} />
        <Route path="assistant" element={<Navigate to="/it/dashboard" replace />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
