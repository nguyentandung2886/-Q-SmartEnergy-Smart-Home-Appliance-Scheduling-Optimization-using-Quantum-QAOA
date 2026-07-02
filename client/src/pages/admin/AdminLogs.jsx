import { useEffect, useState } from "react";
import { getAdminLogs } from "../../api";

const LIMIT = 50;

export default function AdminLogs() {
  const [logs, setLogs] = useState([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    getAdminLogs({ limit: LIMIT, offset })
      .then(setLogs)
      .catch(() => setError("Không tải được nhật ký."))
      .finally(() => setLoading(false));
  }, [offset]);

  return (
    <div>
      <div className="page-head">
        <p className="eyebrow">Quản trị</p>
        <h1>Nhật ký tối ưu</h1>
        <p className="page-sub">Các lần chạy tối ưu / lập lịch gần đây nhất trên toàn hệ thống.</p>
      </div>

      {error && <p className="hint" style={{ color: "var(--accent)" }}>{error}</p>}

      {loading ? (
        <p className="hint" style={{ textAlign: "center", marginTop: "2rem" }}>Đang tải…</p>
      ) : (
        <>
          <div className="card" style={{ overflowX: "auto" }}>
            <table className="data-table" style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={cell}>ID</th>
                  <th style={cell}>Người dùng</th>
                  <th style={cell}>Thời gian</th>
                  <th style={cell}>Solver</th>
                  <th style={cell}>Năng lượng</th>
                  <th style={cell}>Tiết kiệm</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((l) => (
                  <tr key={l.id}>
                    <td style={cell}>{l.id}</td>
                    <td style={cell}>{l.user_email || "—"}</td>
                    <td style={cell}>{l.created_at ? new Date(l.created_at).toLocaleString("vi-VN") : "—"}</td>
                    <td style={cell}>{l.solver_used}</td>
                    <td style={cell}>{l.energy}</td>
                    <td style={cell}>{l.savings_percent != null ? `${l.savings_percent}%` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="row-actions" style={{ marginTop: "1rem", display: "flex", gap: "0.5rem", justifyContent: "space-between" }}>
            <button className="btn nav-ghost" disabled={offset === 0} onClick={() => setOffset((o) => Math.max(0, o - LIMIT))}>
              ← Mới hơn
            </button>
            <span className="hint">Trang {Math.floor(offset / LIMIT) + 1}</span>
            <button className="btn nav-ghost" disabled={logs.length < LIMIT} onClick={() => setOffset((o) => o + LIMIT)}>
              Cũ hơn →
            </button>
          </div>
        </>
      )}
    </div>
  );
}

const cell = { textAlign: "left", padding: "0.6rem 0.75rem", borderBottom: "1px solid var(--border, rgba(155,155,155,0.2))" };
