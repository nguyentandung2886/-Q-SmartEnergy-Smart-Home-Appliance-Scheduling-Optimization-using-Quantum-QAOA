import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { Cpu, Zap, ShieldAlert, BarChart3, Activity, Globe, Lightbulb, TrendingDown, Star, ChevronDown, ChevronUp, CheckCircle, Mail, MapPin, Phone } from '../components/icons';

const fadeIn = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.8, ease: "easeOut" } }
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.2
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } }
};

// Qubit Particle Component
const QubitParticles = () => {
  const particles = Array.from({ length: 15 });
  return (
    <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, overflow: 'hidden', zIndex: 0, pointerEvents: 'none' }}>
      {particles.map((_, i) => (
        <motion.div
          key={i}
          initial={{ 
            opacity: 0, 
            x: Math.random() * 100 + 'vw', 
            y: Math.random() * 100 + 'vh',
            scale: Math.random() * 0.5 + 0.5
          }}
          animate={{
            opacity: [0, 0.5, 0],
            y: [null, Math.random() * -100 - 50],
            x: [null, Math.random() * 50 - 25]
          }}
          transition={{
            duration: Math.random() * 10 + 10,
            repeat: Infinity,
            ease: "linear",
            delay: Math.random() * 10
          }}
          style={{
            position: 'absolute',
            width: '6px',
            height: '6px',
            background: 'var(--quantum)',
            borderRadius: '50%',
            boxShadow: '0 0 10px var(--quantum-glow), 0 0 20px var(--quantum)'
          }}
        />
      ))}
    </div>
  );
};

