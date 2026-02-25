import AppRoutes from "./routes/AppRoutes.jsx";
import LanguageSelector from "./components/LanguageSelector.jsx";
import { LanguageProvider } from "./i18n/LanguageContext.jsx";

export default function App() {
  return (
    <LanguageProvider>
      <LanguageSelector />
      <AppRoutes />
    </LanguageProvider>
  );
}
