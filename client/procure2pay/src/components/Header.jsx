import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { Link, useNavigate } from "react-router-dom";
import Button from "./Button";

const Header = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  if (!user) return null;

  return (
    <header className="bg-slate-900 dark:bg-slate-900/95 border-b border-slate-200 dark:border-slate-700/50 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-4">
            <Link
              to="/"
              className="text-xl font-bold text-white hover:text-slate-200"
            >
              Procure2Pay
            </Link>
            {user.role === "STAFF" && (
              <Link
                to="/requests/create"
                className="px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700 text-sm font-medium"
              >
                New Request
              </Link>
            )}
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-slate-300 hidden sm:block">
              Logged in as {user.username} ({user.role})
            </span>
            <button
              onClick={toggleTheme}
              className="p-2 rounded-md bg-slate-800/50 hover:bg-slate-700/50 text-slate-300"
              title="Toggle theme"
            >
              {theme === "dark" ? "☀️" : "🌙"}
            </button>
            <Button onClick={handleLogout} variant="secondary" size="sm">
              Logout
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
