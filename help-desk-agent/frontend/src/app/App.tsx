import AppRoutes from "./routes";
import LanguageSelector from "../shared/components/LanguageSelector";
import { LanguageProvider } from "../shared/i18n/LanguageContext";

export default function App(): JSX.Element {
  return (
    <LanguageProvider>
      <LanguageSelector />
      <AppRoutes />
    </LanguageProvider>
  );
}
