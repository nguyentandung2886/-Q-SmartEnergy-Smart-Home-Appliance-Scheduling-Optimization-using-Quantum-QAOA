import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import { motion } from "framer-motion";

const fieldStyle = {
  background: "var(--surface-2)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-sm)",
  padding: "0.6rem 0.85rem",
  fontSize: "0.95rem",
  color: "var(--text)",
};

const radioRowStyle = { flexDirection: "row", alignItems: "center", gap: "0.5rem", fontWeight: 400 };

// Cấp điện áp đấu nối theo biểu giá EVN doanh nghiệp (backend/core/business_calc.py).
// Sản xuất có 4 cấp; kinh doanh (nhóm 3.3) chỉ có 3 — không có cấp >= 110 kV.
const VOLTAGE_OPTIONS = {
  production: [
    { value: "duoi_6kv", label: "Dưới 6 kV (phổ biến nhất)" },
    { value: "6_den_22kv", label: "Từ 6 kV đến dưới 22 kV" },
    { value: "22_den_110kv", label: "Từ 22 kV đến dưới 110 kV" },
    { value: "tren_110kv", label: "Từ 110 kV trở lên" },
  ],
  commercial: [
    { value: "duoi_6kv", label: "Dưới 6 kV (phổ biến nhất)" },
    { value: "6_den_22kv", label: "Từ 6 kV đến dưới 22 kV" },
    { value: "22_den_110kv", label: "Từ 22 kV trở lên" },
  ],
};

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [accountType, setAccountType] = useState("household");
  const [businessType, setBusinessType] = useState("production");
  const [voltageLevel, setVoltageLevel] = useState("duoi_6kv");
  const [scale, setScale] = useState("Nhỏ");
  const [contractedPower, setContractedPower] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  function selectBusinessType(type) {
    setBusinessType(type);
    // Kinh doanh không có cấp >= 110 kV: nếu cấp đang chọn không tồn tại ở loại hình
    // mới thì quay về mặc định "Dưới 6 kV".
    if (!VOLTAGE_OPTIONS[type].some((o) => o.value === voltageLevel)) {
      setVoltageLevel("duoi_6kv");
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const metadata =
        accountType === "business"
          ? {
              role: "business",
              business_type: businessType,
              voltage_level: voltageLevel,
              scale,
              contracted_power_kw: Number(contractedPower),
            }
          : { role: "household" };
      await register(email, password, metadata);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message || "Đăng ký thất bại. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      className="auth-page"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      transition={{ duration: 0.25 }}
    >
      <form onSubmit={handleSubmit} className="auth-form glass-panel">
        <h1>Tạo tài khoản</h1>
        {error && <p className="auth-error">{error}</p>}
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
        </label>
        <label>
          Mật khẩu (tối thiểu 8 ký tự)
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
        </label>

        <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
          <span style={{ fontSize: "0.85rem", fontWeight: 500, color: "var(--text-muted)" }}>Loại tài khoản</span>
          <label style={radioRowStyle}>
            <input
              type="radio"
              name="accountType"
              value="household"
              checked={accountType === "household"}
              onChange={() => setAccountType("household")}
            />
            Cá nhân
          </label>
          <label style={radioRowStyle}>
            <input
              type="radio"
              name="accountType"
              value="business"
              checked={accountType === "business"}
              onChange={() => setAccountType("business")}
            />
            Doanh nghiệp
          </label>
        </div>

        {accountType === "business" && (
          <>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 500, color: "var(--text-muted)" }}>Loại hình</span>
              <label style={radioRowStyle}>
                <input
                  type="radio"
                  name="businessType"
                  value="production"
                  checked={businessType === "production"}
                  onChange={() => selectBusinessType("production")}
                />
                Sản xuất
              </label>
              <label style={radioRowStyle}>
                <input
                  type="radio"
                  name="businessType"
                  value="commercial"
                  checked={businessType === "commercial"}
                  onChange={() => selectBusinessType("commercial")}
                />
                Thương mại
              </label>
            </div>
            <label>
              Cấp điện áp đấu nối
              <select
                value={voltageLevel}
                onChange={(e) => setVoltageLevel(e.target.value)}
                style={fieldStyle}
                required
              >
                {VOLTAGE_OPTIONS[businessType].map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Quy mô
              <select value={scale} onChange={(e) => setScale(e.target.value)} style={fieldStyle}>
                <option value="Nhỏ">Nhỏ</option>
                <option value="Vừa">Vừa</option>
                <option value="Lớn">Lớn</option>
              </select>
            </label>
            <label>
              Công suất hợp đồng (kW)
              <input
                type="number"
                value={contractedPower}
                onChange={(e) => setContractedPower(e.target.value)}
                required
                min="0.1"
                step="any"
              />
            </label>
          </>
        )}

        <motion.button
          type="submit"
          disabled={loading}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
        >
          {loading ? "Đang tạo tài khoản..." : "Đăng ký"}
        </motion.button>
        <p>
          Đã có tài khoản? <Link to="/login">Đăng nhập</Link>
        </p>
      </form>
    </motion.div>
  );
}
