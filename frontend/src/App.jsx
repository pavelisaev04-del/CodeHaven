import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import HomePage from "./pages/Home";
import TemplatesPage from "./pages/Templates";
import ConsultationPage from "./pages/Consultation";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
          <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
            <NavLink to="/" className="font-bold text-xl text-blue-700">
              ЮрСервис
            </NavLink>
            <nav className="flex gap-6 text-sm font-medium">
              <NavLink
                to="/"
                className={({ isActive }) =>
                  isActive ? "text-blue-700" : "text-gray-600 hover:text-gray-900"
                }
              >
                Главная
              </NavLink>
              <NavLink
                to="/templates"
                className={({ isActive }) =>
                  isActive ? "text-blue-700" : "text-gray-600 hover:text-gray-900"
                }
              >
                Шаблоны
              </NavLink>
              <NavLink
                to="/consultation"
                className={({ isActive }) =>
                  isActive ? "text-blue-700" : "text-gray-600 hover:text-gray-900"
                }
              >
                Консультация
              </NavLink>
            </nav>
          </div>
        </header>

        <main className="max-w-5xl mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/templates" element={<TemplatesPage />} />
            <Route path="/consultation" element={<ConsultationPage />} />
          </Routes>
        </main>

        <footer className="text-center text-xs text-gray-400 py-8">
          © 2026 ЮрСервис · Все права защищены
        </footer>
      </div>
    </BrowserRouter>
  );
}
