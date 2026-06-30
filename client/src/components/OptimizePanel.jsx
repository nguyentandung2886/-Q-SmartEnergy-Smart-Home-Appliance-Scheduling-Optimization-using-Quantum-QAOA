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
        <button onClick={onForecast} disabled={forecasting} style={{ marginTop: "0.75rem" }}>
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
            style={{ marginTop: "0.75rem", color: "var(--indigo)", fontWeight: 600 }}
          >
            ⚡ Thuật toán lượng tử đang xử lý...
          </motion.div>
        )}
        {error && <p className="auth-error" style={{ marginTop: "0.75rem" }}>{error}</p>}
      </div>
    </>
  );
}
