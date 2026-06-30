import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  createAppliance, deleteAppliance, getAppliances,
  optimize as apiOptimize, updateAppliance, explainSchedule, forecastDurations,
} from "../api";
import { useAuth } from "../AuthContext";
import { useCountUp } from "../useCountUp";
import GanttEditor from "../components/GanttEditor";

const WEATHER_OPTIONS = [
  { value: "sunny", label: "☀️ Nắng" },
  { value: "cloudy", label: "⛅ Có mây" },
  { value: "rainy", label: "🌧 Mưa" },
];

const PROGRAM_LABELS = { quick: "Nhanh", normal: "Thường", heavy: "Mạnh" };

// Đặc trưng công việc cho lớp ML dự báo thời lượng (khớp forecaster.FORECAST_SCHEMA backend).
const FLEX_FORECAST = [
  {
    name: "Máy giặt",
    fields: [
      { key: "load_kg", label: "Khối lượng đồ (kg)", type: "number", default: 5, min: 1, max: 9, step: 0.5 },
      { key: "program", label: "Chương trình", type: "select", default: "normal", options: ["quick", "normal", "heavy"] },
    ],
  },
  { name: "Bình nước nóng gián tiếp", fields: [{ key: "people", label: "Số người dùng", type: "number", default: 4, min: 1, max: 6, step: 1 }] },
  { name: "Bình nước nóng trực tiếp", fields: [{ key: "people", label: "Số người dùng", type: "number", default: 4, min: 1, max: 6, step: 1 }] },
];

function ApplianceRow({ appliance, onSave, onDelete }) {
  const [power, setPower] = useState(appliance.power_w);
  const [duration, setDuration] = useState(appliance.duration_hours);
  const [quantity, setQuantity] = useState(appliance.quantity ?? 1);

  function save(overrides = {}) {
    onSave(appliance.id, {
      ...appliance,
      power_w: Number(power),
      duration_hours: Number(duration),
      quantity: Number(quantity),
      ...overrides,
    });
  }

  function handleBlur() {
    const changed =
      Number(power) !== appliance.power_w ||
      Number(duration) !== appliance.duration_hours ||
      Number(quantity) !== (appliance.quantity ?? 1);
    if (changed) save();
  }

  function toggleFlexible() {
    save({ is_flexible: !appliance.is_flexible });
  }

  return (
    <tr>
      <td>{appliance.name}</td>
      <td>
        <input type="number" value={power} min={1}
          onChange={(e) => setPower(e.target.value)} onBlur={handleBlur} />
      </td>
      <td>
        <input type="number" value={duration} min={0.1} step={0.1}
          onChange={(e) => setDuration(e.target.value)} onBlur={handleBlur} />
      </td>
      <td>
        <input type="number" value={quantity} min={1} step={1}
          onChange={(e) => setQuantity(e.target.value)} onBlur={handleBlur} />
      </td>
      <td>
        <button
          onClick={toggleFlexible}
          style={{
            background: "none", border: "none", cursor: "pointer", padding: "2px 6px",
            borderRadius: "4px", fontSize: "0.8rem", fontWeight: 600,
            color: appliance.is_flexible ? "var(--teal)" : "var(--text-muted)",
            border: `1px solid ${appliance.is_flexible ? "var(--teal)" : "#d1d5db"}`,
          }}
          title="Bấm để đổi loại"
        >
          {appliance.is_flexible ? "Linh hoạt" : "Cố định"}
        </button>
      </td>
      <td>
        <button onClick={() => onDelete(appliance.id)}>Xóa</button>
      </td>
    </tr>
  );
}

