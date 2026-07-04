import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useAppData } from "../AppData";
import { getMe, fetchExternalData } from "../api";
import { WEATHER_OPTIONS } from "../forecastConfig";
import { accountPowerThresholdW } from "../scheduleUtils";
import GanttEditor from "../components/GanttEditor";
import ExplainSection from "../components/ExplainSection";

const WEATHER_ICON = { sunny: "☀️", cloudy: "⛅", rainy: "🌧️" };
const badgeStyle = { fontSize: "0.9rem", padding: "0.5rem 0.9rem", textTransform: "none", letterSpacing: 0 };

// Multi-objective optimize sliders (0-100%). key must match the AppData weights state.
const WEIGHT_SLIDERS = [
  { key: "cost", icon: "💰", label: "Tiết kiệm chi phí" },
  { key: "comfort", icon: "🕒", label: "Tiện lợi (gần giờ quen)" },
  { key: "solar", icon: "☀️", label: "Ưu tiên điện mặt trời" },
];

// Giải thích tức thời (không gọi API) cho tổ hợp trọng số hiện tại — dựa vào trọng số nào đang cao nhất.
const WEIGHT_EXPLAIN = {
  cost: { label: "Tiết kiệm chi phí", effect: "chạy vào giờ điện rẻ nhất có thể, dù có thể lệch xa giờ bạn quen dùng" },
  comfort: { label: "Tiện lợi", effect: "chạy gần giờ bạn quen dùng hơn, có thể không phải giờ điện rẻ nhất" },
  solar: { label: "Điện mặt trời", effect: "dồn vào khung giờ nắng để tự tiêu thụ, dù có thể không rẻ nhất hoặc không đúng giờ quen" },
};

