import { createContext, useContext, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createAppliance, deleteAppliance, getAppliances,
  optimize as apiOptimize, updateAppliance, explainSchedule, forecastDurations,
  qaoaAnalysis, recomputeBill,
} from "./api";
import { useAuth } from "./AuthContext";
import { FLEX_FORECAST } from "./forecastConfig";

const AppDataContext = createContext(null);

export function useAppData() {
  const ctx = useContext(AppDataContext);
  if (!ctx) throw new Error("useAppData must be used within AppDataProvider");
  return ctx;
}

export function AppDataProvider({ children }) {
  const [appliances, setAppliances] = useState([]);
  const [dayOfMonth, setDayOfMonth] = useState(9);
  const [weather, setWeather] = useState("sunny");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reoptimizing, setReoptimizing] = useState(false);
  const [error, setError] = useState("");
  const [explainText, setExplainText] = useState("");
  const [explainLoading, setExplainLoading] = useState(false);
  const [forecastInputs, setForecastInputs] = useState(() =>
    Object.fromEntries(
      FLEX_FORECAST.map((a) => [a.name, Object.fromEntries(a.fields.map((f) => [f.key, f.default]))])
    )
  );
  const [forecasts, setForecasts] = useState({});
  const [forecasting, setForecasting] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [fixedHours, setFixedHours] = useState({});
  const debounceRef = useRef(null);
  const billDebounceRef = useRef(null);
  const { logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => { loadAppliances(); }, []);

  // Expand backend usage windows into per-appliance ON-hour lists on a NEW optimization
  // (keyed on _runId so a bill recompute doesn't wipe the user's edits).
  useEffect(() => {
    if (!result) return;
    const expanded = {};
    for (const [name, windows] of Object.entries(result.fixed_windows ?? {})) {
      const hours = new Set();
      for (const [start, len] of windows) {
        for (let k = 0; k < len; k++) hours.add((start + k) % 24);
      }
      expanded[name] = [...hours].sort((a, b) => a - b);
    }
    setFixedHours(expanded);
  }, [result?._runId]);

  async function loadAppliances() {
    try {
      const data = await getAppliances();
      setAppliances(data);
    } catch (err) {
      if (err.response?.status === 401) { logout(); navigate("/login"); }
    }
  }

  async function handleSave(id, payload) {
    await updateAppliance(id, payload);
    await loadAppliances();
  }

  async function handleDelete(id) {
    await deleteAppliance(id);
    await loadAppliances();
  }

  async function handleAdd(payload) {
    await createAppliance(payload);
    await loadAppliances();
  }

  const durationOverrides = Object.fromEntries(
    Object.entries(forecasts).map(([name, f]) => [name, f.predicted_hours])
  );

  function setForecastField(name, key, value) {
    setForecastInputs((prev) => ({ ...prev, [name]: { ...prev[name], [key]: value } }));
  }

  async function handleForecast() {
    setError("");
    setForecasting(true);
    try {
      setForecasts(await forecastDurations(forecastInputs));
    } catch {
      setError("Lỗi khi dự báo thời gian (ML). Kiểm tra backend đã chạy chưa?");
    } finally {
      setForecasting(false);
    }
  }

  async function runOptimize(pinned = {}) {
    const isDrag = Object.keys(pinned).length > 0;
    setError("");
    if (isDrag) {
      setReoptimizing(true);
      setExplainText("");
    } else {
      setLoading(true);
      setResult(null);
      setExplainText("");
    }
    try {
      const data = await apiOptimize({
        day_of_month: Number(dayOfMonth),
        weather_condition: weather,
        use_quantum: true,
        ...(Object.keys(durationOverrides).length ? { duration_overrides: durationOverrides } : {}),
        ...(isDrag ? { pinned_schedule: pinned } : {}),
      });
      setResult({ ...data, _runId: Date.now() });
    } catch {
      setError("Lỗi khi tối ưu hóa. Kiểm tra backend đã chạy chưa?");
    } finally {
      setLoading(false);
      setReoptimizing(false);
    }
  }

  function handlePinnedChange(newPinned) {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runOptimize(newPinned), 400);
  }

  function handleFixedHoursChange(newFixedHours) {
    setFixedHours(newFixedHours);
    if (billDebounceRef.current) clearTimeout(billDebounceRef.current);
    billDebounceRef.current = setTimeout(async () => {
      if (!result) return;
      try {
        const data = await recomputeBill({
          day_of_month: Number(dayOfMonth),
          weather_condition: weather,
          schedule: result.schedule,
          fixed_hours: newFixedHours,
          ...(Object.keys(durationOverrides).length ? { duration_overrides: durationOverrides } : {}),
        });
        setResult((prev) => prev && {
          ...prev,
          bill_before_vnd: data.bill_before_vnd,
          bill_after_vnd: data.bill_after_vnd,
          savings_percent: data.savings_percent,
          monthly_kwh: data.monthly_kwh,
        });
      } catch {
        /* keep previous bill on error */
      }
    }, 400);
  }

  async function handleAnalyze() {
    setError("");
    setAnalyzing(true);
    try {
      setAnalysis(await qaoaAnalysis({ day_of_month: Number(dayOfMonth), weather_condition: weather }));
    } catch {
      setError("Lỗi khi phân tích thuật toán QAOA.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleExplain() {
    setExplainText("");
    setExplainLoading(true);
    try {
      const response = await explainSchedule({
        schedule: result.schedule,
        appliances: appliances.map((a) => ({
          name: a.name, power_w: a.power_w, duration_hours: a.duration_hours, is_flexible: a.is_flexible,
        })),
        bill_before_vnd: result.bill_before_vnd,
        bill_after_vnd: result.bill_after_vnd,
        savings_percent: result.savings_percent,
        weather_condition: result.weather_condition,
        solver_used: result.solver_used,
      });
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buffer.indexOf("\n")) !== -1) {
          const line = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 1);
          if (!line.startsWith("data: ")) continue;
          const content = line.slice(6);
          if (content === "[DONE]") { setExplainLoading(false); return; }
          if (content) setExplainText((prev) => prev + content);
        }
      }
    } catch {
      setExplainText("Không thể kết nối Gemini. Vui lòng thử lại.");
    } finally {
      setExplainLoading(false);
    }
  }

  const totalKwh = appliances.reduce(
    (sum, a) => sum + (a.power_w / 1000) * a.duration_hours * 30 * (a.quantity ?? 1), 0
  );

  const value = {
    appliances, totalKwh, handleSave, handleDelete, handleAdd,
    dayOfMonth, setDayOfMonth, weather, setWeather,
    result, loading, reoptimizing, error, runOptimize,
    forecastInputs, setForecastField, forecasts, forecasting, handleForecast,
    fixedHours, handlePinnedChange, handleFixedHoursChange,
    analysis, analyzing, handleAnalyze,
    explainText, explainLoading, handleExplain,
  };

  return <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>;
}
