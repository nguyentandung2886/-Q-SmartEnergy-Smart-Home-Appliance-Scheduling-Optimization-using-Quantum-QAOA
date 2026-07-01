import { motion } from "framer-motion";
import { useAppData } from "../AppData";
import { FLEX_FORECAST, PROGRAM_LABELS } from "../forecastConfig";

export default function ForecastTab() {
  const { forecastInputs, setForecastField, forecasts, forecasting, handleForecast } = useAppData();

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <div className="page-head">
        <p className="eyebrow">Bước 2</p>
        <h1>Dự báo thời gian chạy</h1>
        <p className="page-sub">
          Mô hình hồi quy tuyến tính cổ điển (numpy, tự cài) học từ đặc trưng công việc để dự báo
          thời lượng chạy của từng thiết bị linh hoạt, rồi cấp con số đó cho lớp lượng tử QAOA.
        </p>
      </div>

      <div className="bento">
        {FLEX_FORECAST.map((a) => (
          <div key={a.name} className="card">
            <div className="card-head">
              <h3>{a.name}</h3>
              <span className="tag">ML</span>
            </div>
            {a.fields.map((f) => (
              <label key={f.key} className="field">
                <span>{f.label}</span>
                {f.type === "select" ? (
                  <select value={forecastInputs[a.name][f.key]}
                    onChange={(e) => setForecastField(a.name, f.key, e.target.value)}>
                    {f.options.map((o) => <option key={o} value={o}>{PROGRAM_LABELS[o]}</option>)}
                  </select>
                ) : (
                  <input type="number" min={f.min} max={f.max} step={f.step}
                    value={forecastInputs[a.name][f.key]}
                    onChange={(e) => setForecastField(a.name, f.key, Number(e.target.value))} />
                )}
              </label>
            ))}
            {forecasts[a.name] && (
              <div className="forecast-result">
                <span className="forecast-hours mono">{forecasts[a.name].predicted_hours}h</span>
                <span className="forecast-mae">MAE {forecasts[a.name].test_mae}h</span>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="row-actions">
        <button className="btn-ink" onClick={handleForecast} disabled={forecasting}>
          {forecasting ? "Đang phân tích…" : "Chạy mô hình dự báo"}
        </button>
        {Object.keys(forecasts).length > 0 && (
          <span className="hint">Thời lượng dự báo sẽ được áp dụng khi bạn chạy Tối ưu hóa.</span>
        )}
      </div>
    </motion.div>
  );
}