export default function Landing() {
  const navigate = useNavigate();
  const [billInput, setBillInput] = useState(2000000);
  const estimatedSavings = Math.round(billInput * 0.15); // 15%
  
  const [displaySavings, setDisplaySavings] = useState(0);
  const [activeFaq, setActiveFaq] = useState(null);
  
  useEffect(() => {
    let start = displaySavings;
    let end = estimatedSavings;
    let startTime = performance.now();
    const duration = 500;
    
    const updateCounter = (currentTime) => {
      let elapsed = currentTime - startTime;
      let progress = Math.min(elapsed / duration, 1);
      let easeProgress = 1 - Math.pow(1 - progress, 4);
      setDisplaySavings(Math.floor(start + (end - start) * easeProgress));
      
      if (progress < 1) {
        requestAnimationFrame(updateCounter);
      }
    };
    requestAnimationFrame(updateCounter);
  }, [estimatedSavings]);

  const toggleFaq = (index) => {
    setActiveFaq(activeFaq === index ? null : index);
  };

  const faqs = [
    { q: "QAOA Lượng tử hoạt động như thế nào?", a: "Q-SmartEnergy sử dụng thuật toán Lượng tử (QAOA) để giải quyết bài toán Tổ hợp lập lịch. Hệ thống số hóa ngôi nhà của bạn thành mô hình QUBO, sau đó lượng tử hóa để tìm ra lịch biểu tối ưu nhất trong tích tắc, điều mà máy tính thường phải mất hàng năm." },
    { q: "Tôi có cần mua phần cứng lượng tử không?", a: "Hoàn toàn không. Thuật toán của chúng tôi chạy trên Cloud (Đám mây) và sử dụng hệ thống giả lập hoặc kết nối trực tiếp qua API tới các máy tính lượng tử thực tế của IBM. Bạn chỉ cần điện thoại hoặc laptop." },
    { q: "Liệu thuật toán có tự tắt tủ lạnh của tôi không?", a: "Không. Bạn có toàn quyền thiết lập 'Khung giờ bắt buộc hoạt động' cho từng thiết bị. Hệ thống chỉ tối ưu hóa trong những khoảng thời gian linh hoạt (ví dụ: máy giặt, máy bơm, sạc xe điện)." },
    { q: "Tôi có thể tiết kiệm được bao nhiêu?", a: "Trung bình khách hàng của Q-SmartEnergy tiết kiệm được từ 10% đến 25% hóa đơn tiền điện hàng tháng nhờ việc dịch chuyển tải khỏi các khung giờ cao điểm có giá điện đắt đỏ." }
  ];

  return (
    <div className="landing-page" style={{ position: 'relative', zIndex: 10, fontFamily: 'Outfit, sans-serif' }}>
      
      {/* 0. STICKY NAVBAR */}
      <nav style={{
        position: 'fixed',
        top: 0, left: 0, right: 0,
        height: '80px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 2rem',
        background: 'rgba(5, 5, 17, 0.7)',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        zIndex: 1000
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }} onClick={() => window.scrollTo(0,0)}>
          <Zap size={24} color="var(--quantum)" />
          <span style={{ fontSize: '1.5rem', fontWeight: '800', color: '#fff', fontFamily: 'Montserrat' }}>Q-Smart<span style={{ color: 'var(--quantum)' }}>Energy</span></span>
        </div>
        
        <div style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
          <a href="#features" onClick={(e) => { e.preventDefault(); document.getElementById('features').scrollIntoView({ behavior: 'smooth', block: 'start' }); }} style={{ color: 'var(--text-muted)', textDecoration: 'none', fontWeight: '500', transition: 'color 0.2s' }} onMouseOver={(e) => e.target.style.color='#fff'} onMouseOut={(e) => e.target.style.color='var(--text-muted)'}>Tính năng</a>
          <a href="#how-it-works" onClick={(e) => { e.preventDefault(); document.getElementById('how-it-works').scrollIntoView({ behavior: 'smooth', block: 'start' }); }} style={{ color: 'var(--text-muted)', textDecoration: 'none', fontWeight: '500', transition: 'color 0.2s' }} onMouseOver={(e) => e.target.style.color='#fff'} onMouseOut={(e) => e.target.style.color='var(--text-muted)'}>Cơ chế</a>
          <a href="#testimonials" onClick={(e) => { e.preventDefault(); document.getElementById('testimonials').scrollIntoView({ behavior: 'smooth', block: 'start' }); }} style={{ color: 'var(--text-muted)', textDecoration: 'none', fontWeight: '500', transition: 'color 0.2s' }} onMouseOver={(e) => e.target.style.color='#fff'} onMouseOut={(e) => e.target.style.color='var(--text-muted)'}>Đánh giá</a>
          <a href="#faq" onClick={(e) => { e.preventDefault(); document.getElementById('faq').scrollIntoView({ behavior: 'smooth', block: 'start' }); }} style={{ color: 'var(--text-muted)', textDecoration: 'none', fontWeight: '500', transition: 'color 0.2s' }} onMouseOver={(e) => e.target.style.color='#fff'} onMouseOut={(e) => e.target.style.color='var(--text-muted)'}>FAQ</a>
        </div>
        
        <div>
          <button className="btn" onClick={() => navigate('/login')}>
            Đăng nhập
          </button>
        </div>
      </nav>

      {/* 1. HERO SECTION & ROI CALCULATOR */}
      <section className="hero-section" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', paddingTop: '80px', paddingBottom: '4rem', position: 'relative' }}>
        <QubitParticles />
        <div style={{ maxWidth: '1200px', margin: '0 auto', width: '100%', padding: '0 2rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '4rem', alignItems: 'center' }}>
          
          {/* Left: Text */}
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 1, ease: "easeOut" }}
            style={{ position: 'relative', zIndex: 2 }}
          >
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(6, 182, 212, 0.1)', border: '1px solid rgba(6, 182, 212, 0.2)', padding: '0.5rem 1rem', borderRadius: '50px', marginBottom: '2rem' }}>
              <Activity size={16} color="var(--neon-cyan)" />
              <span style={{ fontSize: '0.85rem', color: 'var(--neon-cyan)', fontWeight: '600', letterSpacing: '1px', textTransform: 'uppercase' }}>Vận hành bởi QAOA Quantum</span>
            </div>
            
            <h1 className="landing-title" style={{ fontSize: '4.5rem', lineHeight: '1.1', marginBottom: '1.5rem', textShadow: '0 0 40px rgba(6, 182, 212, 0.3)' }}>
              The New Era of<br />
              <span style={{ color: '#fff', WebkitTextFillColor: '#fff', background: 'none' }}>Smart Energy</span>
            </h1>
            
            <p className="landing-subtitle" style={{ fontSize: '1.25rem', margin: '0 0 2.5rem', opacity: 0.8, lineHeight: '1.6' }}>
              <strong>Q-SmartEnergy: Kiến tạo tương lai năng lượng.</strong><br/>
              Hệ thống tối ưu hóa tiêu thụ điện đầu tiên ứng dụng Điện toán Lượng tử. 
              Cắt giảm chi phí, bảo vệ lưới điện, kiến tạo tương lai bền vững.
            </p>
            
            <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', justifyContent: 'center' }}>
              <motion.button 
                className="btn-quantum"
                onClick={() => navigate('/login')}
                whileHover={{ scale: 1.05, boxShadow: "0 0 30px var(--quantum-glow)" }}
                whileTap={{ scale: 0.95 }}
                style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1.25rem 2.5rem', fontSize: '1.1rem', textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 'bold' }}
              >
                <Zap size={20} />
                Initialize Engine
              </motion.button>
            </div>
          </motion.div>

          {/* Right: Glassmorphism ROI Calculator */}
          <motion.div
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 1, delay: 0.2, ease: "easeOut" }}
            style={{ position: 'relative', zIndex: 2 }}
          >
            <div className="glass-panel" style={{ 
              padding: '3rem', 
              background: 'rgba(20, 24, 40, 0.6)', 
              backdropFilter: 'blur(20px)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              boxShadow: '0 0 40px rgba(16, 185, 129, 0.15) inset, 0 20px 40px rgba(0,0,0,0.5)',
              position: 'relative',
              overflow: 'hidden'
            }}>
              {/* Neon Glow background */}
              <div style={{ position: 'absolute', top: '-50px', right: '-50px', width: '200px', height: '200px', background: 'var(--energy)', filter: 'blur(100px)', opacity: 0.3, borderRadius: '50%' }} />

              <h3 style={{ fontSize: '1.8rem', color: '#fff', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <TrendingDown color="var(--energy)" /> Công cụ Ước tính Tiết kiệm
              </h3>
              <p style={{ color: 'var(--text-muted)', marginBottom: '2.5rem' }}>Thuật toán lượng tử có thể tiết kiệm cho bạn bao nhiêu tiền mỗi tháng?</p>
              
              <div style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', alignItems: 'flex-end' }}>
                  <span style={{ color: '#cbd5e1' }}>Hóa đơn điện hiện tại</span>
                  <span style={{ fontSize: '2rem', fontWeight: 'bold', color: '#fff', fontFamily: 'Montserrat' }}>
                    {billInput.toLocaleString("vi-VN")} <span style={{ fontSize: '1rem', color: 'var(--text-muted)' }}>VNĐ</span>
                  </span>
                </div>
                
                <input 
                  type="range" 
                  min="500000" 
                  max="10000000" 
                  step="100000" 
                  value={billInput}
                  onChange={(e) => setBillInput(Number(e.target.value))}
                  style={{ 
                    width: "100%", 
                    height: "6px",
                    background: "rgba(255,255,255,0.1)",
                    borderRadius: "10px",
                    outline: "none",
                    accentColor: "var(--energy)",
                    cursor: "pointer" 
                  }}
                />
              </div>
              
              <div style={{ background: 'rgba(16,185,129,0.1)', padding: '1.5rem', borderRadius: '12px', border: '1px solid rgba(16,185,129,0.2)', textAlign: 'center' }}>
                <p style={{ margin: 0, color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Tiết kiệm dự kiến (lên đến 15%)</p>
                <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '3rem', fontWeight: '700', color: 'var(--neon-emerald)', fontFamily: 'Montserrat', textShadow: '0 0 20px rgba(16,185,129,0.4)' }}>
                    {displaySavings.toLocaleString("vi-VN")}
                  </span>
                  <span style={{ fontSize: '1rem', color: 'var(--neon-emerald)' }}>VNĐ/tháng</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* 2. PROBLEM VS SOLUTION (Split Screen & Peak Shaving Animation) */}
      <section id="features" className="landing-section" style={{ padding: '6rem 2rem', background: 'rgba(255,255,255,0.02)', scrollMarginTop: '80px' }}>
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.3 }} variants={fadeIn} style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '4rem' }}>
            <h2 style={{ fontSize: '3rem', marginBottom: '1rem', color: '#fff' }}>Đột phá Giới hạn</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '1.2rem', maxWidth: '600px', margin: '0 auto' }}>Cách mạng hóa việc quản lý năng lượng từ hộ gia đình đến khu công nghiệp</p>
          </div>
          
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "3rem", alignItems: 'center' }}>
            {/* Left: Content */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
              <div className="glass-panel" style={{ padding: '2.5rem', background: 'rgba(20, 10, 10, 0.5)', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                  <ShieldAlert size={28} color="var(--error)" />
                  <h3 style={{ fontSize: '1.5rem', color: 'var(--error)', margin: 0 }}>Bài toán quá tải</h3>
                </div>
                <p style={{ fontSize: '1.05rem', color: '#cbd5e1', lineHeight: '1.7', margin: 0 }}>
                  Hóa đơn tăng vọt do sử dụng đồng loạt vào <strong>giờ cao điểm</strong>. Lập lịch thủ công cho hàng chục thiết bị là bài toán Tổ hợp khổng lồ (Knapsack), mang nguy cơ sập nguồn.
                </p>
              </div>
              
              <div className="glass-panel" style={{ padding: '2.5rem', background: 'rgba(6, 182, 212, 0.05)', borderColor: 'rgba(6, 182, 212, 0.3)', boxShadow: '0 0 30px rgba(6, 182, 212, 0.1) inset' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                  <Cpu size={28} color="var(--quantum)" />
                  <h3 style={{ fontSize: '1.5rem', color: 'var(--quantum)', margin: 0 }}>Giải pháp Lượng tử</h3>
                </div>
                <p style={{ fontSize: '1.05rem', color: '#cbd5e1', lineHeight: '1.7', margin: 0 }}>
                  Số hóa thành mô hình <strong>QUBO</strong> và giải bằng <strong>QAOA</strong>. Tự động "san phẳng" đỉnh tải (Peak Shaving) cực nhanh, tối ưu chi phí mà không hy sinh tiện nghi.
                </p>
              </div>
            </div>

            {/* Right: Peak Shaving Animation Chart */}
            <div className="glass-panel" style={{ padding: '2rem', height: '100%', minHeight: '350px', display: 'flex', flexDirection: 'column', position: 'relative', overflow: 'hidden' }}>
              <h4 style={{ color: '#fff', marginBottom: '1rem', textAlign: 'center', fontSize: '1.2rem' }}>Mô phỏng San phẳng Đỉnh tải (Peak Shaving)</h4>
              <div style={{ flex: 1, display: 'flex', alignItems: 'flex-end', gap: '8px', paddingBottom: '20px', position: 'relative' }}>
                
                {/* Reference Line */}
                <div style={{ position: 'absolute', top: '40%', left: 0, right: 0, borderTop: '2px dashed rgba(16,185,129,0.5)', zIndex: 1 }} />
                <span style={{ position: 'absolute', top: 'calc(40% - 26px)', left: '10px', fontSize: '0.8rem', color: 'var(--energy)', background: 'rgba(5,5,17,0.9)', padding: '2px 8px', borderRadius: '4px', zIndex: 10, border: '1px solid rgba(16,185,129,0.3)', fontWeight: 'bold' }}>Giới hạn An toàn</span>

                {[40, 60, 100, 90, 45, 30, 80, 110, 70, 50].map((val, i) => (
                  <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', height: '100%', position: 'relative', zIndex: 2 }}>
                    {/* Before Optimization (Red/High) */}
                    <motion.div 
                      initial={{ height: val + '%' }}
                      animate={{ height: val > 70 ? 60 + (i%10) + '%' : val + '%' }}
                      transition={{ duration: 2, repeat: Infinity, repeatType: 'reverse', ease: 'easeInOut' }}
                      style={{ 
                        width: '100%', 
                        background: val > 70 ? 'linear-gradient(to top, rgba(239,68,68,0.2), var(--error))' : 'linear-gradient(to top, rgba(6,182,212,0.2), var(--quantum))',
                        borderRadius: '4px 4px 0 0',
                        opacity: 0.8
                      }} 
                    />
                  </div>
                ))}
              </div>
              <p style={{ textAlign: 'center', fontSize: '0.9rem', color: 'var(--text-muted)', margin: 0 }}>Hiệu ứng: Chuyển dịch tải từ giờ cao điểm sang giờ thấp điểm</p>
            </div>
          </div>
        </motion.div>
      </section>

      {/* 3. HOW IT WORKS TIMELINE */}
      <section id="how-it-works" className="landing-section" style={{ padding: '6rem 2rem', scrollMarginTop: '80px' }}>
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
          <motion.h2 
            initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6 }}
            style={{ fontSize: '3rem', marginBottom: '4rem', color: '#fff', textAlign: 'center' }}
          >
            4 Bước Vận hành
          </motion.h2>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {[
              { num: "01", title: "Kết nối Hệ thống", desc: "Đăng nhập an toàn và truy cập vào Bảng điều khiển trung tâm.", icon: <Globe size={24} color="#fff"/> },
              { num: "02", title: "Khai báo Thiết bị", desc: "Cập nhật danh sách thiết bị điện, công suất và khung giờ ưu tiên hoạt động.", icon: <Lightbulb size={24} color="#fff"/> },
              { num: "03", title: "Kích hoạt Quantum QAOA", desc: "Chỉ một chạm, thuật toán sẽ tính toán và sắp xếp lại toàn bộ lịch trình tối ưu nhất.", icon: <Cpu size={24} color="#fff"/> },
              { num: "04", title: "Tận hưởng Kết quả", desc: "Theo dõi biểu đồ tiêu thụ đã được 'san phẳng' và nhận báo cáo tiết kiệm.", icon: <BarChart3 size={24} color="#fff"/> }
            ].map((step, index) => (
              <motion.div 
                key={index}
                initial={{ opacity: 0, x: -30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.15, duration: 0.5 }}
                whileHover={{ x: 10, background: 'rgba(6, 182, 212, 0.1)', borderColor: 'rgba(6, 182, 212, 0.3)' }}
                style={{ display: 'flex', gap: '2rem', alignItems: 'center', padding: '2rem', background: 'var(--surface)', borderRadius: '16px', border: '1px solid var(--glass-border)', transition: 'background 0.3s, border-color 0.3s' }}
              >
                <div style={{ fontSize: '3rem', fontWeight: '800', fontFamily: 'Montserrat', color: 'transparent', WebkitTextStroke: '1px rgba(255,255,255,0.2)', opacity: 0.8, minWidth: '80px' }}>
                  {step.num}
                </div>
                <div style={{ width: '60px', height: '60px', borderRadius: '50%', background: 'linear-gradient(135deg, var(--quantum), var(--neon-purple))', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, boxShadow: '0 0 20px rgba(6, 182, 212, 0.4)' }}>
                  {step.icon}
                </div>
                <div>
                  <h3 style={{ fontSize: '1.4rem', color: '#fff', marginBottom: '0.5rem' }}>{step.title}</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '1.05rem', lineHeight: '1.5', margin: 0 }}>{step.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* 4. SOCIAL PROOF (Testimonials) */}
      <section id="testimonials" className="landing-section" style={{ padding: '6rem 2rem', background: 'rgba(139, 92, 246, 0.03)', scrollMarginTop: '80px' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <motion.h2 
            initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6 }}
            style={{ fontSize: '3rem', marginBottom: '4rem', color: '#fff', textAlign: 'center' }}
          >
            Khách hàng Đánh giá
          </motion.h2>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
            {[
              { name: "Anh Hoàng Tuấn", role: "Quản lý Tòa nhà", text: "Từ khi áp dụng Q-SmartEnergy, hóa đơn điện khu căn hộ giảm rõ rệt 18%. Thuật toán tự động sắp xếp giờ bơm nước và sưởi ấm cực kỳ thông minh." },
              { name: "Anh Trịnh Bình", role: "Chủ hộ Gia đình", text: "Giao diện rất tương lai và đẹp mắt. Tôi không rành công nghệ nhưng chỉ cần nhập thiết bị và bấm tối ưu là hệ thống tự lo phần còn lại." },
              { name: "Anh Hoàng Phan", role: "Chuyên gia Năng lượng", text: "Việc đưa QAOA vào bài toán Peak Shaving thực sự là một bước đột phá. Biểu đồ tiêu thụ phẳng hơn hẳn, giảm thiểu áp lực cho lưới điện quốc gia." }
            ].map((review, i) => (
              <motion.div 
                key={i} 
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.2, duration: 0.5 }}
                className="glass-panel" 
                style={{ padding: '2rem' }}
              >
                <div style={{ display: 'flex', gap: '4px', marginBottom: '1rem' }}>
                  {[...Array(5)].map((_, j) => <Star key={j} size={16} color="#fbbf24" fill="#fbbf24" />)}
                </div>
                <p style={{ color: '#cbd5e1', fontSize: '1.05rem', lineHeight: '1.6', marginBottom: '1.5rem', fontStyle: 'italic' }}>
                  "{review.text}"
                </p>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'var(--quantum)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
                    {review.name.charAt(0)}
                  </div>
                  <div>
                    <div style={{ fontWeight: '600', color: '#fff' }}>{review.name}</div>
                    <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>{review.role}</div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* 5. FAQ ACCORDION */}
      <section id="faq" className="landing-section" style={{ padding: '6rem 2rem', scrollMarginTop: '80px' }}>
        <div style={{ maxWidth: '800px', margin: '0 auto' }}>
          <motion.h2 
            initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6 }}
            style={{ fontSize: '3rem', marginBottom: '3rem', color: '#fff', textAlign: 'center' }}
          >
            Câu hỏi Thường gặp
          </motion.h2>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {faqs.map((faq, i) => (
              <motion.div 
                key={i} 
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1, duration: 0.4 }}
                className="glass-panel" 
                style={{ padding: '0', overflow: 'hidden' }}
              >
                <button
                  onClick={() => toggleFaq(i)}
                  style={{ width: '100%', padding: '1.5rem 2rem', background: 'transparent', border: 'none', color: 'var(--text-strong)', fontSize: '1.15rem', textAlign: 'left', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                >
                  <span style={{ fontFamily: 'Montserrat', fontWeight: '600' }}>{faq.q}</span>
                  {activeFaq === i ? <ChevronUp color="var(--quantum)" /> : <ChevronDown color="var(--text-muted)" />}
                </button>
                <AnimatePresence>
                  {activeFaq === i && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.3 }}
                    >
                      <div style={{ padding: '0 2rem 1.5rem', color: 'var(--text-muted)', lineHeight: '1.6', fontSize: '1.05rem' }}>
                        {faq.a}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* 6. PROFESSIONAL FOOTER */}
      <footer style={{ borderTop: "1px solid rgba(255,255,255,0.05)", background: 'rgba(5, 5, 17, 0.8)', padding: '4rem 2rem 2rem' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '3rem', marginBottom: '3rem' }}>
          
          <div>
            <h3 style={{ fontSize: '1.8rem', color: '#fff', marginBottom: '0.5rem', fontFamily: 'Montserrat' }}>
              Q-Smart<span style={{ color: 'var(--quantum)' }}>Energy</span>
            </h3>
            <p style={{ color: 'var(--quantum)', fontWeight: '600', marginBottom: '1.5rem', fontSize: '1.05rem' }}>
              Kiến tạo tương lai năng lượng
            </p>
            <p style={{ color: 'var(--text-muted)', lineHeight: '1.6', marginBottom: '1.5rem' }}>
              Giải pháp tối ưu hóa năng lượng ứng dụng Điện toán Lượng tử, mang lại hiệu quả vượt trội cho tương lai bền vững.
            </p>
            <div style={{ display: 'flex', gap: '1rem' }}>
              {/* Social icons placeholders */}
              <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Activity size={18} color="#fff" /></div>
              <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Globe size={18} color="#fff" /></div>
            </div>
          </div>

          <div>
            <h4 style={{ color: '#fff', fontSize: '1.2rem', marginBottom: '1.5rem', fontFamily: 'Montserrat' }}>Sản phẩm</h4>
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '0.8rem', color: 'var(--text-muted)' }}>
              <li><a href="#" style={{ color: 'inherit', textDecoration: 'none' }}>Tính năng</a></li>
              <li><a href="#" style={{ color: 'inherit', textDecoration: 'none' }}>Công nghệ QAOA</a></li>
              <li><a href="#" style={{ color: 'inherit', textDecoration: 'none' }}>Bảng giá</a></li>
              <li><a href="#" style={{ color: 'inherit', textDecoration: 'none' }}>Case Studies</a></li>
            </ul>
          </div>

          <div>
            <h4 style={{ color: '#fff', fontSize: '1.2rem', marginBottom: '1.5rem', fontFamily: 'Montserrat' }}>Liên hệ</h4>
            <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '1rem', color: 'var(--text-muted)' }}>
              <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><MapPin size={16} /> Trường Đại học FPT Hà Nội, Km 29 Đại Lộ Thăng Long, Xã Hòa Lạc, Thành phố Hà Nội</li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Mail size={16} /> adminqsmartenergy@gmail.com</li>
              <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Phone size={16} /> 0782097999</li>
            </ul>
          </div>
          
        </div>
        
        <div style={{ textAlign: "center", paddingTop: "2rem", borderTop: "1px solid rgba(255,255,255,0.05)", color: "var(--text-muted)", fontSize: "0.9rem" }}>
          © 2026 Q-SmartEnergy by Phá Đảo Thế Giới Ảo. Tất cả các quyền được bảo lưu.
        </div>
      </footer>
    </div>
  );
}
