import { useState } from "react";

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
          style={{
            background: "none", cursor: "pointer", padding: "2px 6px",
            borderRadius: "4px", fontSize: "0.8rem", fontWeight: 600,
            color: appliance.is_flexible ? "var(--teal)" : "var(--text-muted)",
            border: `1px solid ${appliance.is_flexible ? "var(--teal)" : "#d1d5db"}`,
          }}
          title="Bấm để đổi loại"
        >
          {appliance.is_flexible ? "Linh hoạt" : "Cố định"}
        </button>
      </td>
      <td>
        <button onClick={() => onDelete(appliance.id)}>Xóa</button>
      </td>
    </tr>
  );
}

/**
 * Appliance list: editable rows (power/duration/quantity/type) plus the add
 * form for a new fixed appliance. Add-form input state is local to this card.
 */
export default function ApplianceManager({ appliances, totalKwh, onSave, onDelete, onAdd }) {
  const [newName, setNewName] = useState("");
  const [newPower, setNewPower] = useState(100);
  const [newDuration, setNewDuration] = useState(1);
  const [newQty, setNewQty] = useState(1);

  async function handleAdd(e) {
    e.preventDefault();
    await onAdd({
      name: newName, power_w: Number(newPower), duration_hours: Number(newDuration),
      quantity: Number(newQty), candidate_hours: [], is_flexible: false,
    });
    setNewName(""); setNewPower(100); setNewDuration(1); setNewQty(1);
  }

  return (
    <div className="section-card">
      <h2>Thiết bị của bạn — tổng ~{totalKwh.toFixed(0)} kWh/tháng</h2>
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
      <form onSubmit={handleAdd} className="add-form">
        <input placeholder="Tên thiết bị mới" value={newName}
          onChange={(e) => setNewName(e.target.value)} required />
        <input type="number" placeholder="Công suất (W)" value={newPower} min={1}
          onChange={(e) => setNewPower(e.target.value)} required />
        <input type="number" placeholder="Giờ/ngày" value={newDuration} min={0.1} step={0.1}
          onChange={(e) => setNewDuration(e.target.value)} required />
        <input type="number" placeholder="Số lượng" value={newQty} min={1} step={1}
          onChange={(e) => setNewQty(e.target.value)} required style={{ width: "80px" }} />
        <button type="submit">+ Thêm thiết bị</button>
      </form>
    </div>
  );
}
