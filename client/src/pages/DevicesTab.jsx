import { motion } from "framer-motion";
import { useAppData } from "../AppData";
import { useAuth } from "../AuthContext";
import ApplianceManager from "../components/ApplianceManager";

// Khớp COMMERCIAL_SAFETY_MARGIN ở backend (api/optimize_router.py): thương mại cảnh báo sớm hơn.
const COMMERCIAL_SAFETY_MARGIN = 0.8;

export default function DevicesTab() {
  const { appliances, totalKwh, handleSave, handleDelete, handleAdd } = useAppData();
  const { session } = useAuth();

  // Ngưỡng cảnh báo quá tải (kW) cho khách hàng doanh nghiệp — chỉ để hiển thị. Lấy từ metadata
  // đăng ký (role, business_type, contracted_power_kw); household không có banner này.
  const meta = session?.user?.user_metadata ?? {};
  const contractedKw = Number(meta.contracted_power_kw);
  const thresholdKw =
    meta.role === "business" && contractedKw > 0
      ? meta.business_type === "commercial"
        ? contractedKw * COMMERCIAL_SAFETY_MARGIN
        : contractedKw
      : null;

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <div className="page-head">
        <p className="eyebrow">Bước 1</p>
        <h1>Thiết bị trong nhà</h1>
        <p className="page-sub">
          Khai báo công suất, thời lượng dùng và loại tải của từng thiết bị. Tải linh hoạt sẽ được
          thuật toán lượng tử tối ưu giờ chạy; tải cố định giữ nguyên nếp sinh hoạt.
        </p>
      </div>

      {thresholdKw != null && (
        <div
          style={{
            marginBottom: "1rem",
            padding: "0.6rem 0.9rem",
            borderRadius: 8,
            fontSize: "0.85rem",
            fontWeight: 600,
            background: "rgba(99, 102, 241, 0.1)",
            color: "var(--indigo)",
            border: "1px solid rgba(99, 102, 241, 0.3)",
          }}
        >
          Ngưỡng cảnh báo quá tải của bạn: {thresholdKw.toLocaleString("vi-VN")} kW
        </div>
      )}

      <ApplianceManager
        appliances={appliances}
        totalKwh={totalKwh}
        onSave={handleSave}
        onDelete={handleDelete}
        onAdd={handleAdd}
      />
    </motion.div>
  );
}
