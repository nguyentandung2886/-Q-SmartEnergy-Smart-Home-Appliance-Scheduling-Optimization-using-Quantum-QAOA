import { useEffect, useState } from "react";
import { getAdminFeedback, setFeedbackFeatured } from "../../api";

export default function AdminFeedback() {
  const [items, setItems] = useState([]);
  const [ratingFilter, setRatingFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [savingId, setSavingId] = useState(null);

  useEffect(() => {
    setLoading(true);
    getAdminFeedback(ratingFilter ? Number(ratingFilter) : undefined)
      .then(setItems)
      .catch(() => setError("Không tải được danh sách đánh giá."))
      .finally(() => setLoading(false));
  }, [ratingFilter]);

  async function toggleFeatured(item) {
    setSavingId(item.id);
    try {
      const updated = await setFeedbackFeatured(item.id, !item.is_featured);
      setItems((prev) => prev.map((f) => (f.id === item.id ? { ...f, is_featured: updated.is_featured } : f)));
    } catch {
      setError("Không cập nhật được. Vui lòng thử lại.");
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div>
      <div className="page-head">
        <p className="eyebrow">Quản trị</p>
        <h1>Quản lý đánh giá</h1>
        <p className="page-sub">Bật “Hiển thị công khai” để đưa góp ý lên trang chủ.</p>
      </div>

      <label className="field" style={{ maxWidth: 220 }}>
        <span>Lọc theo số sao</span>
        <select value={ratingFilter} onChange={(e) => setRatingFilter(e.target.value)}>
          <option value="">Tất cả</option>
          {[5, 4, 3, 2, 1].map((n) => <option key={n} value={n}>{n} sao</option>)}
        </select>
      </label>

      {error && <p className="hint" style={{ color: "var(--accent)" }}>{error}</p>}

      {loading ? (
        <p className="hint" style={{ textAlign: "center", marginTop: "2rem" }}>Đang tải…</p>
      ) : items.length === 0 ? (
        <div className="card empty-state"><p>Không có đánh giá phù hợp.</p></div>
      ) : (
        <div className="bento" style={{ marginTop: "1rem" }}>
          {items.map((f) => (
            <div key={f.id} className="card">
              <div className="card-head">
                <span style={{ color: "var(--accent)", letterSpacing: "1px" }}>
                  {"★".repeat(f.rating)}
                  <span style={{ color: "var(--text-muted)" }}>{"★".repeat(5 - f.rating)}</span>
                </span>
                <span className="tag">{new Date(f.created_at).toLocaleDateString("vi-VN")}</span>
              </div>
              <p style={{ whiteSpace: "pre-wrap" }}>{f.message}</p>
              <p className="hint" style={{ margin: "0.25rem 0 0.75rem" }}>— {f.customer_name}</p>
              <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={f.is_featured}
                  disabled={savingId === f.id}
                  onChange={() => toggleFeatured(f)}
                />
                <span>Hiển thị công khai</span>
              </label>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
