import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { supabase } from "../supabaseClient";
import { getMe, updateUsername, getMyFeedback, getAppliances, getSchedules } from "../api";

export default function ProfileTab() {
  const [me, setMe] = useState(null);
  const [username, setUsername] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [nameMsg, setNameMsg] = useState(null);

  const [pw1, setPw1] = useState("");
  const [pw2, setPw2] = useState("");
  const [savingPw, setSavingPw] = useState(false);
  const [pwMsg, setPwMsg] = useState(null);

  const [stats, setStats] = useState(null);

  const [feedback, setFeedback] = useState([]);
  const [loadingFeedback, setLoadingFeedback] = useState(true);

  useEffect(() => {
    getMe()
      .then((data) => {
        setMe(data);
        setUsername(data.username || "");
      })
      .catch(() => {});

    Promise.all([getAppliances(), getSchedules()])
      .then(([appliances, schedules]) => {
        const rated = schedules.filter((s) => s.savings_percent != null);
        const avg = rated.length
          ? rated.reduce((sum, s) => sum + s.savings_percent, 0) / rated.length
          : null;
        setStats({
          devices: appliances.length,
          runs: schedules.length,
          avgSavings: avg,
        });
      })
      .catch(() => setStats({ devices: 0, runs: 0, avgSavings: null }));

    getMyFeedback()
      .then(setFeedback)
      .catch(() => setFeedback([]))
      .finally(() => setLoadingFeedback(false));
  }, []);

  async function handleSaveName(e) {
    e.preventDefault();
    const name = username.trim();
    if (!name || savingName) return;
    setSavingName(true);
    setNameMsg(null);
    try {
      const updated = await updateUsername(name);
      setMe(updated);
      setUsername(updated.username || "");
      setNameMsg({ ok: true, text: "Đã lưu tên hiển thị." });
    } catch {
      setNameMsg({ ok: false, text: "Không lưu được tên. Vui lòng thử lại." });
    } finally {
      setSavingName(false);
    }
  }

  async function handleChangePassword(e) {
    e.preventDefault();
    if (savingPw) return;
    if (pw1.length < 6) {
      setPwMsg({ ok: false, text: "Mật khẩu phải có ít nhất 6 ký tự." });
      return;
    }
    if (pw1 !== pw2) {
      setPwMsg({ ok: false, text: "Mật khẩu xác nhận không khớp." });
      return;
    }
    setSavingPw(true);
    setPwMsg(null);
    const { error } = await supabase.auth.updateUser({ password: pw1 });
    if (error) {
      setPwMsg({ ok: false, text: error.message || "Không đổi được mật khẩu." });
    } else {
      setPwMsg({ ok: true, text: "Đổi mật khẩu thành công." });
      setPw1("");
      setPw2("");
    }
    setSavingPw(false);
  }

  const email = me?.email || "";
  const initial = (me?.username || email || "?").charAt(0).toUpperCase();
  const msgStyle = (ok) => ({ color: ok ? "var(--pale-green-fg)" : "var(--accent)" });

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <div className="page-head">
        <p className="eyebrow">Tài khoản</p>
        <h1>Hồ sơ</h1>
        <p className="page-sub">Quản lý thông tin cá nhân, mật khẩu và xem lại hoạt động của bạn.</p>
      </div>

      <div className="bento">
        <form className="card" onSubmit={handleSaveName}>
          <div className="card-head">
            <h3>Thông tin cơ bản</h3>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "0.5rem" }}>
            <div
              style={{
                width: "56px",
                height: "56px",
                borderRadius: "50%",
                background: "var(--accent)",
                color: "#fff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "1.5rem",
                fontWeight: 700,
                flexShrink: 0,
              }}
            >
              {initial}
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 600, color: "var(--text-strong)" }}>{me?.username || "Chưa đặt tên"}</div>
              <div className="hint" style={{ marginTop: "0.1rem" }}>{email}</div>
            </div>
          </div>

          <label className="field">
            <span>Email</span>
            <input type="email" value={email} readOnly disabled />
          </label>

          <label className="field">
            <span>Tên hiển thị</span>
            <input
              type="text"
              value={username}
              maxLength={50}
              placeholder="Nhập tên hiển thị…"
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>

          {nameMsg && <p className="hint" style={msgStyle(nameMsg.ok)}>{nameMsg.text}</p>}

          <div className="row-actions">
            <button className="btn-ink" type="submit" disabled={savingName || !username.trim()}>
              {savingName ? "Đang lưu…" : "Lưu"}
            </button>
          </div>
        </form>

        <form className="card" onSubmit={handleChangePassword}>
          <div className="card-head">
            <h3>Đổi mật khẩu</h3>
          </div>

          <label className="field">
            <span>Mật khẩu mới</span>
            <input
              type="password"
              value={pw1}
              placeholder="Tối thiểu 6 ký tự"
              onChange={(e) => setPw1(e.target.value)}
            />
          </label>

          <label className="field">
            <span>Xác nhận mật khẩu</span>
            <input
              type="password"
              value={pw2}
              placeholder="Nhập lại mật khẩu mới"
              onChange={(e) => setPw2(e.target.value)}
            />
          </label>

          {pwMsg && <p className="hint" style={msgStyle(pwMsg.ok)}>{pwMsg.text}</p>}

          <div className="row-actions">
            <button className="btn-ink" type="submit" disabled={savingPw || !pw1 || !pw2}>
              {savingPw ? "Đang đổi…" : "Đổi mật khẩu"}
            </button>
          </div>
        </form>
      </div>

      <div className="page-head" style={{ marginTop: "1.5rem" }}>
        <h1 style={{ fontSize: "1.25rem" }}>Thống kê sử dụng</h1>
      </div>

      <div className="stat-grid">
        <div className="card stat">
          <span className="eyebrow">Thiết bị</span>
          <span className="stat-value stat-value--blue">{stats ? stats.devices : "…"}</span>
        </div>
        <div className="card stat">
          <span className="eyebrow">Lần tối ưu đã chạy</span>
          <span className="stat-value stat-value--yellow">{stats ? stats.runs : "…"}</span>
        </div>
        <div className="card stat">
          <span className="eyebrow">Tiết kiệm trung bình</span>
          <span className="stat-value stat-value--green">
            {stats ? (stats.avgSavings != null ? `${stats.avgSavings.toFixed(0)}%` : "—") : "…"}
          </span>
        </div>
      </div>

      <div className="page-head" style={{ marginTop: "1.5rem" }}>
        <h1 style={{ fontSize: "1.25rem" }}>Đánh giá đã gửi</h1>
      </div>

      {loadingFeedback ? (
        <p className="hint" style={{ textAlign: "center", marginTop: "2rem" }}>Đang tải…</p>
      ) : feedback.length === 0 ? (
        <div className="card empty-state">
          <p>Bạn chưa gửi đánh giá nào.</p>
        </div>
      ) : (
        <div className="bento">
          {feedback.map((f) => (
            <div key={f.id} className="card">
              <div className="card-head">
                <span aria-label={`${f.rating} sao`} style={{ color: "var(--accent)", letterSpacing: "1px" }}>
                  {"★".repeat(f.rating)}
                  <span style={{ color: "var(--text-muted)" }}>{"★".repeat(5 - f.rating)}</span>
                </span>
                <span className="tag">{new Date(f.created_at).toLocaleString("vi-VN")}</span>
              </div>
              <p style={{ whiteSpace: "pre-wrap" }}>{f.message}</p>
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
