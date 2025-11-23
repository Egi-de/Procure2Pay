import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { AuthAPI } from "../services/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const bootstrap = async () => {
    try {
      await AuthAPI.me().then((response) => setUser(response.data));
    } catch (err) {
      setUser(null);
      console.error("Bootstrap error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem("p2p_access_token");
    if (token) {
      bootstrap();
    } else {
      setLoading(false);
    }
  }, []);

  const login = async ({ username, password }) => {
    setError(null);
    try {
      const { data } = await AuthAPI.login({ username, password });
      localStorage.setItem("p2p_access_token", data.access);
      localStorage.setItem("p2p_refresh_token", data.refresh);
      await bootstrap();
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to login");
      throw err;
    }
  };

  const logout = () => {
    localStorage.removeItem("p2p_access_token");
    localStorage.removeItem("p2p_refresh_token");
    setUser(null);
  };

  const value = useMemo(
    () => ({
      user,
      loading,
      error,
      login,
      logout,
      setError,
    }),
    [user, loading, error, login, logout, setError]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

/* eslint-disable-next-line react-refresh/only-export-components */
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};
