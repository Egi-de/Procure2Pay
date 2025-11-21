import axios from "axios";

const API_HOST = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const API_BASE_URL = `${API_HOST.replace(/\/$/, "")}/api/`;

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
          localStorage.removeItem("p2p_access_token");
          localStorage.removeItem("p2p_refresh_token");
        }
      }
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
    if (key === "items") {
      formData.append("items", JSON.stringify(value));
    } else {
      formData.append(key, value);
    }
  });
  return formData;
};

export const RequestAPI = {
  list: (params = {}) =>
    api.get("requests/", {
      params: { page_size: 50, ...params },
    }),
  detail: (id) => api.get(`requests/${id}/`),
  create: (payload) => api.post("requests/", buildFormData(payload)),
  update: (id, payload) =>
    api.put(`requests/${id}/`, buildFormData(payload)),
  approve: (id, data) => api.patch(`requests/${id}/approve/`, data),
  reject: (id, data) => api.patch(`requests/${id}/reject/`, data),
  submitReceipt: (id, file) => {
    const formData = new FormData();
    formData.append("receipt", file);
    return api.post(`requests/${id}/submit-receipt/`, formData);
  },
};

export default api;

