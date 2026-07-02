import { useEffect, useState } from "react";
import { getAdminUsers } from "../../api";

const ROLE_LABEL = { household: "Hộ gia đình", business: "Doanh nghiệp", admin: "Quản trị" };

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getAdminUsers()
      .then(setUsers)
      .catch(() => setError("Không tải được danh sách người dùng."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-head">
        <p className="eyebrow">Quản trị</p>
        <h1>Người dùng</h1>
        <p className="page-sub">Tổng cộng {users.length} tài khoản.</p>
      </div>

      {error && <p className="hint" style={{ color: "var(--accent)" }}>{error}</p>}

      {loading ? (
        <p className="hint" style={{ textAlign: "center", marginTop: "2rem" }}>Đang tải…</p>
      ) : (
        <div className="card" style={{ overflowX: "auto" }}>
          <table className="data-table" style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={cell}>ID</th>
                <th style={cell}>Email</th>
                <th style={cell}>Tên hiển thị</th>
                <th style={cell}>Vai trò</th>
                <th style={cell}>Loại DN</th>
                <th style={cell}>Ngày tạo</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td style={cell}>{u.id}</td>
                  <td style={cell}>{u.email || "—"}</td>
                  <td style={cell}>{u.username || "—"}</td>
                  <td style={cell}>{ROLE_LABEL[u.role] || u.role}</td>
                  <td style={cell}>{u.business_type || "—"}</td>
                  <td style={cell}>{u.created_at ? new Date(u.created_at).toLocaleDateString("vi-VN") : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const cell = { textAlign: "left", padding: "0.6rem 0.75rem", borderBottom: "1px solid var(--border, rgba(155,155,155,0.2))" };
