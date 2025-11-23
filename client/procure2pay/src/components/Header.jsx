import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { useNotifications } from "../context/NotificationContext";
import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { Bell, Sun, Moon } from "lucide-react";
import Button from "./Button";

const Header = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { notifications } = useNotifications();
  const [showDropdown, setShowDropdown] = useState(false);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  if (!user) return null;

  return (
    <header className="bg-slate-900 dark:bg-slate-900/95 border-b border-slate-200 dark:border-slate-700/50 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-20">
          <div className="flex flex-col items-start space-y-1">
            <Link
              to="/"
              className="text-xl font-bold text-white hover:text-slate-200"
            >
              Procure2Pay
            </Link>
            <span className="text-xs text-slate-300">
              Logged in as {user.username} ({user.role})
            </span>
          </div>
          <div className="flex items-center space-x-4">
            <button
              onClick={toggleTheme}
              className="p-2 rounded-md bg-slate-800/50 hover:bg-slate-700/50 text-slate-300"
              title="Toggle theme"
            >
              {theme === "dark" ? (
                <Sun className="w-5 h-5" />
              ) : (
                <Moon className="w-5 h-5" />
              )}
            </button>
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              className="p-2 rounded-md bg-slate-800/50 hover:bg-slate-700/50 text-slate-300 relative"
              title="Notifications"
            >
              <Bell className="w-5 h-5" />
              {notifications.length > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                  {notifications.length}
                </span>
              )}
            </button>
            <Button onClick={handleLogout} variant="secondary" size="sm">
              Logout
            </Button>
          </div>
          {showDropdown && (
            <div className="absolute right-4 top-20 w-80 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md shadow-lg z-50">
              <div className="p-4 border-b border-slate-200 dark:border-slate-700">
                <h3 className="font-semibold text-slate-900 dark:text-white">
                  Notifications
                </h3>
              </div>
              <div className="max-h-96 overflow-y-auto">
                {notifications.length > 0 ? (
                  notifications.map((notif) => (
                    <div
                      key={notif.id}
                      className="p-3 border-b border-slate-100 dark:border-slate-700 last:border-b-0"
                    >
                      <p className="text-sm text-slate-900 dark:text-white">
                        {notif.message}
                      </p>
                      {notif.timestamp && (
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                          {new Date(notif.timestamp).toLocaleString()}
                        </p>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="p-4 text-center text-slate-500 dark:text-slate-400">
                    No notifications yet
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
