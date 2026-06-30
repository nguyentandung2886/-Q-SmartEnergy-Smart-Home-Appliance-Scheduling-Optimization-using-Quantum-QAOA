import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getSchedules } from "../api";

export default function History() {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    getSchedules()
      .then(setSchedules)
      .finally(() => setLoading(false));
  }, []);

  const WEATHER_LABELS = { sunny: "☀️ Nắng", cloudy: "⛅ Có mây", rainy: "🌧 Mưa" };

  return (
    <motion.div
      className="history-page"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      transition={{ duration: 0.25 }}
    >
      <header className="dashboard-header">
        <h1>Lịch sử tối ưu hóa</h1>
        <button onClick={() => navigate("/dashboard")}>← Quay lại</button>
      </header>

      {loading ? (
        <p style={{ color: "var(--text-muted)", textAlign: "center", marginTop: "2rem" }}>
          Đang tải...
        </p>
      ) : schedules.length === 0 ? (
        <div className="section-card" style={{ textAlign: "center", color: "var(--text-muted)" }}>
          <p>Chưa có lần tối ưu nào. Quay lại Dashboard và thử nhé!</p>
        </div>
      ) : (
        <div className="section-card">
          <table>
            <thead>
              <tr>
                <th>Thời gian</th>
                <th>Ngày</th>
                <th>Thời tiết</th>
                <th>Solver</th>
                <th>Trước (đ)</th>
                <th>Sau (đ)</th>
                <th>Tiết kiệm</th>
              </tr>
            </thead>
            <tbody>
              {schedules.map((s) => (
                <tr key={s.id}>
                  <td>{new Date(s.created_at).toLocaleString("vi-VN")}</td>
                  <td>Ngày {s.day_of_month}</td>
                  <td>{WEATHER_LABELS[s.weather_condition] ?? s.weather_condition}</td>
                  <td style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    {s.solver_used}{s.used_fallback ? "*" : ""}
                  </td>
                  <td>{s.bill_before_vnd.toLocaleString("vi-VN")}</td>
                  <td style={{ color: "var(--teal)", fontWeight: 600 }}>
                    {s.bill_after_vnd.toLocaleString("vi-VN")}
                  </td>
                  <td style={{ color: "var(--gold)", fontWeight: 700 }}>
                    ↓ {s.savings_percent.toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
            * fallback: QAOA không hội tụ, dùng brute-force cổ điển
          </p>
        </div>
      )}
    </motion.div>
  );
}
