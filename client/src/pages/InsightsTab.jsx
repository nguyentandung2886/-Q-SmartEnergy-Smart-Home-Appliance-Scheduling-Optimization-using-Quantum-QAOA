import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { useAppData } from "../AppData";
import BillChart from "../components/BillChart";

const AXIS = "#9b9b9b";

export default function InsightsTab() {
  const { result, appliances, fixedHours } = useAppData();

  if (!result) {
    return (
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <div className="page-head">
          <p className="eyebrow">Tổng quan</p>
          <h1>Bảng insight</h1>
        </div>
        <div className="card empty-state">
          <p>Chưa có kết quả tối ưu hóa nào.</p>
          <Link className="btn-ink" to="/app/optimize">Chạy tối ưu hóa</Link>
        </div>
      </motion.div>
    );
  }

  const fmt = (n) => Math.round(n).toLocaleString("vi-VN");
  const billData = [
    { name: "Trước", value: result.bill_before_vnd },
    { name: "Sau", value: result.bill_after_vnd },
  ];

  const stats = [
    { label: "Hóa đơn sau tối ưu", value: `${fmt(result.bill_after_vnd)}đ`, tone: "green" },
    { label: "Tiết kiệm", value: `${result.savings_percent?.toFixed(1)}%`, tone: "blue" },
    { label: "Tiêu thụ tháng", value: `${fmt(result.monthly_kwh ?? 0)} kWh`, tone: "" },
  ];

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <div className="page-head">
        <p className="eyebrow">Tổng quan</p>
        <h1>Bảng insight</h1>
        <p className="page-sub">Tổng hợp kết quả từ lần tối ưu hóa gần nhất.</p>
      </div>

      <div className="stat-grid">
        {stats.map((s) => (
          <div key={s.label} className="card stat">
            <span className="eyebrow">{s.label}</span>
            <span className={"stat-value" + (s.tone ? ` stat-value--${s.tone}` : "")}>{s.value}</span>
          </div>
        ))}
      </div>

      <div className="bento">
        <div className="card">
          <div className="card-head"><h3>Hóa đơn trước / sau</h3><span className="tag tag--green">-{result.savings_percent?.toFixed(0)}%</span></div>
          <div style={{ height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={billData} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={AXIS} strokeOpacity={0.2} vertical={false} />
                <XAxis dataKey="name" stroke={AXIS} fontSize={12} tickLine={false} />
                <YAxis stroke={AXIS} fontSize={11} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} width={40} />
                <Tooltip formatter={(v) => `${fmt(v)}đ`} cursor={{ fill: "rgba(0,0,0,0.04)" }} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  <Cell fill="#c26a2b" />
                  <Cell fill="#0f766e" />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <BillChart appliances={appliances} result={result} fixedHours={fixedHours} />
    </motion.div>
  );
}
