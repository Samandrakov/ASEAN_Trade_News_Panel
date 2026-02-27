import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
  timeout: 30000,
});

// Request interceptor: attach JWT token
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("asean_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let _isRefreshing = false;
let _pendingQueue: Array<{ resolve: (token: string) => void; reject: (e: unknown) => void }> = [];

function _processQueue(error: unknown, token: string | null) {
  _pendingQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token!)));
  _pendingQueue = [];
}

// Response interceptor: handle 401 with refresh token
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes("/auth/login") &&
      !originalRequest.url?.includes("/auth/refresh")
    ) {
      const refreshToken = localStorage.getItem("asean_refresh_token");
      if (!refreshToken) {
        localStorage.removeItem("asean_token");
        if (window.location.pathname !== "/login") window.location.href = "/login";
        return Promise.reject(error);
      }

      if (_isRefreshing) {
        return new Promise((resolve, reject) => {
          _pendingQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return client(originalRequest);
        });
      }

      originalRequest._retry = true;
      _isRefreshing = true;

      try {
        const res = await axios.post(`${client.defaults.baseURL}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        const { access_token, refresh_token: newRefresh } = res.data;
        localStorage.setItem("asean_token", access_token);
        localStorage.setItem("asean_refresh_token", newRefresh);
        client.defaults.headers.common.Authorization = `Bearer ${access_token}`;
        _processQueue(null, access_token);
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return client(originalRequest);
      } catch (refreshError) {
        _processQueue(refreshError, null);
        localStorage.removeItem("asean_token");
        localStorage.removeItem("asean_refresh_token");
        if (window.location.pathname !== "/login") window.location.href = "/login";
        return Promise.reject(refreshError);
      } finally {
        _isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

// Named export for existing code that imports { api }
export { client as api };
export default client;
