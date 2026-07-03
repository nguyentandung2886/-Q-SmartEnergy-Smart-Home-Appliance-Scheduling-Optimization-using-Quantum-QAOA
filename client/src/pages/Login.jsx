import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import { motion } from "framer-motion";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const { login, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message || "Sai email hoặc mật khẩu.");
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogle() {
    setError("");
    setGoogleLoading(true);
    try {
      // On success the browser redirects to Google, so this component unmounts
      // and the code below never runs. Only errors bring us back here.
      await loginWithGoogle();
    } catch {
      setError("Đăng nhập Google chưa khả dụng. Vui lòng thử lại sau.");
      setGoogleLoading(false);
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
        <h1>Q-SmartEnergy</h1>
        <p style={{ textAlign: "center", color: "var(--text-muted)" }}>
          Tiết kiệm điện thông minh bằng AI lượng tử
        </p>
        {error && <p className="auth-error">{error}</p>}
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
        </label>
        <label>
          Mật khẩu
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        <motion.button
          type="submit"
          disabled={loading}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
        >
          {loading ? "Đang đăng nhập..." : "Đăng nhập"}
        </motion.button>
        <div className="auth-divider"><span>hoặc</span></div>
        <motion.button
          type="button"
          className="auth-google"
          onClick={handleGoogle}
          disabled={googleLoading || loading}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
            <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.71-1.57 2.68-3.88 2.68-6.62z" />
            <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.81.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z" />
            <path fill="#FBBC05" d="M3.97 10.72a5.41 5.41 0 0 1 0-3.44V4.95H.96a9 9 0 0 0 0 8.1l3.01-2.33z" />
            <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.9 11.43 0 9 0A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z" />
          </svg>
          {googleLoading ? "Đang chuyển hướng..." : "Đăng nhập bằng Google"}
        </motion.button>
        <p>
          Chưa có tài khoản? <Link to="/register">Đăng ký</Link>
        </p>
      </form>
    </motion.div>
  );
}
