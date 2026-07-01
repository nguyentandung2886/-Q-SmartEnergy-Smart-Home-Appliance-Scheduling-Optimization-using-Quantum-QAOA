import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getSchedules } from "../api";

const WEATHER_LABELS = { sunny: "Nắng", cloudy: "Có mây", rainy: "Mưa" };

export default function History() {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    getSchedules().then(setSchedules).finally(() => setLoading(false));
  }, []);

  return (
    <motion.div
      className="history-page"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <div className="history-head">
        <div>
          <p className="eyebrow">Nhật ký</p>
          <h1>Lịch sử tối ưu hóa</h1>
        </div>
        <button className="btn" onClick={() => navigate("/app/dashboard")}>← Quay lại</button>
      </div>

      {loading ? (
        <p className="hint" style={{ textAlign: "center", marginTop: "2rem" }}>Đang tải…</p>
      ) : schedules.length === 0 ? (
        <div className="card empty-state">
          <p>Chưa có lần tối ưu nào.</p>
          <button className="btn-ink" onClick={() => navigate("/app/optimize")}>Chạy tối ưu hóa</button>
        </div>
      ) : (
        <div className="card">
          <table>
            <thead>
              <tr>
                <th>Thời gian</th><th>Ngày</th><th>Thời tiết</th><th>Solver</th>
                <th>Trước (đ)</th><th>Sau (đ)</th><th>Tiết kiệm</th>
              </tr>
            </thead>
            <tbody>
              {schedules.map((s) => (
                <tr key={s.id}>
                  <td>{new Date(s.created_at).toLocaleString("vi-VN")}</td>
                  <td>Ngày {s.day_of_month}</td>
                  <td>{WEATHER_LABELS[s.weather_condition] ?? s.weather_condition}</td>
                  <td className="mono" style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    {s.solver_used}{s.used_fallback ? "*" : ""}
                  </td>
                  <td>{s.bill_before_vnd.toLocaleString("vi-VN")}</td>
                  <td style={{ color: "var(--pale-green-fg)", fontWeight: 600 }}>
                    {s.bill_after_vnd.toLocaleString("vi-VN")}
                  </td>
                  <td style={{ color: "var(--accent)", fontWeight: 600 }}>
                    ↓ {s.savings_percent.toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="hint">* fallback: QAOA không hội tụ, dùng brute-force cổ điển</p>
        </div>
      )}
    </motion.div>
  );
}
