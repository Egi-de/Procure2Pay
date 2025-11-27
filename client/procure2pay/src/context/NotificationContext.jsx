/* eslint-disable react-refresh/only-export-components */
import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
} from "react";
import { NotificationAPI } from "../services/api";
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

// Get WebSocket URL based on environment
const getWebSocketUrl = () => {
  const token = localStorage.getItem("p2p_access_token");
  if (!token) return null;

  // In production, use same host with wss
  if (import.meta.env.PROD) {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}/ws/notifications/?token=${token}`;
  }

  // In development, use localhost
  return `ws://localhost:8000/ws/notifications/?token=${token}`;
};

export const NotificationProvider = ({ children }) => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState("");
  const [toastType, setToastType] = useState("info");
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const connectWebSocketRef = useRef(null);
  const prevUserRef = useRef(null);
  const maxReconnectAttempts = 5;

  const { user, loading } = useAuth();

  const fetchNotifications = useCallback(async () => {
    try {
      const response = await NotificationAPI.list();
      const notificationData = response.data.results || response.data;
      setNotifications(notificationData);
      setUnreadCount(notificationData.filter((n) => !n.is_read).length);
    } catch (error) {
      console.error("Failed to fetch notifications:", error);
      setNotifications([]);
    }
  }, []);

  // Connect to WebSocket
  const connectWebSocket = useCallback(() => {
    const wsUrl = getWebSocketUrl();
    if (!wsUrl || !user) return;

    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log("WebSocket connected for notifications");
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "notification") {
            const notification = data.notification;

            // Add to notifications list
            setNotifications((prev) => [notification, ...prev]);
            setUnreadCount((prev) => prev + 1);

            // Show toast for new notification
            setToastMessage(notification.message);
            setToastType("info");
            setShowToast(true);
          } else if (data.type === "pong") {
            // Heartbeat response
            console.log("WebSocket heartbeat received");
          }
        } catch (error) {
          console.error("Error parsing WebSocket message:", error);
        }
      };

      ws.onclose = (event) => {
        console.log("WebSocket disconnected:", event.code, event.reason);
        wsRef.current = null;

        // Attempt to reconnect if not a normal closure and user is still logged in
        if (
          event.code !== 1000 &&
          user &&
          reconnectAttemptsRef.current < maxReconnectAttempts
        ) {
          const delay = Math.min(
            1000 * Math.pow(2, reconnectAttemptsRef.current),
            30000
          );
          console.log(`Attempting to reconnect in ${delay}ms...`);
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connectWebSocketRef.current?.();
          }, delay);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };

      wsRef.current = ws;

      // Set up heartbeat to keep connection alive
      const heartbeatInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 30000);

      // Clean up heartbeat on close
      ws.addEventListener("close", () => {
        clearInterval(heartbeatInterval);
      });
    } catch (error) {
      console.error("Failed to create WebSocket connection:", error);
    }
  }, [user]);

  // Update ref when connectWebSocket changes
  useEffect(() => {
    connectWebSocketRef.current = connectWebSocket;
  }, [connectWebSocket]);

  // Disconnect WebSocket
  const disconnectWebSocket = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close(1000, "User logged out");
      wsRef.current = null;
    }
  }, []);

  // Clear notifications when user logs out (transitions from authenticated to unauthenticated)
  useEffect(() => {
    const prevUser = prevUserRef.current;
    prevUserRef.current = user;

    // Only clear state when transitioning from logged in to logged out
    if (prevUser && !user) {
      setNotifications([]);
      setUnreadCount(0);
      disconnectWebSocket();
    }
  }, [user, disconnectWebSocket]);

  // Fetch notifications and connect WebSocket when authenticated
  useEffect(() => {
    if (loading || !user) return;

    fetchNotifications();
    connectWebSocketRef.current?.();

    // Fallback polling every 60 seconds in case WebSocket fails
    const interval = setInterval(fetchNotifications, 60000);

    return () => {
      clearInterval(interval);
      disconnectWebSocket();
    };
  }, [user, loading, fetchNotifications, disconnectWebSocket]);

  const addNotification = (message, type = "info") => {
    setToastMessage(message);
    setToastType(type);
    setShowToast(true);
  };

  const markAsRead = useCallback(
    async (notificationId) => {
      try {
        // Update local state immediately for responsiveness
        setNotifications((prev) =>
          prev.map((n) =>
            n.id === notificationId ? { ...n, is_read: true } : n
          )
        );
        setUnreadCount((prev) => Math.max(0, prev - 1));

        // Send via WebSocket if connected
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(
            JSON.stringify({
              type: "mark_read",
              notification_id: notificationId,
            })
          );
        } else {
          // Fallback to API call
          await NotificationAPI.markRead(notificationId);
        }
      } catch (error) {
        console.error("Failed to mark notification as read:", error);
        // Revert local state on error
        fetchNotifications();
      }
    },
    [fetchNotifications]
  );

  const markAllAsRead = useCallback(async () => {
    try {
      await NotificationAPI.markAllRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (error) {
      console.error("Failed to mark all notifications as read:", error);
    }
  }, []);

  const closeToast = () => {
    setShowToast(false);
  };

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        addNotification,
        markAsRead,
        markAllAsRead,
        refreshNotifications: fetchNotifications,
      }}
    >
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