function explainWeights(weights) {
  const max = Math.max(weights.cost, weights.comfort, weights.solar);
  const top = ["cost", "comfort", "solar"].filter((k) => weights[k] === max);

  if (top.length === 3) {
    return "Ba ưu tiên đang cân bằng → lịch tối ưu sẽ dung hòa giữa chi phí, tiện lợi và điện mặt trời.";
  }
  if (top.length === 2) {
    const labels = top.map((k) => WEIGHT_EXPLAIN[k].label).join(" & ");
    const effects = top.map((k) => WEIGHT_EXPLAIN[k].effect).join("; đồng thời ");
    return `Ưu tiên ${labels} cao ngang nhau → thiết bị sẽ ${effects}.`;
  }
  const { label, effect } = WEIGHT_EXPLAIN[top[0]];
  return `Ưu tiên ${label} cao nhất → thiết bị sẽ ${effect}.`;
}

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
    weights, handleWeightsChange,
    result, reoptimizing, fixedHours, appliances, handlePinnedChange, handleFixedHoursChange,
    durationOverrides, clearDurationOverrides,
    analysis, analyzing, handleAnalyze, explainText, explainLoading, handleExplain,
    todayISO, tomorrowISO, maxDateISO, selectedDate, changeDate, forecastAvailable,
  } = useAppData();

  // Business bỏ bước "Dự báo" (Bước 2) nên tab này là Bước 2 với họ, Bước 3 với hộ gia đình.
  // Cũng là nguồn threshold công suất thật (role + business_profile) cho banner an toàn bên dưới.
  const [me, setMe] = useState(null);
  useEffect(() => {
    getMe()
      .then(setMe)
      .catch(() => setMe(null));
  }, []);
  const role = me?.role ?? null;

  // URL do người dùng nhập để lấy thêm thông tin đầu vào (vd môi trường/kế hoạch phụ tải).
  // v1: chỉ fetch + hiển thị read-only, chưa nối vào công thức QUBO.
  const [externalUrl, setExternalUrl] = useState("");
  const [externalData, setExternalData] = useState(null);
  const [externalError, setExternalError] = useState(null);
  const [externalLoading, setExternalLoading] = useState(false);

  async function handleFetchExternalData() {
    setExternalLoading(true);
    setExternalError(null);
    setExternalData(null);
    try {
      const res = await fetchExternalData(externalUrl);
      if (res.ok) setExternalData(res.data);
      else setExternalError(res.error);
    } catch {
      setExternalError("Không thể lấy dữ liệu từ URL này. Vui lòng thử lại.");
    } finally {
      setExternalLoading(false);
    }
  }

  // Ngưỡng công suất đồng thời an toàn (W), theo role — backend trả về trong /optimize.
  // Lịch sử lưu (rehydrate) không có trường này, nên fallback về threshold tính từ role/business_profile
  // của chính tài khoản (accountPowerThresholdW), khớp công thức backend, thay vì hardcode 5000W.
  const safePowerW = result?.power_threshold_w ?? accountPowerThresholdW(me);
  const peak = result ? peakPower(result.schedule, fixedHours, appliances) : null;
  const overload = peak && peak.peakW > safePowerW;
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
        <p className="eyebrow">{role === "business" ? "Bước 2" : "Bước 3"}</p>
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
        {Object.keys(durationOverrides).length > 0 && (
          <div className="ml-override">
            <span>⚙️ Đang tối ưu với <strong>thời lượng dự báo (ML)</strong> cho {Object.keys(durationOverrides).length} thiết bị, thay cho thời lượng thật.</span>
            <button className="btn" onClick={clearDurationOverrides} disabled={loading}>Gỡ</button>
          </div>
        )}
        {showAssumedSunny && (
          <div className="safety" style={{ background: "var(--pale-yellow-bg)", color: "var(--pale-yellow-fg)", borderColor: "transparent" }}>
            ⚠️ Chưa có dữ liệu thời tiết chính xác cho ngày {ddmm(selectedDate)} (quá xa so với dự báo).
            Kết quả dùng giả định trời nắng và có thể sai lệch.
          </div>
        )}
        {error && <p className="form-error">{error}</p>}

        <div className="field" style={{ marginTop: "1rem" }}>
          <span>URL dữ liệu bổ sung (tuỳ chọn)</span>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <input
              type="url"
              placeholder="https://..."
              value={externalUrl}
              onChange={(e) => setExternalUrl(e.target.value)}
              style={{ flex: "1 1 260px" }}
            />
            <button
              className="btn"
              onClick={handleFetchExternalData}
              disabled={externalLoading || !externalUrl}
            >
              {externalLoading ? "Đang lấy…" : "Lấy dữ liệu"}
            </button>
          </div>
          <p className="hint">
            Dán URL trả về dữ liệu JSON (vd môi trường, kế hoạch phụ tải) để tham khảo thêm. Chỉ hiển thị,
            chưa được dùng để tính lịch tối ưu.
          </p>
          {externalError && <p className="form-error">{externalError}</p>}
          {externalData && (
            <div className="tag" style={{ ...badgeStyle, display: "block", whiteSpace: "pre-wrap", wordBreak: "break-word", textAlign: "left" }}>
              <strong>Thông tin bổ sung:</strong>
              <pre style={{ margin: "0.4rem 0 0", whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: "0.85rem" }}>
                {JSON.stringify(externalData, null, 2)}
              </pre>
            </div>
          )}
        </div>
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
                <span className="bill-note">= chạy tải linh hoạt vào giờ bất lợi nhất trong khung cho phép</span>
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

            <div className="opt-weights">
              <div>
                <span className="opt-weights-title">Ưu tiên tối ưu</span>
                <p className="opt-weights-sub">
                  Kéo để cân bằng giữa hóa đơn rẻ nhất, chạy gần giờ quen và tận dụng điện mặt trời —
                  lịch và hóa đơn tự cập nhật ngay sau khi bạn thả.
                </p>
              </div>
              {WEIGHT_SLIDERS.map((s) => (
                <label key={s.key} className="weight-slider">
                  <span className="weight-slider-label">{s.icon} {s.label}</span>
                  <input
                    type="range" min={0} max={100} step={5}
                    value={weights[s.key]}
                    onChange={(e) => handleWeightsChange({ ...weights, [s.key]: Number(e.target.value) })}
                    disabled={reoptimizing}
                    aria-label={s.label}
                  />
                  <span className="weight-slider-val">{weights[s.key]}%</span>
                </label>
              ))}
              <p className="hint weight-explain">{explainWeights(weights)}</p>
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
                  ? `Quá tải: ${fmt(peak.peakW)}W cùng lúc lúc ${peak.peakHour}h (> ${fmt(safePowerW)}W) — ${peak.names.join(", ")}`
                  : `An toàn công suất: cao nhất ${fmt(peak.peakW)}W lúc ${peak.peakHour}h, dưới ngưỡng ${fmt(safePowerW)}W`}
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
