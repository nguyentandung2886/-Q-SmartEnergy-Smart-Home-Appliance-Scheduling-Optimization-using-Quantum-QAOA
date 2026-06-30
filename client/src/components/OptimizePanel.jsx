import { motion } from "framer-motion";

const WEATHER_OPTIONS = [
  { value: "sunny", label: "☀️ Nắng" },
  { value: "cloudy", label: "⛅ Có mây" },
  { value: "rainy", label: "🌧 Mưa" },
];

const PROGRAM_LABELS = { quick: "Nhanh", normal: "Thường", heavy: "Mạnh" };

// Đặc trưng công việc cho lớp ML dự báo thời lượng (khớp forecaster.FORECAST_SCHEMA backend).
export const FLEX_FORECAST = [
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

/**
 * Pre-optimization inputs: the classical ML duration forecaster (feeds QAOA)
 * and the optimize controls (day of month, weather, run button).
 */
export default function OptimizePanel({
  dayOfMonth,
  setDayOfMonth,
  weather,
  setWeather,
  loading,
  error,
  onOptimize,
  forecastInputs,
  setForecastField,
  forecasts,
  forecasting,
  onForecast,
}) {
  return (
    <>
      {/* ML duration forecasting (classical layer feeding QAOA) */}
      <div className="section-card glass-panel">
        <h2>Dự báo thời gian chạy (ML cổ điển)</h2>
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginTop: "-0.5rem" }}>
          Mô hình hồi quy tuyến tính (numpy, tự cài) học từ đặc trưng công việc để dự báo thời
          lượng chạy, rồi đưa vào QAOA — lớp classical cấp dữ liệu cho lớp lượng tử.
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
          {FLEX_FORECAST.map((a) => (
            <div key={a.name} className="forecast-card glass-panel" style={{ minWidth: 210, padding: "1rem", flex: "1 1 210px" }}>
              <strong style={{ fontSize: "1rem", color: "var(--quantum)", display: "block", marginBottom: "0.5rem" }}>{a.name}</strong>
              {a.fields.map((f) => (
                <label key={f.key} style={{ display: "block", fontSize: "0.8rem", marginTop: "0.5rem" }}>
                  {f.label}
                  {f.type === "select" ? (
                    <select
                      value={forecastInputs[a.name][f.key]}
                      onChange={(e) => setForecastField(a.name, f.key, e.target.value)}
                      style={{ marginTop: "0.3rem", width: "100%", background: "rgba(0, 0, 0, 0.3)", border: "1px solid rgba(255, 255, 255, 0.1)" }}
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
                      style={{ marginTop: "0.3rem", width: "100%", background: "rgba(0, 0, 0, 0.3)", border: "1px solid rgba(255, 255, 255, 0.1)" }}
                    />
                  )}
                </label>
              ))}
              {forecasts[a.name] && (
                <div style={{ marginTop: "1rem", padding: "0.5rem", background: "rgba(6, 182, 212, 0.1)", borderRadius: "6px", border: "1px solid rgba(6, 182, 212, 0.3)", fontSize: "0.85rem", color: "var(--teal)", fontWeight: 600, textAlign: "center" }}>
                  Dự kiến: {forecasts[a.name].predicted_hours}h
                  <div style={{ color: "var(--text-muted)", fontWeight: 400, fontSize: "0.75rem", marginTop: "0.2rem" }}>Độ lệch (MAE): {forecasts[a.name].test_mae}h</div>
                </div>
              )}
            </div>
          ))}
        </div>
        <button className="btn-primary" onClick={onForecast} disabled={forecasting} style={{ marginTop: "1.2rem", width: "100%", maxWidth: "300px" }}>
          {forecasting ? "Đang phân tích dữ liệu..." : "Chạy mô hình dự báo AI"}
        </button>
        {Object.keys(forecasts).length > 0 && (
          <div style={{ marginTop: "0.75rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
            Thời lượng dự báo đã được cập nhật. Hãy nhấn <strong>Tối ưu hóa</strong> để áp dụng.
          </div>
        )}
      </div>

      {/* Optimize controls */}
      <div className="section-card glass-panel">
        <h2>Tối ưu hóa lịch chạy</h2>
        <div className="optimize-controls">
          <label>
            Ngày trong tháng
            <input type="number" min={1} max={30} value={dayOfMonth}
              onChange={(e) => setDayOfMonth(e.target.value)} />
          </label>
          <label>
            Thời tiết hôm nay
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <select value={weather} onChange={(e) => setWeather(e.target.value)}>
                {WEATHER_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
              <button 
                type="button" 
                className="btn-primary" 
                style={{ padding: "0 10px", fontSize: "0.85rem" }}
                title="Lấy thời tiết thực tế từ GPS"
                onClick={async () => {
                  try {
                    const { getLiveWeather } = await import("../api");
                    navigator.geolocation.getCurrentPosition(
                      async (pos) => {
                        const condition = await getLiveWeather(pos.coords.latitude, pos.coords.longitude);
                        setWeather(condition.condition);
                      },
                      async () => {
                        // Fallback to TP.HCM if GPS denied
                        const condition = await getLiveWeather(10.823, 106.6297);
                        setWeather(condition.condition);
                      }
                    );
                  } catch (e) {
                    console.error("Live weather failed:", e);
                  }
                }}
              >
                Live
              </button>
            </div>
          </label>
          <motion.button
            className="btn-optimize"
            onClick={onOptimize}
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
            style={{ marginTop: "1rem", color: "var(--quantum)", fontWeight: 600, textShadow: "0 0 10px var(--quantum-glow)" }}
          >
            ⚡ Quantum Engine is calculating optimal superposition...
          </motion.div>
        )}
        {error && <p className="auth-error" style={{ marginTop: "0.75rem" }}>{error}</p>}
      </div>
    </>
  );
}
