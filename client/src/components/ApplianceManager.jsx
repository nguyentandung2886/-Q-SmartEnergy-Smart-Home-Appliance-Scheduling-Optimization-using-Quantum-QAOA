import { useState } from "react";
import { useAppData } from "../AppData";
import { computeCandidateHours } from "../scheduleUtils";

function ApplianceRow({ appliance, onSave, onDelete }) {
  const [power, setPower] = useState(appliance.power_w);
  const [duration, setDuration] = useState(appliance.duration_hours);
  const [quantity, setQuantity] = useState(appliance.quantity ?? 1);

  function save(overrides = {}) {
    onSave(appliance.id, {
      ...appliance,
      power_w: Number(power),
      duration_hours: Number(duration),
      quantity: Number(quantity),
      ...overrides,
    });
  }

  function handleBlur() {
    const changed =
      Number(power) !== appliance.power_w ||
      Number(duration) !== appliance.duration_hours ||
      Number(quantity) !== (appliance.quantity ?? 1);
    if (changed) save();
  }

  function toggleFlexible() {
    save({ is_flexible: !appliance.is_flexible });
  }

  return (
    <tr>
      <td>{appliance.name}</td>
      <td>
        <input type="number" value={power} min={1}
          onChange={(e) => setPower(e.target.value)} onBlur={handleBlur} />
      </td>
      <td>
        <input type="number" value={duration} min={0.1} step={0.1}
          onChange={(e) => setDuration(e.target.value)} onBlur={handleBlur} />
      </td>
      <td>
        <input type="number" value={quantity} min={1} step={1}
          onChange={(e) => setQuantity(e.target.value)} onBlur={handleBlur} />
      </td>
      <td>
        <button
          onClick={toggleFlexible}
          className={"type-toggle" + (appliance.is_flexible ? " type-toggle--flex" : "")}
          title="Bấm để đổi loại"
        >
          {appliance.is_flexible ? "Cố định · tự lên lịch" : "Linh hoạt · theo nhu cầu"}
        </button>
      </td>
      <td>
        <button className="row-delete" onClick={() => onDelete(appliance.id)}>Xóa</button>
      </td>
    </tr>
  );
}

/**
 * Appliance list: editable rows (power/duration/quantity/type) plus the add
 * form for a new fixed appliance. Add-form input state is local to this card.
 */
