/* eslint-disable react-refresh/only-export-components */
import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { RequestAPI } from "../services/api"; // Assuming notifications come via API, or extend for notifications
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

  const fetchNotifications = useCallback(async () => {
    try {
      // Assuming an API endpoint for notifications; adjust as needed
      // For now, simulate or use existing API; in real, add /api/notifications/
      const response = await RequestAPI.list({ only_notifications: true }); // Placeholder
      setNotifications(response.data.results || []);
      if (response.data.new_notifications) {
        setToastMessage("New notifications available!");
        setToastType("info");
        setShowToast(true);
      }
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
      setToastMessage("Failed to load notifications");
      setToastType("error");
      setShowToast(true);
    }
  }, []);

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 30000); // Poll every 30 seconds
    return () => clearInterval(interval);
  }, [fetchNotifications]);
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
