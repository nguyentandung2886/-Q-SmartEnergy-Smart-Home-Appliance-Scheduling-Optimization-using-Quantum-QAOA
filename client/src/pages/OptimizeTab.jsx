import { motion, AnimatePresence } from "framer-motion";
import { useAppData } from "../AppData";
import { WEATHER_OPTIONS } from "../forecastConfig";
import GanttEditor from "../components/GanttEditor";
import ExplainSection from "../components/ExplainSection";

const SAFE_POWER_W = 5000;
const WEATHER_ICON = { sunny: "☀️", cloudy: "⛅", rainy: "🌧️" };
const badgeStyle = { fontSize: "0.9rem", padding: "0.5rem 0.9rem", textTransform: "none", letterSpacing: 0 };

function peakPower(schedule, fixedHours, appliances) {
  const watts = Array(24).fill(0);
  const at = Array.from({ length: 24 }, () => []);
  for (const a of appliances) {
    const eff = a.power_w * (a.quantity ?? 1);
    if (a.is_flexible) {
      const h = schedule[a.name];
      if (h == null) continue;
      const len = Math.max(1, Math.ceil(a.duration_hours));
      for (let k = 0; k < len; k++) { watts[(h + k) % 24] += eff; at[(h + k) % 24].push(a.name); }
    } else {
      for (const hour of fixedHours[a.name] ?? []) { watts[hour] += eff; at[hour].push(a.name); }
    }
  }
  let peak = 0;
  for (let h = 1; h < 24; h++) if (watts[h] > watts[peak]) peak = h;
  return { peakW: watts[peak], peakHour: peak, names: [...new Set(at[peak])] };
}

