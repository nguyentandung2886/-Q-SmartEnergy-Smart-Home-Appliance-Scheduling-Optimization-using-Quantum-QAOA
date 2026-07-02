import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { getFeedback, submitFeedback } from "../api";

export default function FeedbackTab() {
  const [rating, setRating] = useState(5);
  const [message, setMessage] = useState("");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getFeedback().then(setItems).finally(() => setLoading(false));
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!message.trim() || submitting) return;
    setSubmitting(true);
    setError("");
    try {
      const created = await submitFeedback({ rating, message: message.trim() });
      setItems((prev) => [created, ...prev]);
      setMessage("");
      setRating(5);
    } catch {
      setError("Không gửi được góp ý. Vui lòng thử lại.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <div className="page-head">
        <p className="eyebrow">Cộng đồng</p>
        <h1>Góp ý & đánh giá</h1>
        <p className="page-sub">
          Chia sẻ nhận xét, đánh giá hoặc đề xuất của bạn về Q-SmartEnergy. Tất cả góp ý được hiển
          thị công khai cho người dùng đã đăng nhập.
        </p>
      </div>

      <div className="bento">
        <form className="card" onSubmit={handleSubmit}>
          <div className="card-head">
            <h3>Gửi góp ý</h3>
          </div>

          <label className="field">
            <span>Đánh giá</span>
            <div style={{ display: "flex", gap: "0.25rem" }}>
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  type="button"
                  onClick={() => setRating(n)}
                  aria-label={`${n} sao`}
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    padding: 0,
                    fontSize: "1.5rem",
                    lineHeight: 1,
                    color: n <= rating ? "var(--accent)" : "var(--text-muted)",
                  }}
                >
                  ★
                </button>
              ))}
            </div>
          </label>

          <label className="field">
            <span>Nội dung</span>
            <textarea
              rows={4}
              value={message}
              maxLength={2000}
              placeholder="Nhận xét, đánh giá hoặc đề xuất của bạn…"
              onChange={(e) => setMessage(e.target.value)}
              style={{ resize: "vertical", fontFamily: "inherit" }}
            />
          </label>

          {error && <p className="hint" style={{ color: "var(--accent)" }}>{error}</p>}

          <div className="row-actions">
            <button className="btn-ink" type="submit" disabled={submitting || !message.trim()}>
              {submitting ? "Đang gửi…" : "Gửi góp ý"}
            </button>
          </div>
        </form>
      </div>

      <div className="page-head" style={{ marginTop: "1.5rem" }}>
        <h1 style={{ fontSize: "1.25rem" }}>Góp ý đã gửi</h1>
      </div>

      {loading ? (
        <p className="hint" style={{ textAlign: "center", marginTop: "2rem" }}>Đang tải…</p>
      ) : items.length === 0 ? (
        <div className="card empty-state">
          <p>Chưa có góp ý nào. Hãy là người đầu tiên!</p>
        </div>
      ) : (
        <div className="bento">
          {items.map((f) => (
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
