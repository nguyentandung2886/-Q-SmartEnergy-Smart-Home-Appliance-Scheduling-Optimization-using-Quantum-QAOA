import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { getAdminStats, getAdminFeedback } from "../../api";

const RATING_COLORS = ["#EF4444", "#F59E0B", "#FACC15", "#10B981", "#06B6D4"];

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [ratingDist, setRatingDist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([getAdminStats(), getAdminFeedback()])
      .then(([s, feedback]) => {
        setStats(s);
        const counts = [1, 2, 3, 4, 5].map((star) => ({
          rating: `${star}★`,
          count: feedback.filter((f) => f.rating === star).length,
        }));
        setRatingDist(counts);
      })
      .catch(() => setError("Không tải được số liệu quản trị."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="hint" style={{ textAlign: "center", marginTop: "2rem" }}>Đang tải…</p>;
  if (error) return <p className="hint" style={{ color: "var(--accent)" }}>{error}</p>;

  const cards = [
    { label: "Tổng người dùng", value: stats.total_users },
    { label: "Hộ gia đình", value: stats.users_by_role.household },
    { label: "Doanh nghiệp", value: stats.users_by_role.business },
    { label: "Quản trị viên", value: stats.users_by_role.admin },
    { label: "Tổng đánh giá", value: stats.total_feedback },
    { label: "Điểm TB", value: stats.average_rating ?? "—" },
    { label: "Tổng lịch tối ưu", value: stats.total_schedules },
    { label: "Tiết kiệm TB", value: stats.average_savings_percent != null ? `${stats.average_savings_percent}%` : "—" },
  ];

  return (
    <div>
      <div className="page-head">
        <p className="eyebrow">Quản trị</p>
        <h1>Tổng quan hệ thống</h1>
        <p className="page-sub">Số liệu tổng hợp toàn hệ thống, cập nhật trực tiếp từ cơ sở dữ liệu.</p>
      </div>

      <div className="bento" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
        {cards.map((c) => (
          <div key={c.label} className="card">
            <div className="card-head"><h3 style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>{c.label}</h3></div>
            <p style={{ fontSize: "2rem", fontWeight: 700, margin: 0 }}>{c.value}</p>
          </div>
        ))}
      </div>

      <div className="bento" style={{ marginTop: "1.5rem" }}>
        <div className="card">
          <div className="card-head"><h3>Phân bố đánh giá</h3></div>
          <p className="hint" style={{ marginTop: 0, marginBottom: "1rem" }}>Số lượng góp ý theo mức sao.</p>
          <div style={{ height: 300, width: "100%" }}>
            <ResponsiveContainer>
              <BarChart data={ratingDist} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#9b9b9b" strokeOpacity={0.18} vertical={false} />
                <XAxis dataKey="rating" stroke="#9b9b9b" fontSize={12} tickLine={false} />
                <YAxis stroke="#9b9b9b" fontSize={11} allowDecimals={false} width={32} />
                <Tooltip
                  cursor={{ fill: "rgba(155,155,155,0.1)" }}
                  contentStyle={{ background: "#171717", border: "none", borderRadius: "8px", fontSize: "12px" }}
                  itemStyle={{ color: "#fff" }} labelStyle={{ color: "#9b9b9b" }}
                  formatter={(value) => [value, "Số góp ý"]}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {ratingDist.map((entry, i) => (
                    <Cell key={entry.rating} fill={RATING_COLORS[i]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