export default function OptimizeTab() {
  const {
    weather, weatherLoading, loading, error, runOptimize,
    result, reoptimizing, fixedHours, appliances, handlePinnedChange, handleFixedHoursChange,
    analysis, analyzing, handleAnalyze, explainText, explainLoading, handleExplain,
    todayISO, tomorrowISO, maxDateISO, selectedDate, changeDate, forecastAvailable,
  } = useAppData();

  const peak = result ? peakPower(result.schedule, fixedHours, appliances) : null;
  const overload = peak && peak.peakW > SAFE_POWER_W;
  const fmt = (n) => Math.round(n).toLocaleString("vi-VN");

  const ddmm = (iso) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
  const isToday = selectedDate === todayISO;
  const isTomorrow = selectedDate === tomorrowISO;
  const isFuture = selectedDate > todayISO;
  const showAssumedSunny = isFuture && !forecastAvailable;
  const weatherLabel = WEATHER_OPTIONS.find((o) => o.value === weather)?.label ?? weather;

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <div className="page-head">
        <p className="eyebrow">Bước 3</p>
        <h1>Tối ưu hóa lịch chạy</h1>
        <p className="page-sub">
          Chọn ngày tối ưu (hôm nay, ngày mai hoặc trong 5 ngày tới); thời tiết được lấy tự động theo
          dự báo cho ngày đó và vị trí của bạn. Thuật toán QAOA xếp các tải linh hoạt vào khung giờ có
          nắng để tối đa tự tiêu thụ điện mặt trời và giảm hóa đơn theo biểu giá bậc thang.
        </p>
      </div>

      <div className="card">
        <div className="controls">
          <div className="field">
            <span>Ngày tối ưu</span>
            <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
              <button className={isToday ? "btn-ink" : "btn"} onClick={() => changeDate(todayISO)}>Hôm nay</button>
              <button className={isTomorrow ? "btn-ink" : "btn"} onClick={() => changeDate(tomorrowISO)}>Ngày mai</button>
              <input
                type="date"
                value={selectedDate}
                min={todayISO}
                max={maxDateISO}
                onChange={(e) => e.target.value && changeDate(e.target.value)}
              />
            </div>
          </div>
          <div className="field">
            <span>Thời tiết {isToday ? "hiện tại" : `ngày ${ddmm(selectedDate)}`}</span>
            <span className="tag" style={badgeStyle}>
              {weatherLoading ? "⏳ Đang lấy…" : `${WEATHER_ICON[weather] ?? "🌤️"} ${weatherLabel}`}
            </span>
          </div>
          <button className="btn-ink btn-lg" onClick={() => runOptimize()} disabled={loading}>
            {loading ? "Đang tối ưu…" : "Tối ưu hóa"}
          </button>
        </div>
        {showAssumedSunny && (
          <div className="safety" style={{ background: "var(--pale-yellow-bg)", color: "var(--pale-yellow-fg)", borderColor: "transparent" }}>
            ⚠️ Chưa có dữ liệu thời tiết chính xác cho ngày {ddmm(selectedDate)} (quá xa so với dự báo).
            Kết quả dùng giả định trời nắng và có thể sai lệch.
          </div>
        )}
        {error && <p className="form-error">{error}</p>}
      </div>

      <AnimatePresence>
        {result && (
          <motion.div className="card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
            <p className="hint" style={{ marginTop: 0 }}>
              Lịch tối ưu cho ngày <strong>{result._forDate ? ddmm(result._forDate) : `số ${result.day_of_month} trong tháng`}</strong>
            </p>
            <div className="bill-strip">
              <div className="bill-figure">
                <span className="bill-num">{fmt(result.bill_before_vnd)}đ</span>
                <span className="bill-label">Hóa đơn trước</span>
              </div>
              <span className="bill-arrow">→</span>
              <div className="bill-figure">
                <span className="bill-num bill-num--accent">{fmt(result.bill_after_vnd)}đ</span>
                <span className="bill-label">Sau tối ưu</span>
              </div>
              <div className="bill-figure">
                <span className="bill-num bill-num--save">↓ {result.savings_percent?.toFixed(1)}%</span>
                <span className="bill-label">Tiết kiệm</span>
              </div>
              <div className="bill-solver">
                <span className="tag">{result.solver_used}{result.used_fallback ? " · fallback" : ""}</span>
              </div>
            </div>

            {reoptimizing && <p className="hint">Đang tính lại lịch…</p>}

            <GanttEditor
              schedule={result.schedule}
              fixedHours={fixedHours}
              appliances={appliances}
              onPinnedChange={handlePinnedChange}
              onFixedHoursChange={handleFixedHoursChange}
              disabled={reoptimizing}
            />
            <p className="hint">
              Tải linh hoạt: kéo khối để tối ưu lại. Tải cố định: bấm ô giờ để bật/tắt theo nhu cầu
              thật (có thể nhiều khung giờ rời nhau).
            </p>

            {peak && (
              <div className={"safety " + (overload ? "safety--bad" : "safety--ok")}>
                {overload
                  ? `Quá tải: ${fmt(peak.peakW)}W cùng lúc lúc ${peak.peakHour}h (> ${fmt(SAFE_POWER_W)}W) — ${peak.names.join(", ")}`
                  : `An toàn công suất: cao nhất ${fmt(peak.peakW)}W lúc ${peak.peakHour}h, dưới ngưỡng ${fmt(SAFE_POWER_W)}W`}
              </div>
            )}

            <ExplainSection explainText={explainText} explainLoading={explainLoading} onExplain={handleExplain} />

            <div className="qaoa">
              <button className="btn" onClick={handleAnalyze} disabled={analyzing}>
                {analyzing ? "Đang chạy QAOA nhiều cấu hình…" : "Phân tích thuật toán lượng tử"}
              </button>
              {analysis && (
                <div className="qaoa-body">
                  <p className="hint">
                    QUBO: <strong>{analysis.num_variables} qubit</strong> ({analysis.num_appliances} thiết bị linh hoạt)
                    · Nghiệm tối ưu toàn cục (brute-force): <strong>{Number(analysis.brute_force_energy).toLocaleString("vi-VN")}</strong>
                  </p>
                  <table className="qaoa-table">
                    <thead>
                      <tr><th>reps</th><th>maxiter</th><th>Thời gian (s)</th><th>Năng lượng</th><th>Đạt tối ưu?</th></tr>
                    </thead>
                    <tbody>
                      {analysis.configs.map((c, i) => (
                        <tr key={i}>
                          <td>{c.reps}</td><td>{c.maxiter}</td><td>{c.runtime_seconds.toFixed(2)}</td>
                          <td>{c.error ? "—" : Number(c.energy).toLocaleString("vi-VN")}</td>
                          <td>{c.matches_global_optimum
                            ? <span className="tag tag--green">Có</span>
                            : <span className="tag tag--yellow">Chưa</span>}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
