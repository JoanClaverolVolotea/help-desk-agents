import { Navigate, Route } from "react-router-dom";

import {
  ITAdminCategoriesPage,
  ITAdminTicketsPage,
  ITAdminUseCasesPage,
  ITConsoleLayout,
  ITDashboardPage,
} from "../../features/admin_assistant";

export function adminAssistantRoute(): JSX.Element {
  return (
    <Route path="/it" element={<ITConsoleLayout />}>
      <Route index element={<Navigate to="/it/dashboard" replace />} />
      <Route path="dashboard" element={<ITDashboardPage />} />
      <Route path="admin/categories" element={<ITAdminCategoriesPage />} />
      <Route path="admin/tickets" element={<ITAdminTicketsPage />} />
      <Route path="admin/use-cases" element={<ITAdminUseCasesPage />} />
      <Route path="assistant" element={<Navigate to="/it/dashboard" replace />} />
    </Route>
  );
}
