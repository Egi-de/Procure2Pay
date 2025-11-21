import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import ProtectedRoute from "../components/ProtectedRoute.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { useTheme } from "../context/ThemeContext.jsx";
import { Moon, Sun } from "lucide-react";
import CreateRequest from "../pages/CreateRequest.jsx";
import Dashboard from "../pages/Dashboard.jsx";
import DetailView from "../pages/DetailView.jsx";
import Login from "../pages/Login.jsx";
import ReceiptUpload from "../pages/ReceiptUpload.jsx";
import Unauthorized from "../pages/Unauthorized.jsx";

const AppShell = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex flex-col transition-colors">
      <header className="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Logged in as
            </p>
            <p className="font-semibold text-slate-900 dark:text-white">
              {user?.first_name || user?.username} · {user?.role}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={toggleTheme}
              className="px-3 py-2 rounded-md border border-slate-200 dark:border-slate-600 text-sm text-slate-600 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-2"
            >
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <button
              onClick={logout}
              className="px-4 py-2 rounded-md bg-slate-900 text-white hover:bg-slate-700 dark:bg-slate-700 dark:hover:bg-slate-600"
            >
              Logout
            </button>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
};

const AppRoutes = () => (
  <Routes>
    <Route path="/login" element={<Login />} />
    <Route path="/unauthorized" element={<Unauthorized />} />
    <Route
      element={
        <ProtectedRoute>
          <AppShell />
        </ProtectedRoute>
      }
    >
      <Route index element={<Dashboard />} />
      <Route
        path="requests/create"
        element={
          <ProtectedRoute roles={["STAFF"]}>
            <CreateRequest />
          </ProtectedRoute>
        }
      />
      <Route path="requests/:id" element={<DetailView />} />
      <Route
        path="requests/:id/receipt"
        element={
          <ProtectedRoute roles={["STAFF"]}>
            <ReceiptUpload />
          </ProtectedRoute>
        }
      />
    </Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
);

export default AppRoutes;
