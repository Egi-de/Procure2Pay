/* eslint-disable react-refresh/only-export-components */
import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { RequestAPI } from "../services/api"; // Assuming notifications come via API, or extend for notifications
import { useAuth } from "./AuthContext";
import Toast from "../components/Toast";

const NotificationContext = createContext();

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error(
      "useNotifications must be used within NotificationProvider"
    );
  }
  return context;
};

export const NotificationProvider = ({ children }) => {
  const [notifications, setNotifications] = useState([]);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState("");
  const [toastType, setToastType] = useState("info");

  const { user, loading } = useAuth();

  const fetchNotifications = useCallback(async () => {
    try {
      const response = await NotificationAPI.list();
      setNotifications(response.data);
      if (response.data.length > 0) {
        setToastMessage("New notifications available!");
        setToastType("info");
        setShowToast(true);
      }
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
      setNotifications([]);
    }
  }, []);

  // Clear notifications when user is not authenticated
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (!user) {
      setNotifications([]);
    }
  }, [user]);
  /* eslint-enable react-hooks/set-state-in-effect */

  // Fetch and poll notifications when authenticated
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (loading || !user) return;

    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000); // Poll every 30 seconds
    return () => clearInterval(interval);
  }, [user, loading, fetchNotifications]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const addNotification = (message, type = "info") => {
    setToastMessage(message);
    setToastType(type);
    setShowToast(true);
  };

  const closeToast = () => {
    setShowToast(false);
  };

  return (
    <NotificationContext.Provider value={{ notifications, addNotification }}>
      {children}
      {showToast && (
        <Toast
          message={toastMessage}
          type={toastType}
          onClose={closeToast}
          duration={5000}
        />
      )}
    </NotificationContext.Provider>
  );
};