export default function ApplianceManager({ appliances, totalKwh, onSave, onDelete, onAdd }) {
  const { runOptimize } = useAppData();
  const [newName, setNewName] = useState("");
  const [newPower, setNewPower] = useState(100);
  const [newDuration, setNewDuration] = useState(1);
  const [newQty, setNewQty] = useState(1);

  // "flex" = tải theo nhu cầu (form cũ). "fixed" = tải tự lên lịch: khai báo khung
  // giờ được phép chạy + số giờ cần chạy, hệ thống tính candidate_hours cho QAOA.
  const [mode, setMode] = useState("flex");
  const [useStart, setUseStart] = useState(22);
  const [useEnd, setUseEnd] = useState(6);
  const [needDuration, setNeedDuration] = useState(4);
  const [fixedError, setFixedError] = useState("");
  const [addedHint, setAddedHint] = useState(false);

  function switchMode(next) {
    setMode(next);
    setFixedError("");
    setAddedHint(false);
  }

  async function handleAdd(e) {
    e.preventDefault();
    await onAdd({
      name: newName, power_w: Number(newPower), duration_hours: Number(newDuration),
      quantity: Number(newQty), candidate_hours: [], is_flexible: false,
    });
    setNewName(""); setNewPower(100); setNewDuration(1); setNewQty(1);
  }

  async function handleAddFixed(e) {
    e.preventDefault();
    const candidate_hours = computeCandidateHours(Number(useStart), Number(useEnd), Number(needDuration));
    if (candidate_hours.length === 0) {
      setFixedError("Khung giờ có thể chạy ngắn hơn số giờ cần chạy. Hãy mở rộng khung hoặc giảm số giờ.");
      return;
    }
    setFixedError("");
    await onAdd({
      name: newName, power_w: Number(newPower), duration_hours: Number(needDuration),
      quantity: Number(newQty), candidate_hours, is_flexible: true,
    });
    setNewName(""); setNewPower(100); setNewQty(1);
    setUseStart(22); setUseEnd(6); setNeedDuration(4);
    setAddedHint(true);
    runOptimize();
  }

  return (
    <div className="card">
      <div className="card-head">
        <h3>Danh sách thiết bị</h3>
        <span className="tag tag--green">~{totalKwh.toFixed(0)} kWh/tháng</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>Tên thiết bị</th><th>Công suất (W)</th>
            <th>Giờ dùng</th><th>Số lượng</th><th>Loại</th><th></th>
          </tr>
        </thead>
        <tbody>
          {appliances.map((a) => (
            <ApplianceRow key={a.id} appliance={a} onSave={onSave} onDelete={onDelete} />
          ))}
        </tbody>
      </table>
      <div className="add-type-switch">
        <button type="button" onClick={() => switchMode("flex")}
          className={"type-toggle" + (mode === "flex" ? " type-toggle--flex" : "")}>
          Linh hoạt · theo nhu cầu
        </button>
        <button type="button" onClick={() => switchMode("fixed")}
          className={"type-toggle" + (mode === "fixed" ? " type-toggle--flex" : "")}>
          + Cố định · tự lên lịch
        </button>
      </div>

      {mode === "flex" ? (
        <form onSubmit={handleAdd} className="add-form">
          <input placeholder="Tên thiết bị mới" value={newName}
            onChange={(e) => setNewName(e.target.value)} required />
          <input type="number" placeholder="Công suất (W)" value={newPower} min={1}
            onChange={(e) => setNewPower(e.target.value)} required />
          <input type="number" placeholder="Giờ/ngày" value={newDuration} min={0.1} step={0.1}
            onChange={(e) => setNewDuration(e.target.value)} required />
          <input type="number" placeholder="Số lượng" value={newQty} min={1} step={1}
            onChange={(e) => setNewQty(e.target.value)} required style={{ width: "80px" }} />
          <button className="btn-ink" type="submit">Thêm thiết bị</button>
        </form>
      ) : (
        <form onSubmit={handleAddFixed} className="add-form">
          <input placeholder="Tên thiết bị mới" value={newName}
            onChange={(e) => setNewName(e.target.value)} required />
          <input type="number" placeholder="Công suất (W)" value={newPower} min={1}
            onChange={(e) => setNewPower(e.target.value)} required />
          <input type="number" placeholder="Khung giờ: từ (0-23)" value={useStart} min={0} max={23} step={1}
            onChange={(e) => setUseStart(e.target.value)} required style={{ width: "150px" }} />
          <input type="number" placeholder="đến (0-23)" value={useEnd} min={0} max={23} step={1}
            onChange={(e) => setUseEnd(e.target.value)} required style={{ width: "120px" }} />
          <input type="number" placeholder="Số giờ cần chạy" value={needDuration} min={1} max={24} step={1}
            onChange={(e) => setNeedDuration(e.target.value)} required style={{ width: "130px" }} />
          <input type="number" placeholder="Số lượng" value={newQty} min={1} step={1}
            onChange={(e) => setNewQty(e.target.value)} required style={{ width: "80px" }} />
          <button className="btn-ink" type="submit">Thêm thiết bị</button>
        </form>
      )}

      {fixedError && <p className="add-error" style={{ color: "var(--error)", margin: "0.5rem 0 0" }}>{fixedError}</p>}
      {addedHint && (
        <p className="add-hint" style={{ margin: "0.5rem 0 0" }}>
          Đã thêm thiết bị. Mở tab <strong>Tối ưu hóa</strong> để xem giờ chạy được xếp trong khung cho phép.
        </p>
      )}
    </div>
  );
}
