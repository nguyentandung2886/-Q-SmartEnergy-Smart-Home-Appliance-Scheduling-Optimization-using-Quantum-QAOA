import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

const fadeIn = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8 } }
};

export default function Landing() {
  const navigate = useNavigate();
  const [billInput, setBillInput] = useState(2000000);
  const estimatedSavings = Math.round(billInput * 0.12); // Assume ~12% savings

  return (
    <div className="landing-page">
      {/* 1. Hero Section */}
      <section className="hero-section">
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          variants={fadeIn}
        >
          <h1 className="landing-title">Q-SmartEnergy</h1>
          <p className="landing-subtitle">
            Khai phóng sức mạnh Máy tính Lượng tử để tối ưu hóa năng lượng cho ngôi nhà của bạn. 
            Giảm thiểu hóa đơn điện, tối đa hóa năng lượng xanh, bảo vệ Trái Đất.
          </p>
        </motion.div>

        <motion.button 
          className="btn-quantum"
          onClick={() => navigate('/login')}
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.6, duration: 0.5, type: 'spring' }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          style={{ marginTop: "2rem" }}
        >
          Initialize Quantum Engine
        </motion.button>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8, duration: 0.5 }}
          style={{ 
            marginTop: "3rem", 
            padding: "2rem", 
            background: "rgba(20,24,40,0.6)", 
            borderRadius: "16px",
            border: "1px solid rgba(6,182,212,0.3)",
            width: "100%",
            maxWidth: "500px",
            boxShadow: "0 0 30px rgba(6,182,212,0.1)"
          }}
        >
          <h3 style={{ color: "var(--quantum)", marginBottom: "1rem", marginTop: 0 }}>Công cụ Ước tính Tiết kiệm (ROI)</h3>
          <p style={{ fontSize: "0.9rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
            Hóa đơn tiền điện tháng trước của bạn là bao nhiêu?
          </p>
          <div style={{ marginBottom: "1.5rem" }}>
            <span style={{ fontSize: "1.5rem", fontWeight: "bold", color: "#fff" }}>
              {billInput.toLocaleString("vi-VN")} VNĐ
            </span>
          </div>
          <input 
            type="range" 
            min="500000" 
            max="10000000" 
            step="100000" 
            value={billInput}
            onChange={(e) => setBillInput(Number(e.target.value))}
            style={{ width: "100%", accentColor: "var(--quantum)", cursor: "pointer" }}
          />
          <div style={{ marginTop: "1.5rem", padding: "1rem", background: "rgba(16,185,129,0.1)", borderRadius: "8px", border: "1px solid rgba(16,185,129,0.2)" }}>
            <p style={{ margin: 0, fontSize: "0.9rem", color: "var(--text-muted)" }}>Thuật toán lượng tử có thể giúp bạn tiết kiệm tới:</p>
            <p style={{ margin: "0.5rem 0 0", fontSize: "1.8rem", fontWeight: "bold", color: "var(--energy)" }}>
              ~{estimatedSavings.toLocaleString("vi-VN")} VNĐ/tháng
            </p>
          </div>
        </motion.div>
      </section>

      {/* 2. Vấn đề & Giải pháp */}
      <section className="landing-section" style={{ background: "rgba(6, 182, 212, 0.03)" }}>
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.3 }} variants={fadeIn}>
          <h2>Vấn đề & Giải pháp</h2>
          <div style={{ display: "flex", gap: "3rem", flexWrap: "wrap", justifyContent: "center" }}>
            <div className="feature-card" style={{ flex: "1 1 400px" }}>
              <h3 style={{ color: "var(--error)" }}>Vấn đề (Nỗi đau)</h3>
              <p>
                Tiền điện tăng vọt do sử dụng thiết bị đồng loạt vào <strong>giờ cao điểm</strong> (đỉnh tải).
                Việc tính toán lịch chạy thiết bị bằng tay cho hàng chục thiết bị là một bài toán Tổ hợp khổng lồ (Knapsack Problem) vượt quá khả năng con người. Nguy cơ cháy nổ do quá tải công suất luôn rình rập.
              </p>
            </div>
            <div className="feature-card" style={{ flex: "1 1 400px", borderColor: "var(--quantum)", boxShadow: "0 0 20px rgba(6,182,212,0.1)" }}>
              <h3 style={{ color: "var(--quantum)" }}>Giải pháp Lượng tử</h3>
              <p>
                <strong>Q-SmartEnergy</strong> chuyển đổi bài toán lên mô hình <strong>QUBO</strong> (Quadratic Unconstrained Binary Optimization) và giải quyết bằng thuật toán lượng tử <strong>QAOA</strong>.
                AI tự động "san phẳng" đỉnh tải (Peak Shaving), dời lịch chạy máy giặt, xe điện vào ban đêm, giúp bạn tiết kiệm tiền mà không làm giảm tiện nghi.
              </p>
            </div>
          </div>
        </motion.div>
      </section>

      {/* 3. Tính năng ưu việt */}
      <section className="landing-section">
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.2 }} variants={fadeIn}>
          <h2>Tính năng Ưu việt</h2>
          <div className="feature-grid">
            <div className="feature-card">
              <h3>Hybrid ML-QAOA</h3>
              <p>Sự kết hợp hoàn hảo: Machine Learning (Random Forest) dự báo chính xác thói quen dùng điện, cung cấp dữ liệu đầu vào cho Thuật toán Lượng tử (QAOA) ra quyết định tối ưu.</p>
            </div>
            <div className="feature-card">
              <h3>Giám sát Trực quan</h3>
              <p>Hệ thống biểu đồ Area Chart và Pie Chart thời gian thực giúp bạn theo dõi từng số điện được tiêu thụ, so sánh trực tiếp "Trước và Sau" tối ưu để thấy rõ hiệu quả.</p>
            </div>
            <div className="feature-card">
              <h3>Cảnh báo An toàn</h3>
              <p>Hệ thống tính toán công suất đồng thời (Peak Power) để phòng chống cháy nổ. Tự động gửi báo cáo tối ưu qua Email và SMS đến người dùng.</p>
            </div>
            <div className="feature-card">
              <h3>Tích hợp Thời tiết</h3>
              <p>Tự động lấy dữ liệu thời tiết (Nắng/Mưa) để ưu tiên sử dụng thiết bị vào lúc hệ thống Pin Năng lượng mặt trời (Solar Panel) tạo ra nhiều điện nhất.</p>
            </div>
          </div>
        </motion.div>
      </section>

      {/* 4. Hướng dẫn sử dụng */}
      <section className="landing-section" style={{ background: "rgba(16, 185, 129, 0.02)" }}>
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.2 }} variants={fadeIn}>
          <h2>Hướng dẫn Sử dụng</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", maxWidth: "800px", margin: "0 auto", textAlign: "left" }}>
            <div className="feature-card" style={{ display: "flex", gap: "1.5rem", alignItems: "center", padding: "1.5rem" }}>
              <div style={{ fontSize: "2rem", fontWeight: "bold", color: "var(--quantum)", minWidth: "40px" }}>1</div>
              <div>
                <h3 style={{ margin: "0 0 0.5rem 0" }}>Khởi tạo Động cơ (Đăng nhập)</h3>
                <p style={{ margin: 0 }}>Bấm <strong>Initialize Quantum Engine</strong> để đăng nhập/đăng ký tài khoản và truy cập vào Bảng điều khiển (Dashboard).</p>
              </div>
            </div>
            <div className="feature-card" style={{ display: "flex", gap: "1.5rem", alignItems: "center", padding: "1.5rem" }}>
              <div style={{ fontSize: "2rem", fontWeight: "bold", color: "var(--quantum)", minWidth: "40px" }}>2</div>
              <div>
                <h3 style={{ margin: "0 0 0.5rem 0" }}>Khai báo Thiết bị</h3>
                <p style={{ margin: 0 }}>Thêm các thiết bị tiêu thụ điện trong nhà bạn (Ví dụ: Máy giặt, Xe điện, Tủ lạnh). Đặt giới hạn thời gian hoạt động linh hoạt hoặc cố định.</p>
              </div>
            </div>
            <div className="feature-card" style={{ display: "flex", gap: "1.5rem", alignItems: "center", padding: "1.5rem" }}>
              <div style={{ fontSize: "2rem", fontWeight: "bold", color: "var(--quantum)", minWidth: "40px" }}>3</div>
              <div>
                <h3 style={{ margin: "0 0 0.5rem 0" }}>Kích hoạt Lượng tử (Tối ưu hóa)</h3>
                <p style={{ margin: 0 }}>Bấm nút <strong>Tối ưu hóa bằng Quantum QAOA</strong>. Thuật toán sẽ tính toán và vẽ lại toàn bộ lịch trình, "san phẳng" đỉnh tải tiêu thụ.</p>
              </div>
            </div>
            <div className="feature-card" style={{ display: "flex", gap: "1.5rem", alignItems: "center", padding: "1.5rem" }}>
              <div style={{ fontSize: "2rem", fontWeight: "bold", color: "var(--quantum)", minWidth: "40px" }}>4</div>
              <div>
                <h3 style={{ margin: "0 0 0.5rem 0" }}>Nhận Báo cáo</h3>
                <p style={{ margin: 0 }}>Xem trực quan số tiền tiết kiệm được, biểu đồ tiêu thụ 24h. Bạn có thể xuất file PDF hoặc gửi kết quả trực tiếp qua Email.</p>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* 5. Tech Stack (Optional but good for Hackathons) */}
      <section className="landing-section" style={{ textAlign: "center", borderTop: "1px solid rgba(255,255,255,0.05)" }}>
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeIn}>
          <p style={{ color: "var(--text-muted)", marginBottom: "1rem" }}>ĐƯỢC XÂY DỰNG BẰNG CÔNG NGHỆ LÕI</p>
          <div style={{ display: "flex", justifyContent: "center", gap: "2rem", flexWrap: "wrap", opacity: 0.7, fontSize: "1.2rem", fontWeight: "bold" }}>
            <span>ReactJS</span>
            <span>FastAPI</span>
            <span>Python</span>
            <span>Qiskit / QAOA</span>
            <span>Recharts</span>
          </div>
        </motion.div>
      </section>

      {/* 5. Đội ngũ phát triển */}
      <section className="landing-section" style={{ textAlign: "center", background: "rgba(16, 185, 129, 0.02)", borderTop: "1px solid rgba(255,255,255,0.05)" }}>
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeIn}>
          <h2 style={{ color: "var(--energy)", marginBottom: "1rem" }}>Đội Ngũ Phát Triển</h2>
          <p style={{ fontSize: "1.2rem", fontWeight: "600", color: "#fff" }}>Nhóm Phá Đảo Thế Giới Ảo</p>
          <p style={{ color: "var(--text-muted)", marginTop: "0.5rem" }}>
            Cùng nhau mang công nghệ Lượng Tử vào cuộc sống thực, kiến tạo tương lai năng lượng bền vững.
          </p>
        </motion.div>
      </section>
      
      {/* Footer */}
      <footer style={{ textAlign: "center", padding: "2rem", background: "rgba(0,0,0,0.5)", color: "var(--text-muted)", fontSize: "0.9rem" }}>
        © 2026 Q-SmartEnergy. Giải pháp năng lượng tương lai.
      </footer>
    </div>
  );
}
