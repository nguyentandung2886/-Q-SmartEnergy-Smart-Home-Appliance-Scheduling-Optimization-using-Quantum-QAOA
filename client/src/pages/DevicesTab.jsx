import { motion } from "framer-motion";
import { useAppData } from "../AppData";
import ApplianceManager from "../components/ApplianceManager";

export default function DevicesTab() {
  const { appliances, totalKwh, handleSave, handleDelete, handleAdd } = useAppData();

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
