import { createContext, useContext, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createAppliance, deleteAppliance, getAppliances, getSchedules,
  optimize as apiOptimize, updateAppliance, explainSchedule, forecastDurations,
  qaoaAnalysis, recomputeBill, getLiveWeather,
} from "./api";
import { useAuth } from "./AuthContext";
import { FLEX_FORECAST } from "./forecastConfig";

const AppDataContext = createContext(null);

// Geolocation fallback when the browser denies/lacks it — central Hà Nội.
const HANOI = { lat: 21.0285, lon: 105.8542 };

// --- date helpers: the UI works in local yyyy-mm-dd strings; the backend needs day_of_month
// (1-30) for the EVN tier baseline and days_ahead (0=today) to pick the forecast block. ---
function toISODate(d) {
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}
function addDaysISO(iso, n) {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + n);
  return toISODate(d);
}
function daysBetween(fromISO, toISO) {
  const a = new Date(`${fromISO}T00:00:00`);
  const b = new Date(`${toISO}T00:00:00`);
  return Math.round((b - a) / 86400000);
}
// The tier-price profile only accepts [1, 30]; the 31st clamps to 30 (a whole-day of extra
// baseline consumption is immaterial to the marginal tier and keeps the backend from erroring).
function isoToDayOfMonth(iso) {
  return Math.min(30, new Date(`${iso}T00:00:00`).getDate());
}

// Flatten the optimized plan into per-device ON/OFF moments (integer hours 0-23) so the
// notification hook can compare them against the wall clock. This is a PLANNING app — it never
// controls real hardware, so these events only ever drive simulated in-app reminders.
function buildDeviceEvents(schedule, fixedHours, appliances) {
  const byName = Object.fromEntries(appliances.map((a) => [a.name, a]));
  const events = [];
  // Flexible devices: a single start hour from the solver + duration => on at start, off after.
  for (const [name, start] of Object.entries(schedule ?? {})) {
    const a = byName[name];
    if (!a) continue;
    const len = Math.max(1, Math.ceil(a.duration_hours));
    events.push({ name, type: "on", hour: start % 24 });
    events.push({ name, type: "off", hour: (start + len) % 24 });
  }
  // Fixed devices: an explicit list of ON hours. Collapse contiguous runs into on/off moments.
  for (const [name, hoursArr] of Object.entries(fixedHours ?? {})) {
    const hours = [...(hoursArr ?? [])].sort((a, b) => a - b);
    if (!hours.length) continue;
    let runStart = hours[0];
    let prev = hours[0];
    for (let i = 1; i <= hours.length; i++) {
      if (hours[i] === prev + 1) { prev = hours[i]; continue; }
      events.push({ name, type: "on", hour: runStart });
      events.push({ name, type: "off", hour: (prev + 1) % 24 });
      runStart = hours[i];
      prev = hours[i];
    }
  }
  return events;
}

export function useAppData() {
  const ctx = useContext(AppDataContext);
  if (!ctx) throw new Error("useAppData must be used within AppDataProvider");
  return ctx;
}

