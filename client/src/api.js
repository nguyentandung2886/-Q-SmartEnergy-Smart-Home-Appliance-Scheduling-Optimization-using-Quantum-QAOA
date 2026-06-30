/**
 * Axios client + all backend API calls.
 * JWT token is read from localStorage and injected as Authorization header on every request.
 */
import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const apiClient = axios.create({ baseURL: API_BASE_URL });

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function register(username, password) {
  const { data } = await apiClient.post("/auth/register", { username, password });
  return data;
}

export async function login(username, password) {
  const { data } = await apiClient.post("/auth/login", { username, password });
  return data;
}

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

// Returns raw fetch Response (not axios) — needed for SSE ReadableStream
export function explainSchedule(payload) {
  return fetch(`${API_BASE_URL}/explain`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem("token")}`,
    },
    body: JSON.stringify(payload),
  });
}

export default apiClient;
