import axios from "axios";

// In production, use relative URL (same origin). In development, use localhost.
const getApiBaseUrl = () => {
  // If VITE_API_BASE_URL is explicitly set, use it
  if (import.meta.env.VITE_API_BASE_URL) {
    return `${import.meta.env.VITE_API_BASE_URL.replace(/\/$/, "")}/api/`;
  }

  // In production (when served from the same domain), use relative URL
  if (import.meta.env.PROD) {
    return "/api/";
  }

  // In development, default to localhost
  return "http://localhost:8000/api/";
};

const API_BASE_URL = getApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("p2p_access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      const refresh = localStorage.getItem("p2p_refresh_token");
      if (refresh) {
        try {
          const { data } = await axios.post(`${API_BASE_URL}token/refresh/`, {
            refresh,
          });
          localStorage.setItem("p2p_access_token", data.access);
          error.config.headers.Authorization = `Bearer ${data.access}`;
          return api.request(error.config);
        } catch (refreshError) {
          console.error("Refresh token error:", refreshError);
          localStorage.removeItem("p2p_access_token");
          localStorage.removeItem("p2p_refresh_token");
        }
      }
    }
    // Enhanced error handling
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;
      if (status >= 500) {
        error.userMessage = "Server error. Please try again later.";
      } else if (status === 404) {
        error.userMessage = "Resource not found.";
      } else if (status === 403) {
        error.userMessage =
          data.detail || "You don't have permission to perform this action.";
      } else if (status === 400) {
        error.userMessage = data.detail || "Invalid request data.";
      } else {
        error.userMessage = data.detail || "An error occurred.";
      }
    } else if (error.request) {
      // Network error
      error.userMessage = "Network error. Please check your connection.";
    } else {
      // Other error
      error.userMessage = "An unexpected error occurred.";
    }
    return Promise.reject(error);
  }
);

export const AuthAPI = {
  login: (payload) => api.post("token/", payload),
  me: () => api.get("me/"),
};

const buildFormData = (payload) => {
  const formData = new FormData();
  Object.entries(payload).forEach(([key, value]) => {
    if (value === undefined || value === null) return;
    if (key === "items" && Array.isArray(value)) {
      value.forEach((item, i) => {
        Object.entries(item).forEach(([field, val]) => {
          formData.append(`items[${i}][${field}]`, val);
        });
      });
    } else {
      formData.append(key, value);
    }
  });
  return formData;
};

export const RequestAPI = {
  list: (params = {}) =>
    api.get("v1/requests/", {
      params: { page_size: 50, ...params },
    }),
  detail: (id) => api.get(`v1/requests/${id}/`),
  create: (payload) => api.post("v1/requests/", buildFormData(payload)),
  update: (id, payload) =>
    api.put(`v1/requests/${id}/`, buildFormData(payload)),
  approve: (id, data) => api.patch(`v1/requests/${id}/approve/`, data),
  reject: (id, data) => api.patch(`v1/requests/${id}/reject/`, data),
  submitReceipt: (id, file, onProgress) => {
    const formData = new FormData();
    formData.append("receipt", file);
    return api.post(`v1/requests/${id}/submit-receipt/`, formData, {
      onUploadProgress: onProgress,
    });
  },
};

export const NotificationAPI = {
  list: () => api.get("v1/notifications/"),
  markAllRead: () => api.patch("v1/notifications/mark_all_read/"),
  markRead: (id) => api.patch(`v1/notifications/${id}/mark_read/`),
  getUnreadCount: () =>
    api.get("v1/notifications/", { params: { is_read: false } }),
};

// Add error logging for API calls
api.interceptors.request.use((config) => {
  console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

export default api;
