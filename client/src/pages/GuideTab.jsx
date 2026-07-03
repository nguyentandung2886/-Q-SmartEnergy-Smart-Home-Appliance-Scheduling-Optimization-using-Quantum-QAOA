import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getMe } from "../api";

export default function GuideTab() {
  // Business accounts don't have the Dự báo tab (see AppLayout/RequireHousehold), so hide its
  // guide section for them to avoid pointing at a feature they can't reach.
  const [role, setRole] = useState(null);

  useEffect(() => {
    getMe()
      .then((me) => setRole(me.role))
      .catch(() => setRole(null));
  }, []);

  // Business bỏ bước "Dự báo" nên số bước và cách đánh số các card sau đó lùi lại một.
  const isBusiness = role === "business";

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <div className="page-head">
        <p className="eyebrow">Bắt đầu</p>
        <h1>Hướng dẫn sử dụng</h1>
        <p className="page-sub">
          {isBusiness ? (
            <>
              Ba bước để tối ưu hóa lịch dùng điện với Q-SmartEnergy: khai báo thiết bị, chạy tối ưu
              và đọc kết quả. Làm theo đúng thứ tự các tab bên dưới.
            </>
          ) : (
            <>
              Bốn bước để tối ưu hóa lịch dùng điện với Q-SmartEnergy: khai báo thiết bị, xem dự báo,
              chạy tối ưu và đọc kết quả. Làm theo đúng thứ tự các tab bên dưới.
            </>
          )}
        </p>
      </div>

      <div className="bento">
        <div className="card">
          <div className="card-head">
            <h3>1. Thiết bị</h3>
            <span className="tag">Tab Thiết bị</span>
          </div>
          <p>
            Khai báo các thiết bị điện trong nhà. Mỗi thiết bị có hai loại, chọn bằng nút gạt ở cột
            <strong> Loại</strong> hoặc khi thêm mới:
          </p>
          <ul>
            <li>
              <strong>Cố định · theo nhu cầu</strong>: thiết bị dùng theo thói quen (đèn, TV…).
              Bạn nhập công suất (W), số giờ dùng/ngày và số lượng.
            </li>
            <li>
              <strong>Linh hoạt · tự lên lịch</strong>: thiết bị có thể để hệ thống chọn giờ chạy
              (máy giặt, máy bơm, sạc xe…). Bạn nhập công suất, <strong>khung giờ có thể chạy</strong>
              (từ / đến) và <strong>số giờ cần chạy</strong>; hệ thống sẽ tự xếp giờ trong khung đó.
            </li>
          </ul>
          <p className="hint">
            Bấm <strong>Thêm thiết bị</strong> để lưu. Ô trên cùng hiển thị tổng ước tính kWh/tháng.
          </p>
        </div>

        {role !== "business" && (
          <div className="card">
            <div className="card-head">
              <h3>2. Dự báo</h3>
              <span className="tag">Tab Dự báo</span>
            </div>
            <p>
              Xem dự báo thời tiết theo vị trí của bạn cho hôm nay và các ngày tới. Thời tiết (nắng,
              nhiều mây, mưa) quyết định lượng điện mặt trời tự sản xuất, và ảnh hưởng đến cách thuật
              toán xếp các tải linh hoạt vào khung giờ có nắng.
            </p>
          </div>
        )}

        <div className="card">
          <div className="card-head">
            <h3>{isBusiness ? "2" : "3"}. Tối ưu hóa</h3>
            <span className="tag">Tab Tối ưu hóa</span>
          </div>
          <p>
            Chọn <strong>ngày tối ưu</strong> (Hôm nay, Ngày mai hoặc một ngày trong 5 ngày tới),
            thời tiết được lấy tự động cho ngày đó. Bấm <strong>Tối ưu hóa</strong> để thuật toán
            QAOA sắp xếp lịch chạy.
          </p>
          <p>Sau khi chạy xong, bạn sẽ thấy:</p>
          <ul>
            <li>
              Dải <strong>Hóa đơn trước → Sau tối ưu</strong> và phần trăm tiết kiệm.
            </li>
            <li>
              Biểu đồ <strong>Gantt</strong> giờ chạy của từng thiết bị. Tải linh hoạt: kéo khối để
              đổi giờ và tối ưu lại. Tải cố định: bấm vào ô giờ để bật/tắt theo nhu cầu thật (có thể
              chọn nhiều khung giờ rời nhau).
            </li>
          </ul>
        </div>

        <div className="card">
          <div className="card-head">
            <h3>Ý nghĩa các badge</h3>
          </div>
          <ul>
            <li>
              <span className="tag tag--green">An toàn công suất</span> — tổng công suất dùng cùng
              lúc luôn dưới ngưỡng an toàn. Nếu vượt ngưỡng, badge chuyển thành cảnh báo
              <strong> Quá tải</strong> kèm giờ và tên thiết bị gây quá tải.
            </li>
            <li>
              <span className="tag bill-num--save" style={{ padding: "0.2rem 0.5rem" }}>↓ %</span> —
              phần trăm hóa đơn tiết kiệm được so với trước khi tối ưu.
            </li>
            <li>
              Badge <strong>solver</strong> cho biết bộ giải đã dùng (kèm <em>fallback</em> nếu QAOA
              lùi về phương án dự phòng).
            </li>
          </ul>
        </div>

        <div className="card">
          <div className="card-head">
            <h3>{isBusiness ? "3" : "4"}. Tổng quan & Lịch sử</h3>
            <span className="tag">Tab Tổng quan</span>
          </div>
          <p>
            Tab <strong>Tổng quan</strong> tổng hợp tình hình tiêu thụ và tiết kiệm của bạn. Để xem
            lại các lần tối ưu trước đó, bấm nút <strong>Lịch sử</strong> ở góc trên bên phải thanh
            điều hướng.
          </p>
        </div>
      </div>
    </motion.div>
  );
}
