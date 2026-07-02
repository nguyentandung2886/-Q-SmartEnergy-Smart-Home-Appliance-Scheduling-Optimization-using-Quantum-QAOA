import { useState } from "react";
import { useAppData } from "../AppData";
import { computeCandidateHours } from "../scheduleUtils";

// Read-only summary of the allowed run window for a self-scheduling appliance,
// reconstructed from its candidate (valid start) hours + how long it must run.
function windowLabel(appliance) {
  const ch = appliance.candidate_hours ?? [];
  if (ch.length === 0) return "—";
  const end = (ch[ch.length - 1] + appliance.duration_hours) % 24;
  return `${ch[0]}h–${end}h`;
}

// "Linh hoạt · theo nhu cầu" (is_flexible === false): power / giờ dùng / số lượng.
function FlexRow({ appliance, onSave, onDelete }) {
  const [power, setPower] = useState(appliance.power_w);
  const [duration, setDuration] = useState(appliance.duration_hours);
  const [quantity, setQuantity] = useState(appliance.quantity ?? 1);

  function handleBlur() {
    const changed =
      Number(power) !== appliance.power_w ||
      Number(duration) !== appliance.duration_hours ||
      Number(quantity) !== (appliance.quantity ?? 1);
    if (changed) {
      onSave(appliance.id, {
        ...appliance,
        power_w: Number(power),
        duration_hours: Number(duration),
        quantity: Number(quantity),
      });
    }
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
        <button className="row-delete" onClick={() => onDelete(appliance.id)}>Xóa</button>
      </td>
    </tr>
  );
}

// "Cố định · tự lên lịch" (is_flexible === true): power / số lượng editable; the
// allowed window + required hours are read-only (change by re-adding the device).
function FixedRow({ appliance, onSave, onDelete }) {
  const [power, setPower] = useState(appliance.power_w);
  const [quantity, setQuantity] = useState(appliance.quantity ?? 1);

  function handleBlur() {
    const changed =
      Number(power) !== appliance.power_w ||
      Number(quantity) !== (appliance.quantity ?? 1);
    if (changed) {
      onSave(appliance.id, {
        ...appliance,
        power_w: Number(power),
        quantity: Number(quantity),
      });
    }
  }

  return (
    <tr>
      <td>{appliance.name}</td>
      <td>
        <input type="number" value={power} min={1}
          onChange={(e) => setPower(e.target.value)} onBlur={handleBlur} />
      </td>
      <td>{windowLabel(appliance)}</td>
      <td>{appliance.duration_hours}h</td>
      <td>
        <input type="number" value={quantity} min={1} step={1}
          onChange={(e) => setQuantity(e.target.value)} onBlur={handleBlur} />
      </td>
      <td>
        <button className="row-delete" onClick={() => onDelete(appliance.id)}>Xóa</button>
      </td>
    </tr>
  );
}

/**
 * Appliance list: the type switch at the bottom picks which kind of device is
 * shown (and which add form is active). Each type shows only its own columns —
 * flexible loads (power/duration/quantity) vs. self-scheduling loads
 * (power/allowed window/required hours/quantity).
 */
export default function ApplianceManager({ appliances, totalKwh, onSave, onDelete, onAdd }) {
  const { runOptimize } = useAppData();
  const [newName, setNewName] = useState("");
  const [newPower, setNewPower] = useState(100);
  const [newDuration, setNewDuration] = useState(1);
  const [newQty, setNewQty] = useState(1);

  // "flex" = tải theo nhu cầu (is_flexible false). "fixed" = tải tự lên lịch
  // (is_flexible true): khai báo khung giờ được phép chạy + số giờ cần chạy,
  // hệ thống tính candidate_hours cho QAOA.
  const [mode, setMode] = useState("flex");
  const [useStart, setUseStart] = useState(22);
  const [useEnd, setUseEnd] = useState(6);
  const [needDuration, setNeedDuration] = useState(4);
  const [fixedError, setFixedError] = useState("");
  const [addedHint, setAddedHint] = useState(false);

  const shown = appliances.filter((a) => (mode === "fixed" ? a.is_flexible : !a.is_flexible));

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
          {mode === "flex" ? (
            <tr>
              <th>Tên thiết bị</th><th>Công suất (W)</th>
              <th>Giờ dùng</th><th>Số lượng</th><th></th>
            </tr>
          ) : (
            <tr>
              <th>Tên thiết bị</th><th>Công suất (W)</th>
              <th>Khung giờ chạy</th><th>Số giờ cần chạy</th><th>Số lượng</th><th></th>
            </tr>
          )}
        </thead>
        <tbody>
          {shown.length === 0 ? (
            <tr>
              <td colSpan={mode === "flex" ? 5 : 6}
                style={{ color: "var(--text-muted)", textAlign: "center", padding: "1rem" }}>
                Chưa có thiết bị {mode === "flex" ? "linh hoạt" : "cố định"} nào.
              </td>
            </tr>
          ) : (
            shown.map((a) =>
              mode === "flex"
                ? <FlexRow key={a.id} appliance={a} onSave={onSave} onDelete={onDelete} />
                : <FixedRow key={a.id} appliance={a} onSave={onSave} onDelete={onDelete} />
            )
          )}
        </tbody>
      </table>
      <div className="add-type-switch">
        <button type="button" onClick={() => switchMode("flex")}
          className={"type-toggle" + (mode === "flex" ? " type-toggle--flex" : "")}>
          Linh hoạt · theo nhu cầu
        </button>
        <button type="button" onClick={() => switchMode("fixed")}
          className={"type-toggle" + (mode === "fixed" ? " type-toggle--flex" : "")}>
          Cố định · tự lên lịch
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
