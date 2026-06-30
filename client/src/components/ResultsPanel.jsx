import { motion } from "framer-motion";
import { useCountUp } from "../useCountUp";
import GanttEditor from "./GanttEditor";
import ExplainSection from "./ExplainSection";

// Ngưỡng công suất đồng thời an toàn của hộ gia đình (khớp power_threshold_w trong QUBO H_power).
const SAFE_POWER_W = 5000;

// Tính công suất đồng thời (W) từng giờ từ giờ chạy thật của mọi thiết bị: tải linh hoạt ở giờ
// được tối ưu (1 khối liên tục theo thời lượng), tải cố định ở các giờ người dùng bật trên lưới
// (fixedHours: {tên: [giờ...]}). Trả { peakW, peakHour, names } của giờ đỉnh.
function computePeakPower(flexibleSchedule, fixedHours, appliances) {
  const watts = Array(24).fill(0);
  const atHour = Array.from({ length: 24 }, () => []);
  const add = (name, eff, hour) => {
    watts[hour] += eff;
    atHour[hour].push(name);
  };
  for (const a of appliances) {
    const eff = a.power_w * (a.quantity ?? 1);
    if (a.is_flexible) {
      const h = flexibleSchedule[a.name];
      if (h == null) continue;
      const len = Math.max(1, Math.ceil(a.duration_hours));
      for (let k = 0; k < len; k++) add(a.name, eff, (h + k) % 24);
    } else {
      for (const hour of fixedHours[a.name] ?? []) add(a.name, eff, hour);
    }
  }
  let peakHour = 0;
  for (let h = 1; h < 24; h++) if (watts[h] > watts[peakHour]) peakHour = h;
  return { peakW: watts[peakHour], peakHour, names: [...new Set(atHour[peakHour])] };
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

/**
 * Optimization result card: animated bill comparison, the interactive Gantt
 * editor, the power-overload safety check, the bill chart, the Gemini
 * explanation, and the QAOA hyperparameter analysis. Rendered inside an
 * AnimatePresence so it animates in/out as results arrive.
 */
export default function ResultsPanel({
  result,
  reoptimizing,
  fixedHours,
  appliances,
  onPinnedChange,
  onFixedHoursChange,
  analysis,
  analyzing,
  onAnalyze,
  explainText,
  explainLoading,
  onExplain,
}) {
  return (
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

      {/* Interactive Gantt — flexible appliances draggable at QAOA hour, fixed appliances
          shown at their realistic usage windows (possibly several per day) */}
      <GanttEditor
        schedule={result.schedule}
        fixedHours={fixedHours}
        appliances={appliances}
        onPinnedChange={onPinnedChange}
        onFixedHoursChange={onFixedHoursChange}
        disabled={reoptimizing}
      />
      <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "0.4rem" }}>
        ⟳ Tải linh hoạt: kéo khối để tối ưu lại. ⠿ Tải cố định: bấm vào ô giờ để bật/tắt
        theo nhu cầu thật (có thể nhiều khung giờ rời nhau, vd điều hòa 0-3h rồi 10-13h).
      </p>

      {/* Power-overload safety check (+8đ Mức Dễ): cảnh báo công suất đồng thời */}
      {(() => {
        const peak = computePeakPower(
          result.schedule,
          fixedHours,
          appliances
        );
        const overload = peak.peakW > SAFE_POWER_W;
        return (
          <div
            style={{
              marginTop: "1rem", padding: "0.6rem 0.9rem", borderRadius: 8,
              fontSize: "0.85rem", fontWeight: 600,
              background: overload ? "#FEF2F2" : "#F0FDF4",
              color: overload ? "#B91C1C" : "var(--teal)",
              border: `1px solid ${overload ? "#FCA5A5" : "#86EFAC"}`,
            }}
          >
            {overload
              ? `⚠️ Cảnh báo quá tải: ${peak.peakW.toLocaleString("vi-VN")}W cùng lúc lúc ${peak.peakHour}h (> ngưỡng ${SAFE_POWER_W.toLocaleString("vi-VN")}W) — ${peak.names.join(", ")}`
              : `✓ An toàn công suất: cao nhất ${peak.peakW.toLocaleString("vi-VN")}W lúc ${peak.peakHour}h, dưới ngưỡng ${SAFE_POWER_W.toLocaleString("vi-VN")}W`}
          </div>
        );
      })()}

      {/* Bill comparison chart (static PNG, unchanged) */}
      {result.bill_chart_png && (
        <img
          src={`data:image/png;base64,${result.bill_chart_png}`}
          alt="So sánh hóa đơn điện"
          style={{ marginTop: "1rem" }}
        />
      )}

      {/* Storytelling section */}
      <ExplainSection
        explainText={explainText}
        explainLoading={explainLoading}
        onExplain={onExplain}
      />

      {/* QAOA hyperparameter analysis (III.3 — evidence of quantum tuning) */}
      <div style={{ marginTop: "1.5rem", borderTop: "1px solid #e5e7eb", paddingTop: "1rem" }}>
        <button onClick={onAnalyze} disabled={analyzing}>
          {analyzing ? "⏳ Đang chạy QAOA nhiều cấu hình..." : "🔬 Phân tích thuật toán lượng tử"}
        </button>
        {analysis && (
          <div style={{ marginTop: "0.75rem" }}>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
              QUBO: <strong style={{ color: "var(--indigo)" }}>{analysis.num_variables} qubit</strong>
              {" "}({analysis.num_appliances} thiết bị linh hoạt) · Nghiệm tối ưu toàn cục (brute-force):
              {" "}<strong>{Number(analysis.brute_force_energy).toLocaleString("vi-VN")}</strong>
            </p>
            <table style={{ fontSize: "0.82rem" }}>
              <thead>
                <tr>
                  <th>reps</th><th>maxiter</th><th>Thời gian (s)</th>
                  <th>Năng lượng</th><th>Đạt tối ưu?</th>
                </tr>
              </thead>
              <tbody>
                {analysis.configs.map((c, i) => (
                  <tr key={i}>
                    <td>{c.reps}</td>
                    <td>{c.maxiter}</td>
                    <td>{c.runtime_seconds.toFixed(2)}</td>
                    <td>{c.error ? "—" : Number(c.energy).toLocaleString("vi-VN")}</td>
                    <td style={{ color: c.matches_global_optimum ? "var(--teal)" : "var(--gold)", fontWeight: 600 }}>
                      {c.matches_global_optimum ? "✓ Có" : "✗ Chưa"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: "0.4rem" }}>
              Tăng reps/maxiter giúp QAOA tiệm cận nghiệm tối ưu toàn cục, đổi lại thời gian chạy lâu hơn —
              đây là trade-off tuning tham số lượng tử.
            </p>
          </div>
        )}
      </div>
    </motion.div>
  );
}
