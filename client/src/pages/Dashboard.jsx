import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createAppliance, deleteAppliance, getAppliances,
  optimize as apiOptimize, updateAppliance,
} from "../api";
import { useAuth } from "../AuthContext";

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
    const data = await getAppliances();
    setAppliances(data);
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
    <div className="dashboard">
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
          <button className="btn-optimize" onClick={handleOptimize} disabled={loading}>
            {loading ? "⏳ Đang tối ưu..." : "⚡ Tối ưu hóa"}
          </button>
        </div>
        {error && <p className="auth-error" style={{ marginTop: "0.75rem" }}>{error}</p>}
      </div>

      {/* Results */}
      {result && (
        <div className="section-card results-section">
          <h2>Kết quả</h2>
          <div className="bill-numbers">
            <div className="bill-item">
              <strong>{result.bill_before_vnd.toLocaleString("vi-VN")}đ</strong>
              Hóa đơn trước
            </div>
            <div style={{ fontSize: "1.5rem", alignSelf: "center" }}>→</div>
            <div className="bill-item">
              <strong style={{ color: "var(--teal)" }}>{result.bill_after_vnd.toLocaleString("vi-VN")}đ</strong>
              Sau tối ưu hóa
            </div>
            <div className="bill-item">
              <strong className="savings-highlight">↓ {result.savings_percent.toFixed(1)}%</strong>
              Tiết kiệm
            </div>
          </div>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
            Solver: {result.solver_used}{result.used_fallback ? " (dùng fallback cổ điển)" : ""}
          </p>
          {result.gantt_chart_png && (
            <img src={`data:image/png;base64,${result.gantt_chart_png}`} alt="Lịch chạy thiết bị tối ưu" />
          )}
          {result.bill_chart_png && (
            <img src={`data:image/png;base64,${result.bill_chart_png}`} alt="So sánh hóa đơn điện" style={{ marginTop: "1rem" }} />
          )}
        </div>
      )}
    </div>
  );
}