export function AppDataProvider({ children }) {
  const [appliances, setAppliances] = useState([]);
  const [dayOfMonth, setDayOfMonth] = useState(9);
  const [todayISO] = useState(() => toISODate(new Date()));
  const [selectedDate, setSelectedDate] = useState(() => toISODate(new Date()));
  const [weather, setWeather] = useState("sunny");
  const [weatherLoading, setWeatherLoading] = useState(false);
  // false once we know the selected day is beyond the forecast horizon (assumed sunny).
  const [forecastAvailable, setForecastAvailable] = useState(true);
  const coordsRef = useRef(null);
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
  // Simulated device on/off reminders (in-memory only — never persisted, never controls hardware).
  const [notifications, setNotifications] = useState([]);
  const firedRef = useRef(new Set()); // event keys already notified today, so we alert once each
  const firedDayRef = useRef(toISODate(new Date()));
  const debounceRef = useRef(null);
  const billDebounceRef = useRef(null);
  const { logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    loadAppliances();
    // Rehydrate saved history first, then override day/weather with live values so the
    // Optimize tab always runs against today's date + current weather (badges are read-only).
    (async () => { await loadLatestSchedule(); detectLiveConditions(); })();
  }, []);

  // Auto-detect current date + resolve geolocation once, then load today's weather.
  // Any failure (permission denied, no geolocation, network) falls back to Hà Nội + "sunny".
  async function detectLiveConditions() {
    setSelectedDate(todayISO);
    setDayOfMonth(isoToDayOfMonth(todayISO));
    coordsRef.current = await new Promise((resolve) => {
      if (!navigator.geolocation) return resolve(HANOI);
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
        () => resolve(HANOI),
        { timeout: 8000 }
      );
    });
    await refreshWeather(0);
  }

  // Fetch weather for a day offset (0 = today) using the cached coords, and record whether a
  // real forecast was available so the UI can warn when we fell back to a sunny assumption.
  async function refreshWeather(daysAhead) {
    setWeatherLoading(true);
    const coords = coordsRef.current ?? HANOI;
    try {
      const { condition, forecast_available } = await getLiveWeather(coords.lat, coords.lon, daysAhead);
      if (condition) setWeather(condition);
      setForecastAvailable(forecast_available ?? true);
    } catch {
      // Our-side failure: keep "sunny" and treat future days as unavailable so we don't imply
      // a real forecast we never got (the UI only surfaces this for days after today).
      setForecastAvailable(false);
    } finally {
      setWeatherLoading(false);
    }
  }

  // Change the optimization day (from the date selector). Keeps weather + day_of_month in sync
  // so runOptimize/recomputeBill/qaoaAnalysis pick up the new day with no changes at their sites.
  function changeDate(dateStr) {
    setSelectedDate(dateStr);
    setDayOfMonth(isoToDayOfMonth(dateStr));
    refreshWeather(daysBetween(todayISO, dateStr));
  }

  // Rehydrate the most recent optimization on entry so a page reload doesn't reset
  // to a blank state (the schedule + bills + fixed windows are persisted server-side).
  async function loadLatestSchedule() {
    try {
      const list = await getSchedules();
      if (list && list.length) {
        const s = list[0];
        setDayOfMonth(s.day_of_month);
        setWeather(s.weather_condition);
        setResult({ ...s, _runId: `saved-${s.id}` });
      }
    } catch {
      /* no history yet, or not authenticated — start fresh */
    }
  }

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

  // Poll the wall clock every 60s (no network) and raise an in-app reminder the moment we cross a
  // device's planned ON/OFF hour. Purely simulated — the app schedules, it does not switch devices.
  useEffect(() => {
    function pushNotification(ev) {
      const verb = ev.type === "on" ? "bật" : "tắt";
      const icon = ev.type === "on" ? "🔔" : "🔕";
      setNotifications((prev) => [
        {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          text: `${icon} Đã đến giờ ${verb} ${ev.name} (dự kiến, không điều khiển thiết bị thật)`,
          type: ev.type,
          at: new Date(),
          read: false,
        },
        ...prev,
      ].slice(0, 50));
    }

    function tick() {
      if (!result) return;
      const now = new Date();
      const todayStr = toISODate(now);
      if (todayStr !== firedDayRef.current) { firedRef.current = new Set(); firedDayRef.current = todayStr; }
      const hour = now.getHours();
      for (const ev of buildDeviceEvents(result.schedule, fixedHours, appliances)) {
        const key = `${todayStr}|${ev.name}|${ev.type}|${ev.hour}`;
        if (firedRef.current.has(key)) continue;
        if (ev.hour === hour) { firedRef.current.add(key); pushNotification(ev); }
      }
    }

    tick(); // fire immediately for any device whose hour is active right now
    const id = setInterval(tick, 60000);
    return () => clearInterval(id);
  }, [result, fixedHours, appliances]);

  function markAllRead() {
    setNotifications((prev) => prev.map((n) => (n.read ? n : { ...n, read: true })));
  }
  function clearNotifications() {
    setNotifications([]);
  }

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

  async function runOptimize(pinned = {}, overrides = durationOverrides) {
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
        ...(Object.keys(overrides).length ? { duration_overrides: overrides } : {}),
        ...(isDrag ? { pinned_schedule: pinned } : {}),
      });
      setResult({ ...data, _runId: Date.now(), _forDate: selectedDate });
    } catch {
      setError("Lỗi khi tối ưu hóa. Kiểm tra backend đã chạy chưa?");
      // Kéo-thả thất bại: GanttEditor đã optimistic dời khối sang chỗ mới. Bơm lại một tham chiếu
      // schedule mới (cùng giá trị cũ) để effect reset trong GanttEditor chạy lại, đưa khối về đúng
      // vị trí trước khi kéo thay vì để nó nằm ở chỗ vừa thả.
      if (isDrag) setResult((prev) => prev && { ...prev, schedule: { ...prev.schedule } });
    } finally {
      setLoading(false);
      setReoptimizing(false);
    }
  }

  function handlePinnedChange(newPinned) {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runOptimize(newPinned), 400);
  }

  // Gỡ override thời lượng dự báo (ML): xóa forecasts và tối ưu lại với thời lượng thật ngay
  // lập tức (truyền overrides rỗng vì setForecasts chưa kịp cập nhật closure của runOptimize).
  function clearDurationOverrides() {
    setForecasts({});
    runOptimize({}, {});
  }

  function handleFixedHoursChange(newFixedHours) {
    const prevFixedHours = fixedHours; // for revert if the recompute request fails
    setError("");
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
        // Không nuốt lỗi: trả các ô giờ về trạng thái trước (GanttEditor đồng bộ lại từ prop
        // fixedHours) và báo cho người dùng thay vì âm thầm giữ nguyên hóa đơn cũ.
        setFixedHours(prevFixedHours);
        setError("Lỗi khi tính lại hóa đơn. Kiểm tra backend đã chạy chưa?");
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
      // Đứt giữa chừng: đã đọc được một phần text → NỐI THÊM dấu gián đoạn, không ghi đè mất phần
      // đang đọc. Lỗi ngay từ đầu (401/500, chưa có text) → hiện thông báo rõ ràng.
      setExplainText((prev) =>
        prev ? `${prev} …[Kết nối gián đoạn]` : "Không thể kết nối Gemini. Vui lòng thử lại."
      );
    } finally {
      setExplainLoading(false);
    }
  }

  const totalKwh = appliances.reduce((sum, a) => {
    // On-demand (is_flexible=false) devices carry a placeholder duration_hours=1.0; their real
    // daily run-time is the ON hours the user set (fixedHours) — same basis BillChart's pie uses.
    const hoursPerDay = a.is_flexible
      ? a.duration_hours
      : (fixedHours[a.name]?.length ?? a.duration_hours);
    return sum + (a.power_w / 1000) * hoursPerDay * 30 * (a.quantity ?? 1);
  }, 0);

  const value = {
    appliances, totalKwh, handleSave, handleDelete, handleAdd,
    dayOfMonth, setDayOfMonth, weather, setWeather, weatherLoading,
    todayISO, tomorrowISO: addDaysISO(todayISO, 1), maxDateISO: addDaysISO(todayISO, 5),
    selectedDate, changeDate, forecastAvailable,
    result, loading, reoptimizing, error, runOptimize,
    forecastInputs, setForecastField, forecasts, forecasting, handleForecast,
    fixedHours, handlePinnedChange, handleFixedHoursChange,
    durationOverrides, clearDurationOverrides,
    analysis, analyzing, handleAnalyze,
    explainText, explainLoading, handleExplain,
    notifications, markAllRead, clearNotifications,
  };

  return <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>;
}
