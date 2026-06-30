import { useMemo } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';

export default function BillChart({ appliances, result, fixedHours }) {
  const chartData = useMemo(() => {
    if (!result) return [];
    
    const hourlyBefore = new Array(24).fill(0);
    const hourlyAfter = new Array(24).fill(0);

    appliances.forEach(app => {
      const dur = Math.ceil(app.duration_hours);
      const power = app.power_w;

      if (app.is_flexible) {
        // Before: default starts at 18 (Peak hour)
        for (let i = 0; i < dur; i++) {
          hourlyBefore[(18 + i) % 24] += power;
        }
        // After: optimized schedule
        const start = result.schedule[app.name] ?? 18;
        for (let i = 0; i < dur; i++) {
          hourlyAfter[(start + i) % 24] += power;
        }
      } else {
        // Fixed: uses fixedHours state
        const hours = fixedHours[app.name] || [];
        hours.forEach(h => {
          hourlyBefore[h] += power;
          hourlyAfter[h] += power;
        });
      }
    });

    const data = [];
    for (let i = 0; i < 24; i++) {
      data.push({
        hour: `${i}h`,
        before: hourlyBefore[i] / 1000, // kW
        after: hourlyAfter[i] / 1000,   // kW
      });
    }
    return data;
  }, [appliances, result, fixedHours]);

  const pieData = useMemo(() => {
    if (!result) return [];
    return appliances.map(app => ({
      name: app.name,
      value: (app.power_w / 1000) * app.duration_hours * 30, // Monthly kWh
    })).sort((a, b) => b.value - a.value);
  }, [appliances, result]);

  const COLORS = ['#06B6D4', '#10B981', '#3B82F6', '#8B5CF6', '#EC4899', '#F59E0B', '#EF4444', '#6B7280'];

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "2rem", marginTop: "2rem" }}>
      {/* Area Chart for Hourly Load */}
      <div className="section-card glass-panel" style={{ flex: "1 1 500px" }}>
        <h3 style={{ marginTop: 0, marginBottom: "1rem", color: "var(--quantum)" }}>📉 Biểu đồ Tải điện (24h)</h3>
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
          Hiệu quả san phẳng đỉnh tải. Đường màu cam đại diện cho thói quen cũ (tập trung giờ cao điểm).
        </p>
        <div style={{ height: 300, width: "100%" }}>
          <ResponsiveContainer>
            <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="colorBefore" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#F59E0B" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorAfter" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06B6D4" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#06B6D4" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="hour" stroke="rgba(255,255,255,0.4)" fontSize={12} />
              <YAxis stroke="rgba(255,255,255,0.4)" fontSize={12} unit="kW" />
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <Tooltip 
                contentStyle={{ backgroundColor: "rgba(20,24,40,0.9)", borderColor: "rgba(255,255,255,0.1)", borderRadius: "8px" }}
                itemStyle={{ color: "#fff" }}
              />
              <Area type="monotone" dataKey="before" name="Trước tối ưu" stroke="#F59E0B" fillOpacity={1} fill="url(#colorBefore)" />
              <Area type="monotone" dataKey="after" name="Sau tối ưu" stroke="#06B6D4" fillOpacity={1} fill="url(#colorAfter)" />
              <Legend verticalAlign="top" height={36}/>
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Pie Chart for Breakdown */}
      <div className="section-card glass-panel" style={{ flex: "1 1 300px" }}>
        <h3 style={{ marginTop: 0, marginBottom: "1rem", color: "var(--quantum)" }}>🥧 Tỷ trọng Tiêu thụ (Tháng)</h3>
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
          Thiết bị tiêu tốn nhiều điện năng nhất.
        </p>
        <div style={{ height: 400, width: "100%" }}>
          <ResponsiveContainer>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="40%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={5}
                dataKey="value"
                stroke="none"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip 
                formatter={(value) => [`${value.toFixed(1)} kWh`, "Điện năng"]}
                contentStyle={{ backgroundColor: "rgba(20,24,40,0.9)", borderColor: "rgba(255,255,255,0.1)", borderRadius: "8px" }}
              />
              <Legend wrapperStyle={{ fontSize: "12px" }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
