import AppRoutes from "./routes/AppRoutes";
import LanguageSelector from "./components/LanguageSelector";
import { LanguageProvider } from "./i18n/LanguageContext";

export default function App() {
  return (
    <LanguageProvider>
      <LanguageSelector />
      <AppRoutes />
    </LanguageProvider>
  );
}