function ResultsBillNumbers({ billBefore, billAfter, savingsPct }) {
  const animBefore = useCountUp(billBefore);
  const animAfter = useCountUp(billAfter);
  const animSavings = useCountUp(savingsPct, 800, 1);

  return (
    <div className="bill-numbers">
      <div className="bill-item">
        <strong>{animBefore.toLocaleString("vi-VN")}đ</strong>
        Hóa đơn trước
      </div>
      <div style={{ fontSize: "1.5rem", alignSelf: "center" }}>→</div>
      <div className="bill-item">
        <strong style={{ color: "var(--teal)" }}>{animAfter.toLocaleString("vi-VN")}đ</strong>
        Sau tối ưu hóa
      </div>
      <div className="bill-item">
        <strong className="savings-highlight">↓ {animSavings.toFixed(1)}%</strong>
        Tiết kiệm
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [appliances, setAppliances] = useState([]);
  const [dayOfMonth, setDayOfMonth] = useState(9);
  const [weather, setWeather] = useState("sunny");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reoptimizing, setReoptimizing] = useState(false);
  const [error, setError] = useState("");
  const [newName, setNewName] = useState("");
  const [newPower, setNewPower] = useState(100);
  const [newDuration, setNewDuration] = useState(1);
  const [newQty, setNewQty] = useState(1);
  const [pinnedSchedule, setPinnedSchedule] = useState({});
  const [explainText, setExplainText] = useState("");
  const [explainLoading, setExplainLoading] = useState(false);
  const [forecastInputs, setForecastInputs] = useState(() =>
    Object.fromEntries(
      FLEX_FORECAST.map((a) => [a.name, Object.fromEntries(a.fields.map((f) => [f.key, f.default]))])
    )
  );
  const [forecasts, setForecasts] = useState({}); // { name: { predicted_hours, test_mae } }
  const [forecasting, setForecasting] = useState(false);
  const debounceRef = useRef(null);
  const { logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => { loadAppliances(); }, []);

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

  async function handleSetAllFlexible() {
    await Promise.all(
      appliances
        .filter((a) => !a.is_flexible)
        .map((a) => updateAppliance(a.id, { ...a, is_flexible: true }))
    );
    await loadAppliances();
  }

  async function handleAdd(e) {
    e.preventDefault();
    await createAppliance({
      name: newName, power_w: Number(newPower), duration_hours: Number(newDuration),
      quantity: Number(newQty), candidate_hours: [], is_flexible: false,
    });
    setNewName(""); setNewPower(100); setNewDuration(1); setNewQty(1);
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
      const data = await forecastDurations(forecastInputs);
      setForecasts(data);
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
    } else {
      setLoading(true);
      setResult(null);
      setPinnedSchedule({});
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
      setResult(data);
    } catch {
      setError("Lỗi khi tối ưu hóa. Kiểm tra backend đã chạy chưa?");
    } finally {
      setLoading(false);
      setReoptimizing(false);
    }
  }

  function handlePinnedChange(newPinned) {
    setPinnedSchedule(newPinned);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runOptimize(newPinned), 400);
  }

  async function handleExplain() {
    setExplainText("");
    setExplainLoading(true);
    try {
      const response = await explainSchedule({
        schedule: result.schedule,
        appliances: appliances.map((a) => ({
          name: a.name,
          power_w: a.power_w,
          duration_hours: a.duration_hours,
          is_flexible: a.is_flexible,
        })),
        bill_before_vnd: result.bill_before_vnd,
        bill_after_vnd: result.bill_after_vnd,
        savings_percent: result.savings_percent,
        weather_condition: result.weather_condition,
        solver_used: result.solver_used,
      });
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        for (const line of text.split("\n")) {
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

  function handleLogout() { logout(); navigate("/login"); }

  const totalKwh = appliances.reduce(
    (sum, a) => sum + (a.power_w / 1000) * a.duration_hours * 30 * (a.quantity ?? 1), 0
  );

  return (
    <motion.div
      className="dashboard"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
    >
      <header className="dashboard-header">
        <h1>Q-SmartEnergy</h1>
        <nav>
          <button onClick={() => navigate("/history")}>📋 Lịch sử</button>
          <button onClick={handleLogout}>Đăng xuất</button>
        </nav>
      </header>

      {/* Appliance list */}
      <div className="section-card">
        <h2>Thiết bị của bạn — tổng ~{totalKwh.toFixed(0)} kWh/tháng</h2>
        <table>
          <thead>
            <tr>
              <th>Tên thiết bị</th><th>Công suất (W)</th>
              <th>Giờ dùng</th><th>Số lượng</th><th>Loại</th><th></th>
            </tr>
          </thead>
          <tbody>
            {appliances.map((a) => (
              <ApplianceRow key={a.id} appliance={a} onSave={handleSave} onDelete={handleDelete} />
            ))}
          </tbody>
        </table>
        {appliances.some((a) => !a.is_flexible) && (
          <button
            onClick={handleSetAllFlexible}
            style={{
              margin: "0.5rem 0", background: "none", border: "1px solid var(--teal)",
              color: "var(--teal)", borderRadius: "6px", padding: "4px 12px",
              cursor: "pointer", fontSize: "0.82rem", fontWeight: 600,
            }}
          >
            ⟳ Đặt tất cả thành Linh hoạt
          </button>
        )}
        <form onSubmit={handleAdd} className="add-form">
          <input placeholder="Tên thiết bị mới" value={newName}
            onChange={(e) => setNewName(e.target.value)} required />
          <input type="number" placeholder="Công suất (W)" value={newPower} min={1}
            onChange={(e) => setNewPower(e.target.value)} required />
          <input type="number" placeholder="Giờ/ngày" value={newDuration} min={0.1} step={0.1}
            onChange={(e) => setNewDuration(e.target.value)} required />
          <input type="number" placeholder="Số lượng" value={newQty} min={1} step={1}
            onChange={(e) => setNewQty(e.target.value)} required style={{ width: "80px" }} />
          <button type="submit">+ Thêm thiết bị</button>
        </form>
      </div>

      {/* ML duration forecasting (classical layer feeding QAOA) */}
      <div className="section-card">
        <h2>🔮 Dự báo thời gian chạy (ML cổ điển)</h2>
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "-0.5rem" }}>
          Mô hình hồi quy tuyến tính (numpy, tự cài) học từ đặc trưng công việc để dự báo thời
          lượng chạy, rồi đưa vào QAOA — lớp classical cấp dữ liệu cho lớp lượng tử.
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
          {FLEX_FORECAST.map((a) => (
            <div key={a.name} style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: "0.75rem", minWidth: 210 }}>
              <strong style={{ fontSize: "0.9rem" }}>{a.name}</strong>
              {a.fields.map((f) => (
                <label key={f.key} style={{ display: "block", fontSize: "0.8rem", marginTop: "0.5rem" }}>
                  {f.label}
                  {f.type === "select" ? (
                    <select
                      value={forecastInputs[a.name][f.key]}
                      onChange={(e) => setForecastField(a.name, f.key, e.target.value)}
                    >
                      {f.options.map((o) => (
                        <option key={o} value={o}>{PROGRAM_LABELS[o]}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="number" min={f.min} max={f.max} step={f.step}
                      value={forecastInputs[a.name][f.key]}
                      onChange={(e) => setForecastField(a.name, f.key, Number(e.target.value))}
                    />
                  )}
                </label>
              ))}
              {forecasts[a.name] && (
                <div style={{ marginTop: "0.5rem", fontSize: "0.82rem", color: "var(--teal)", fontWeight: 600 }}>
                  ⏱ {forecasts[a.name].predicted_hours}h
                  <span style={{ color: "var(--text-muted)", fontWeight: 400 }}> (MAE {forecasts[a.name].test_mae}h)</span>
                </div>
              )}
            </div>
          ))}
        </div>
        <button onClick={handleForecast} disabled={forecasting} style={{ marginTop: "0.75rem" }}>
          {forecasting ? "⏳ Đang dự báo..." : "🔮 Dự báo & áp dụng"}
        </button>
        {Object.keys(forecasts).length > 0 && (
          <span style={{ marginLeft: "0.75rem", fontSize: "0.8rem", color: "var(--text-muted)" }}>
            Thời lượng dự báo sẽ được dùng khi bấm Tối ưu hóa.
          </span>
        )}
      </div>

      {/* Optimize controls */}
      <div className="section-card">
        <h2>Tối ưu hóa lịch chạy</h2>
        <div className="optimize-controls">
          <label>
            Ngày trong tháng
            <input type="number" min={1} max={30} value={dayOfMonth}
              onChange={(e) => setDayOfMonth(e.target.value)} />
          </label>
          <label>
            Thời tiết hôm nay
            <select value={weather} onChange={(e) => setWeather(e.target.value)}>
              {WEATHER_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
          <motion.button
            className="btn-optimize"
            onClick={() => runOptimize()}
            disabled={loading}
            whileHover={{ scale: loading ? 1 : 1.03 }}
            whileTap={{ scale: loading ? 1 : 0.97 }}
          >
            {loading ? "⏳ Đang tối ưu..." : "⚡ Tối ưu hóa"}
          </motion.button>
        </div>
        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: [0.4, 1, 0.4] }}
            transition={{ repeat: Infinity, duration: 1.2 }}
            style={{ marginTop: "0.75rem", color: "var(--indigo)", fontWeight: 600 }}
          >
            ⚡ Thuật toán lượng tử đang xử lý...
          </motion.div>
        )}
        {error && <p className="auth-error" style={{ marginTop: "0.75rem" }}>{error}</p>}
      </div>

      {/* Results */}
      <AnimatePresence>
        {result && (
          <motion.div
            className="section-card results-section"
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
          >
            <h2>Kết quả</h2>
            <ResultsBillNumbers
              billBefore={result.bill_before_vnd}
              billAfter={result.bill_after_vnd}
              savingsPct={result.savings_percent}
            />
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
              Solver: {result.solver_used}
              {result.used_fallback ? " (dùng fallback cổ điển)" : ""}
            </p>

            {/* Re-optimize pulse */}
            {reoptimizing && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ repeat: Infinity, duration: 1.2 }}
                style={{
                  color: "var(--indigo)", fontWeight: 600,
                  marginBottom: "0.5rem", fontSize: "0.85rem",
                }}
              >
                ⚡ Đang tính lại lịch...
              </motion.div>
            )}

            {/* Interactive Gantt — all appliances: fixed at hour 0, flexible at QAOA hour */}
            <GanttEditor
              schedule={{
                ...appliances.reduce((acc, a) => ({ ...acc, [a.name]: 0 }), {}),
                ...result.schedule,
              }}
              appliances={appliances}
              onPinnedChange={handlePinnedChange}
              disabled={reoptimizing}
            />

            {/* Bill comparison chart (static PNG, unchanged) */}
            {result.bill_chart_png && (
              <img
                src={`data:image/png;base64,${result.bill_chart_png}`}
                alt="So sánh hóa đơn điện"
                style={{ marginTop: "1rem" }}
              />
            )}

            {/* Storytelling section */}
            <div style={{ marginTop: "1rem" }}>
              <motion.button
                className="btn-explain"
                onClick={handleExplain}
                disabled={explainLoading}
                whileHover={{ scale: explainLoading ? 1 : 1.03 }}
                whileTap={{ scale: explainLoading ? 1 : 0.97 }}
              >
                ✨ Giải thích kết quả
              </motion.button>

              {explainLoading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: [0.4, 1, 0.4] }}
                  transition={{ repeat: Infinity, duration: 1.2 }}
                  style={{
                    marginTop: "0.75rem",
                    color: "var(--indigo)",
                    fontSize: "0.85rem",
                  }}
                >
                  ⟳ Gemini đang phân tích...
                </motion.div>
              )}

              {explainText && (
                <div className="explain-card">
                  <strong>💡 Phân tích kết quả</strong>
                  <p style={{ marginTop: "0.5rem", whiteSpace: "pre-wrap" }}>
                    {explainText}
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
