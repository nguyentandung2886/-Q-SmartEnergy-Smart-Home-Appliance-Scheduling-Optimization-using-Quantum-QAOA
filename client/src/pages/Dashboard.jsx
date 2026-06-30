import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  createAppliance, deleteAppliance, getAppliances,
  optimize as apiOptimize, updateAppliance,
} from "../api";
import { useAuth } from "../AuthContext";
import { useCountUp } from "../useCountUp";

const WEATHER_OPTIONS = [
  { value: "sunny", label: "☀️ Nắng" },
  { value: "cloudy", label: "⛅ Có mây" },
  { value: "rainy", label: "🌧 Mưa" },
];

function ApplianceRow({ appliance, onSave, onDelete }) {
  const [power, setPower] = useState(appliance.power_w);
  const [duration, setDuration] = useState(appliance.duration_hours);

  function save() {
    if (Number(power) !== appliance.power_w || Number(duration) !== appliance.duration_hours) {
      onSave(appliance.id, { ...appliance, power_w: Number(power), duration_hours: Number(duration) });
    }
  }

  return (
    <tr>
      <td>{appliance.name}</td>
      <td>
        <input
          type="number" value={power} min={1}
          onChange={(e) => setPower(e.target.value)}
          onBlur={save}
        />
      </td>
      <td>
        <input
          type="number" value={duration} min={0.1} step={0.1}
          onChange={(e) => setDuration(e.target.value)}
          onBlur={save}
        />
      </td>
      <td style={{ color: appliance.is_flexible ? "var(--teal)" : "var(--text-muted)" }}>
        {appliance.is_flexible ? "Linh hoạt" : "Cố định"}
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
  const [error, setError] = useState("");
  const [newName, setNewName] = useState("");
  const [newPower, setNewPower] = useState(100);
  const [newDuration, setNewDuration] = useState(1);
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

  async function handleAdd(e) {
    e.preventDefault();
    await createAppliance({
      name: newName, power_w: Number(newPower), duration_hours: Number(newDuration),
      candidate_hours: [], is_flexible: false,
    });
    setNewName(""); setNewPower(100); setNewDuration(1);
    await loadAppliances();
  }

  async function handleOptimize() {
    setLoading(true); setError(""); setResult(null);
    try {
      const data = await apiOptimize({ day_of_month: Number(dayOfMonth), weather_condition: weather, use_quantum: true });
      setResult(data);
    } catch {
      setError("Lỗi khi tối ưu hóa. Kiểm tra backend đã chạy chưa?");
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() { logout(); navigate("/login"); }

  const totalKwh = appliances.reduce((sum, a) => sum + a.power_w / 1000 * a.duration_hours * 30, 0);

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
            <tr><th>Tên thiết bị</th><th>Công suất (W)</th><th>Giờ dùng</th><th>Loại</th><th></th></tr>
          </thead>
          <tbody>
            {appliances.map((a) => (
              <ApplianceRow key={a.id} appliance={a} onSave={handleSave} onDelete={handleDelete} />
            ))}
          </tbody>
        </table>
        <form onSubmit={handleAdd} className="add-form">
          <input placeholder="Tên thiết bị mới" value={newName} onChange={(e) => setNewName(e.target.value)} required />
          <input type="number" placeholder="Công suất (W)" value={newPower} min={1} onChange={(e) => setNewPower(e.target.value)} required />
          <input type="number" placeholder="Giờ/ngày" value={newDuration} min={0.1} step={0.1} onChange={(e) => setNewDuration(e.target.value)} required />
          <button type="submit">+ Thêm thiết bị</button>
        </form>
      </div>

      {/* Optimize controls */}
      <div className="section-card">
        <h2>Tối ưu hóa lịch chạy</h2>
        <div className="optimize-controls">
          <label>
            Ngày trong tháng
            <input type="number" min={1} max={30} value={dayOfMonth} onChange={(e) => setDayOfMonth(e.target.value)} />
          </label>
          <label>
            Thời tiết hôm nay
            <select value={weather} onChange={(e) => setWeather(e.target.value)}>
              {WEATHER_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
          <motion.button
            className="btn-optimize"
            onClick={handleOptimize}
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
              Solver: {result.solver_used}{result.used_fallback ? " (dùng fallback cổ điển)" : ""}
            </p>
            {result.gantt_chart_png && (
              <img src={`data:image/png;base64,${result.gantt_chart_png}`} alt="Lịch chạy thiết bị tối ưu" />
            )}
            {result.bill_chart_png && (
              <img src={`data:image/png;base64,${result.bill_chart_png}`} alt="So sánh hóa đơn điện" style={{ marginTop: "1rem" }} />
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
