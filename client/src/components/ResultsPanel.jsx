import { useState, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import { useCountUp } from "../useCountUp";
import GanttEditor from "./GanttEditor";
import { sendAlert } from "../api";
import { supabase } from "../supabaseClient";
import ExplainSection from "./ExplainSection";
import BillChart from "./BillChart";
import html2pdf from "html2pdf.js";

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
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulatedTime, setSimulatedTime] = useState(0);
  const [alertEmail, setAlertEmail] = useState("");
  const [alertPhone, setAlertPhone] = useState("");
  const [alertStatus, setAlertStatus] = useState(null);
  const [sendingAlert, setSendingAlert] = useState(false);

  // Ngưỡng công suất đồng thời an toàn (W), theo role — backend trả về trong /optimize.
  // Lịch sử lưu (rehydrate) không có trường này nên fallback về mặc định hộ gia đình 5000W.
  const safePowerW = result.power_threshold_w ?? 5000;

  // Auto-explain on overload
  const peak = computePeakPower(result.schedule, fixedHours, appliances);
  const overload = peak.peakW > safePowerW;

  useEffect(() => {
    if (overload && !explainText && !explainLoading) {
      onExplain();
    }
  }, [overload, explainText, explainLoading, onExplain]);

  // IoT Simulator Timer
  useEffect(() => {
    let interval;
    if (isSimulating) {
      interval = setInterval(() => {
        setSimulatedTime((prev) => (prev >= 23 ? 0 : prev + 1));
      }, 800); // 0.8s per hour
    } else {
      setSimulatedTime(0);
    }
    return () => clearInterval(interval);
  }, [isSimulating]);

  const handleSendAlert = async () => {
    setSendingAlert(true);
    try {
      await sendAlert({
        email: alertEmail || null,
        phone: alertPhone || null,
        bill_before: result.bill_before_vnd,
        bill_after: result.bill_after_vnd,
        savings_percent: result.savings_percent
      });
      setAlertStatus({ type: "success", msg: "Cảnh báo đã được gửi thành công!" });
    } catch (err) {
      setAlertStatus({ type: "error", msg: "Lỗi gửi cảnh báo. Vui lòng thử lại." });
    }
    setSendingAlert(false);
    setTimeout(() => setAlertStatus(null), 4000);
  };

  const handleExportPDF = async () => {
    // Lấy email user từ phiên Supabase để hiển thị trên báo cáo
    let username = "Khách hàng";
    try {
      const { data } = await supabase.auth.getSession();
      username = data.session?.user?.email || "Khách hàng";
    } catch (e) {}

    const element = document.getElementById("pdf-content-area");
    
    // Tạo header cho PDF
    const header = document.createElement("div");
    header.id = "pdf-temp-header";
    header.innerHTML = `
      <div style="text-align: center; margin-bottom: 20px;">
        <h1 style="color: #000; margin-bottom: 5px; font-size: 24px;">BÁO CÁO TỐI ƯU HÓA NĂNG LƯỢNG</h1>
        <p style="color: #333; margin-top: 0; font-size: 14px;"><strong>Khách hàng:</strong> ${username} | <strong>Ngày xuất báo cáo:</strong> ${new Date().toLocaleDateString('vi-VN')}</p>
        <hr style="border-color: #ccc; margin-top: 15px;"/>
      </div>
    `;
    element.insertBefore(header, element.firstChild);

    // Kích hoạt chế độ in (để CSS xử lý màu sắc đen/trắng)
    document.body.classList.add("pdf-export-mode");

    const opt = {
      margin:       10,
      filename:     'q-smartenergy-report.pdf',
      image:        { type: 'jpeg', quality: 0.98 },
      html2canvas:  { scale: 2, useCORS: true, backgroundColor: '#ffffff' },
      jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };
    
    // Chờ html2pdf hoàn thành
    await html2pdf().set(opt).from(element).save();

    // Dọn dẹp DOM
    document.body.classList.remove("pdf-export-mode");
    element.removeChild(header);
  };

  // Tính toán ESG (Môi trường)
  const { kwhShifted, co2Reduced, treesPlanted } = useMemo(() => {
    let shifted = 0;
    appliances.forEach(a => {
      if (a.is_flexible) {
        const optimalHour = result.schedule[a.name];
        // Nếu dời khỏi giờ cao điểm (17, 18, 19) thì tính là tiết kiệm CO2
        if (optimalHour !== 17 && optimalHour !== 18 && optimalHour !== 19) {
          shifted += (a.power_w / 1000) * a.duration_hours * 30; // monthly
        }
      }
    });
    const co2 = shifted * 0.8; // 0.8 kg CO2/kWh cho điện cao điểm (thường là than/diesel)
    const trees = co2 / 22; // 1 cây xanh trưởng thành hấp thụ ~22kg CO2/năm
    return { kwhShifted: shifted, co2Reduced: co2, treesPlanted: trees };
  }, [appliances, result.schedule]);

  return (
    <motion.div
      className="section-card results-section glass-panel"
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2>Kết quả</h2>
        <button 
          className="btn-primary" 
          onClick={handleExportPDF}
          style={{ background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.2)" }}
        >
          ⬇️ Xuất Báo cáo PDF
        </button>
      </div>
      
      <div id="pdf-content-area">
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
          Đang tính lại lịch...
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
        simulatedTime={simulatedTime}
      />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.4rem" }}>
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
          Tải linh hoạt: kéo khối để tối ưu lại. Tải cố định: bấm vào ô giờ để bật/tắt.
        </p>
        <button 
          className="btn-primary" 
          onClick={() => setIsSimulating(!isSimulating)}
          style={{ padding: "0.3rem 0.8rem", fontSize: "0.8rem", background: isSimulating ? "var(--error)" : "var(--quantum)" }}
        >
          {isSimulating ? "Dừng giả lập" : "Chạy giả lập (IoT)"}
        </button>
      </div>

      {/* Power-overload safety check (+8đ Mức Dễ): cảnh báo công suất đồng thời */}
      <div
        className={overload ? "alert-critical" : ""}
        style={{
              marginTop: "1rem", padding: "0.6rem 0.9rem", borderRadius: 8,
              fontSize: "0.85rem", fontWeight: 600,
              background: overload ? "rgba(239, 68, 68, 0.1)" : "rgba(16, 185, 129, 0.1)",
              color: overload ? "#ef4444" : "var(--energy)",
              border: `1px solid ${overload ? "rgba(239, 68, 68, 0.3)" : "rgba(16, 185, 129, 0.3)"}`,
              boxShadow: overload ? "0 0 15px rgba(239, 68, 68, 0.2)" : "0 0 15px var(--energy-glow)",
            }}
          >
          {overload
            ? `CẢNH BÁO CHÁY NỔ: ${peak.peakW.toLocaleString("vi-VN")}W cùng lúc lúc ${peak.peakHour}h (> ngưỡng ${safePowerW.toLocaleString("vi-VN")}W) — ${peak.names.join(", ")}`
            : `An toàn công suất: cao nhất ${peak.peakW.toLocaleString("vi-VN")}W lúc ${peak.peakHour}h, dưới ngưỡng ${safePowerW.toLocaleString("vi-VN")}W`}
        </div>
        {overload && (
          <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: "0.4rem", fontWeight: 400 }}>
            Lưu ý giới hạn: bộ tối ưu chỉ phát hiện các thiết bị linh hoạt trùng đúng GIỜ BẮT ĐẦU,
            chưa bắt hết trường hợp khung giờ chồng lấn khác giờ bắt đầu và chưa cộng dồn tải các
            thiết bị cố định (tủ lạnh, điều hòa...). Vui lòng kiểm tra thủ công với hệ thống máy móc
            lớn — đặc biệt tài khoản doanh nghiệp.
          </p>
        )}



      {/* Recharts Area and Pie Chart */}
      <BillChart appliances={appliances} result={result} fixedHours={fixedHours} />

      {/* ESG Report - Báo cáo Môi trường */}
      <div className="section-card glass-panel" style={{ marginTop: "1.5rem", background: "rgba(16, 185, 129, 0.05)", borderColor: "rgba(16, 185, 129, 0.2)" }}>
        <h3 style={{ marginTop: 0, marginBottom: "1rem", color: "var(--energy)" }}>🌍 Báo cáo Môi trường (ESG)</h3>
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
          Thuật toán Lượng tử đã dời các thiết bị tiêu thụ lớn khỏi giờ cao điểm (thời điểm lưới điện phải chạy thêm máy phát điện Diesel/Than ô nhiễm).
        </p>
        <div style={{ display: "flex", gap: "2rem", flexWrap: "wrap" }}>
          <div>
            <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--text-muted)" }}>Điện năng dịch chuyển:</p>
            <p style={{ margin: "0.2rem 0", fontSize: "1.5rem", fontWeight: "bold", color: "#fff" }}>{kwhShifted.toFixed(1)} <span style={{fontSize: "1rem"}}>kWh/tháng</span></p>
          </div>
          <div>
            <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--text-muted)" }}>Khí thải CO2 cắt giảm:</p>
            <p style={{ margin: "0.2rem 0", fontSize: "1.5rem", fontWeight: "bold", color: "var(--energy)" }}>↓ {co2Reduced.toFixed(1)} <span style={{fontSize: "1rem"}}>kg CO2</span></p>
          </div>
          <div>
            <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--text-muted)" }}>Tương đương trồng mới:</p>
            <p style={{ margin: "0.2rem 0", fontSize: "1.5rem", fontWeight: "bold", color: "#10B981" }}>🌲 {treesPlanted.toFixed(1)} <span style={{fontSize: "1rem"}}>cây xanh</span></p>
          </div>
          </div>
        </div>

      {/* Storytelling section (Insight & Lời khuyên) */}
      <div style={{ marginTop: "1.5rem" }}>
        <ExplainSection
          explainText={explainText}
          explainLoading={explainLoading}
          onExplain={onExplain}
        />
      </div>

      </div> {/* Đóng thẻ id="pdf-content-area" */}

      {/* Alert Center */}
      <div className="section-card glass-panel" style={{ marginTop: "1.5rem" }}>
        <h3 style={{ marginTop: 0, marginBottom: "0.5rem", color: "var(--quantum)" }}>Cảnh báo Tiêu thụ (Email/SMS)</h3>
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
          Hệ thống sẽ tự động gửi email báo cáo tối ưu nếu hóa đơn vượt ngưỡng hoặc công suất bị quá tải.
        </p>
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "center" }}>
          <input 
            type="email" 
            placeholder="Nhập Email nhận báo cáo..." 
            value={alertEmail}
            onChange={(e) => setAlertEmail(e.target.value)}
            style={{ padding: "0.5rem", borderRadius: "6px", background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.1)", color: "#fff", flex: "1 1 200px" }}
          />
          <input 
            type="text" 
            placeholder="Nhập SĐT (Mock SMS)..." 
            value={alertPhone}
            onChange={(e) => setAlertPhone(e.target.value)}
            style={{ padding: "0.5rem", borderRadius: "6px", background: "rgba(0,0,0,0.3)", border: "1px solid rgba(255,255,255,0.1)", color: "#fff", flex: "1 1 150px" }}
          />
          <button 
            className="btn-primary" 
            onClick={handleSendAlert} 
            disabled={sendingAlert || (!alertEmail && !alertPhone)}
          >
            {sendingAlert ? "Đang gửi..." : "Gửi báo cáo"}
          </button>
        </div>
        {alertStatus && (
          <div style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: alertStatus.type === "error" ? "var(--error)" : "var(--energy)" }}>
            {alertStatus.msg}
          </div>
        )}
      </div>


      {/* QAOA hyperparameter analysis (III.3 — evidence of quantum tuning) */}
      <div style={{ marginTop: "1.5rem", borderTop: "1px solid #e5e7eb", paddingTop: "1rem" }}>
        <button className="btn-primary" onClick={onAnalyze} disabled={analyzing}>
          {analyzing ? "Đang chạy QAOA nhiều cấu hình..." : "Phân tích thuật toán lượng tử"}
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
