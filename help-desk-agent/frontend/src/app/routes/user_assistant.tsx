import { Route } from "react-router-dom";

import { UserPortalPage } from "../../features/user_assistant";

export function userAssistantRoute(): JSX.Element {
  return <Route path="/user" element={<UserPortalPage />} />;
}
