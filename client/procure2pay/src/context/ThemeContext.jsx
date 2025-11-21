import { createContext, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "p2p_theme";

const ThemeContext = createContext({
  theme: "light",
  toggleTheme: () => {},
  setTheme: () => {},
});

const getPreferredTheme = () => {
  if (typeof window === "undefined") return "light";
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") {
    return stored;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
};

export const ThemeProvider = ({ children }) => {
  const [theme, setThemeState] = useState(getPreferredTheme);

  useEffect(() => {
    const root = document.documentElement;
    const mode = theme === "dark" ? "dark" : "light";
    root.classList.toggle("dark", mode === "dark");
    root.style.colorScheme = mode;
    localStorage.setItem(STORAGE_KEY, mode);
  }, [theme]);

  const setTheme = (mode) => {
    setThemeState(mode === "dark" ? "dark" : "light");
  };

  const toggleTheme = () => {
    setThemeState((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const value = useMemo(
    () => ({
      theme,
      setTheme,
      toggleTheme,
    }),
    [theme]
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
};
