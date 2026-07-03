/**
 * Axios client + all backend API calls.
 * The Supabase access token is read from the current session and injected as the
 * Authorization header on every request.
 */
import axios from "axios";
import { supabase } from "./supabaseClient";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const apiClient = axios.create({ baseURL: API_BASE_URL });

apiClient.interceptors.request.use(async (config) => {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// If the backend rejects the token (stale/expired/deleted Supabase session),
// clear the local session so the app falls back to the login screen instead of
// looping on 401s with a dead session.
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      await supabase.auth.signOut({ scope: "local" });
    }
    return Promise.reject(error);
  }
);

export async function getAppliances() {
  const { data } = await apiClient.get("/appliances");
  return data;
}

export async function createAppliance(appliance) {
  const { data } = await apiClient.post("/appliances", appliance);
  return data;
}

export async function updateAppliance(id, appliance) {
  const { data } = await apiClient.put(`/appliances/${id}`, appliance);
  return data;
}

export async function deleteAppliance(id) {
  await apiClient.delete(`/appliances/${id}`);
}

export async function optimize(params) {
  const { data } = await apiClient.post("/optimize", params);
  return data;
}

export async function getSchedules() {
  const { data } = await apiClient.get("/schedules");
  return data;
}

// ML duration forecast: jobs = { applianceName: { feature: value } }
export async function forecastDurations(jobs) {
  const { data } = await apiClient.post("/forecast", { jobs });
  return data;
}

// QAOA hyperparameter sweep vs classical brute-force optimum
export async function qaoaAnalysis(params) {
  const { data } = await apiClient.post("/qaoa-analysis", params);
  return data;
}

// Recompute bill from an edited schedule (fixed-hour toggles) without re-running QAOA
export async function recomputeBill(params) {
  const { data } = await apiClient.post("/recompute-bill", params);
  return data;
}

export async function sendAlert(params) {
  const { data } = await apiClient.post("/alert/", params);
  return data;
}

export async function getMe() {
  const { data } = await apiClient.get("/auth/me");
  return data;
}

export async function updateUsername(username) {
  const { data } = await apiClient.put("/auth/me", { username });
  return data;
}

export async function getMyFeedback() {
  const { data } = await apiClient.get("/feedback/me");
  return data;
}

export async function submitFeedback(payload) {
  const { data } = await apiClient.post("/feedback", payload);
  return data;
}

// Public testimonials for the landing page (no auth required).
export async function getPublicFeedback() {
  const { data } = await apiClient.get("/feedback/public");
  return data;
}

// ── Admin (role="admin" only; backend enforces via get_current_admin) ──────────
export async function getAdminStats() {
  const { data } = await apiClient.get("/admin/stats");
  return data;
}

export async function getAdminFeedback(rating) {
  const { data } = await apiClient.get("/admin/feedback", {
    params: rating ? { rating } : {},
  });
  return data;
}

export async function setFeedbackFeatured(id, isFeatured) {
  const { data } = await apiClient.patch(`/admin/feedback/${id}`, { is_featured: isFeatured });
  return data;
}

export async function getAdminUsers() {
  const { data } = await apiClient.get("/admin/users");
  return data;
}

export async function getAdminLogs({ limit = 50, offset = 0 } = {}) {
  const { data } = await apiClient.get("/admin/logs", { params: { limit, offset } });
  return data;
}

// Returns raw fetch Response (not axios) — needed for SSE ReadableStream
export async function explainSchedule(payload) {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  const response = await fetch(`${API_BASE_URL}/explain`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
  // 401/500 trả về Response với ok=false nhưng KHÔNG throw — nếu đọc stream ngay thì lỗi bị nuốt
  // im lặng (giống như chưa bấm). Ném lỗi để caller hiện thông báo rõ ràng.
  if (!response.ok) throw new Error(`Explain request failed: ${response.status}`);
  return response;
}

// Fetch weather from backend for a given day offset (0 = today, 1 = tomorrow, …).
// Returns { condition, forecast_available }; forecast_available is false when the day is
// beyond the free-tier forecast horizon (caller should warn instead of trusting "sunny").
export async function getLiveWeather(lat, lon, daysAhead = 0) {
  const { data } = await apiClient.post("/weather", { lat, lon, days_ahead: daysAhead });
  return data;
}

export default apiClient;
