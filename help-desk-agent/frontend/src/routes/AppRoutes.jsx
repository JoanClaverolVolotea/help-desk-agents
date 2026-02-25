import { Navigate, Route, Routes } from "react-router-dom";

import ITAdminCategoriesPage from "../pages/ITAdminCategoriesPage.jsx";
import ITAdminTicketsPage from "../pages/ITAdminTicketsPage.jsx";
import ITAdminUseCasesPage from "../pages/ITAdminUseCasesPage.jsx";
import ITAssistantPage from "../pages/ITAssistantPage.jsx";
import ITConsoleLayout from "../pages/ITConsoleLayout.jsx";
import RoleLandingPage from "../pages/RoleLandingPage.jsx";
import UserPortalPage from "../pages/UserPortalPage.jsx";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<RoleLandingPage />} />
      <Route path="/user" element={<UserPortalPage />} />

      <Route path="/it" element={<ITConsoleLayout />}>
        <Route index element={<Navigate to="/it/admin/categories" replace />} />
        <Route path="admin/categories" element={<ITAdminCategoriesPage />} />
        <Route path="admin/tickets" element={<ITAdminTicketsPage />} />
        <Route path="admin/use-cases" element={<ITAdminUseCasesPage />} />
        <Route path="assistant" element={<ITAssistantPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
