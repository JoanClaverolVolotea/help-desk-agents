import { Navigate, Route, Routes } from "react-router-dom";

import RoleLandingPage from "../pages/RoleLandingPage";
import { adminAssistantRoute } from "./admin_assistant";
import { userAssistantRoute } from "./user_assistant";

export default function AppRoutes(): JSX.Element {
  return (
    <Routes>
      <Route path="/" element={<RoleLandingPage />} />
      {userAssistantRoute()}
      {adminAssistantRoute()}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
