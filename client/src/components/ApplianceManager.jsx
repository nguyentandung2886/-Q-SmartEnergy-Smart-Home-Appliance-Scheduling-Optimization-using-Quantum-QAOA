import { useRef, useState } from "react";
import { useAppData } from "../AppData";
import { recognizeAppliance } from "../api";
import { computeCandidateHours } from "../scheduleUtils";

// Read-only summary of the allowed run window for a self-scheduling appliance,
// reconstructed from its candidate (valid start) hours + how long it must run.
function windowLabel(appliance) {
  const ch = appliance.candidate_hours ?? [];
  if (ch.length === 0) return "—";
  const end = (ch[ch.length - 1] + appliance.duration_hours) % 24;
  return `${ch[0]}h–${end}h`;
}

// Ước lượng kWh/ngày của 1 thiết bị (dùng cho dòng cha của nhóm — thuần hiển thị).
function dailyKwh(a) {
  return (a.power_w * a.duration_hours * (a.quantity ?? 1)) / 1000;
}

// Chia danh sách "Cố định · tự lên lịch" thành nhóm (cùng group_name) và thiết bị lẻ,
// giữ nguyên thứ tự: nhóm đặt ở vị trí xuất hiện đầu tiên của nó.
function groupFixed(items) {
  const groups = new Map(); // group_name -> [appliance]
  const order = [];         // {type:"single", appliance} | {type:"group", name}
  for (const a of items) {
    if (a.group_name) {
      if (!groups.has(a.group_name)) {
        groups.set(a.group_name, []);
        order.push({ type: "group", name: a.group_name });
      }
      groups.get(a.group_name).push(a);
    } else {
      order.push({ type: "single", appliance: a });
    }
  }
  return { order, groups };
}

// "Cố định · theo nhu cầu" (is_flexible === false): power / số lượng. Giờ dùng không
// còn nhập ở đây — mỗi giờ bấm ON trên Gantt được tính đủ 1 giờ dùng.
function FlexRow({ appliance, onSave, onDelete }) {
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

// "Linh hoạt · tự lên lịch" (is_flexible === true): power / số lượng editable; the
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

// Hàng cha gộp các khung giờ của cùng một thiết bị vật lý (cùng group_name). Mở/đóng để
// hiện các FixedRow con — mỗi con vẫn sửa/xóa độc lập. Xóa cả nhóm = xóa mọi khung.
function GroupRow({ name, items, expanded, onToggle, onSave, onDelete }) {
  const totalKwh = items.reduce((sum, a) => sum + dailyKwh(a), 0);

  function handleDeleteGroup(e) {
    e.stopPropagation();
    if (!window.confirm(`Xóa cả nhóm "${name}" gồm ${items.length} khung giờ? Tất cả ${items.length} thiết bị sẽ bị xóa.`)) return;
    items.forEach((a) => onDelete(a.id));
  }

  return (
    <>
      <tr className="group-row" onClick={onToggle} style={{ cursor: "pointer" }}>
        <td>
          <span style={{ marginRight: "0.5rem" }}>{expanded ? "▼" : "▶"}</span>
          <strong>{name}</strong>
          <span className="tag" style={{ marginLeft: "0.5rem" }}>{items.length} khung</span>
        </td>
        <td colSpan={3} style={{ color: "var(--text-muted)" }}>~{totalKwh.toFixed(2)} kWh/ngày (gộp)</td>
        <td></td>
        <td>
          <button className="row-delete" onClick={handleDeleteGroup}>Xóa nhóm</button>
        </td>
      </tr>
      {expanded && items.map((a) => (
        <FixedRow key={a.id} appliance={a} onSave={onSave} onDelete={onDelete} />
      ))}
    </>
  );
}

/**
 * Appliance list: the type switch at the bottom picks which kind of device is
 * shown (and which add form is active). Each type shows only its own columns —
 * flexible loads (power/quantity) vs. self-scheduling loads
 * (power/allowed window/required hours/quantity).
 */
export default function ApplianceManager({ appliances, totalKwh, onSave, onDelete, onAdd }) {
  const { runOptimize } = useAppData();
  const [newName, setNewName] = useState("");
  const [newPower, setNewPower] = useState(null);
  const [newQty, setNewQty] = useState(null);

  // "flex" = tải theo nhu cầu (is_flexible false). "fixed" = tải tự lên lịch
  // (is_flexible true): khai báo khung giờ được phép chạy + số giờ cần chạy,
  // hệ thống tính candidate_hours cho QAOA.
  const [mode, setMode] = useState("flex");
  // Mỗi khung giờ chạy độc lập của cùng 1 thiết bị: {start, end, duration}. Mặc định 1 khung.
  const [windows, setWindows] = useState([{ start: null, end: null, duration: null }]);
  const [fixedError, setFixedError] = useState("");
  const [addedHint, setAddedHint] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState({});

  // Nhận diện thiết bị từ ảnh nhãn (Gemini Vision) — TÍNH NĂNG THÊM, song song nhập tay.
  const fileInputRef = useRef(null);
  const [recognizing, setRecognizing] = useState(false);
  const [recognizeError, setRecognizeError] = useState("");
  const [recognizeBadge, setRecognizeBadge] = useState(null); // { verified, note } | null

  function readFileAsBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
      reader.onerror = () => reject(new Error("Không đọc được ảnh"));
      reader.readAsDataURL(file);
    });
  }

  async function handleRecognize(e) {
    const file = e.target.files?.[0];
    e.target.value = ""; // cho phép chọn lại cùng ảnh
    if (!file) return;
    setRecognizeError("");
    setRecognizeBadge(null);
    setRecognizing(true);
    try {
      const base64 = await readFileAsBase64(file);
      const res = await recognizeAppliance(base64, file.type || "image/jpeg");
      if (res.error) {
        setRecognizeError(res.error);
        return;
      }
      // Tự động điền — user vẫn sửa tay được sau đó.
      if (res.suggested_name) setNewName(res.suggested_name);
      if (res.suggested_power_w != null) setNewPower(res.suggested_power_w);
      setRecognizeBadge({ verified: res.verified, estimated: res.estimated, note: res.note });
      if (res.suggested_power_w == null) {
        setRecognizeError("Không đọc được công suất từ ảnh. Vui lòng nhập tay công suất.");
      }
    } catch {
      setRecognizeError("Không thể nhận diện ảnh. Vui lòng thử lại hoặc nhập tay.");
    } finally {
      setRecognizing(false);
    }
  }

  const shown = appliances.filter((a) => (mode === "fixed" ? a.is_flexible : !a.is_flexible));
  const fixedGroups = groupFixed(shown);

  function updateWindow(i, field, value) {
    setWindows((ws) => ws.map((w, idx) => (idx === i ? { ...w, [field]: value } : w)));
  }
  function addWindow() {
    setWindows((ws) => [...ws, { start: null, end: null, duration: null }]);
  }
  function removeWindow(i) {
    setWindows((ws) => (ws.length > 1 ? ws.filter((_, idx) => idx !== i) : ws));
  }
  function toggleGroup(name) {
    setExpandedGroups((g) => ({ ...g, [name]: !g[name] }));
  }

  function switchMode(next) {
    setMode(next);
    setFixedError("");
    setAddedHint(false);
  }

  // Sửa/xóa từ các hàng được gọi fire-and-forget (onBlur/onClick). onSave/onDelete (AppData) trả
  // false khi API lỗi thay vì reject — bọc lại để hiện thông báo thân thiện trong thẻ này, không
  // chặn thao tác tiếp theo, và tránh unhandled rejection tràn stack trace.
  async function handleRowSave(id, payload) {
    const ok = await onSave(id, payload);
    if (ok === false) setFixedError("Lỗi khi lưu thay đổi thiết bị. Kiểm tra backend đã chạy chưa?");
  }
  async function handleRowDelete(id) {
    const ok = await onDelete(id);
    if (ok === false) setFixedError("Lỗi khi xóa thiết bị. Kiểm tra backend đã chạy chưa?");
  }

  async function handleAdd(e) {
    e.preventDefault();
    // duration_hours mặc định 1.0: schema backend vẫn yêu cầu, nhưng giá trị này chỉ
    // ảnh hưởng ước lượng ban đầu — hoá đơn thật tính theo số giờ bấm ON trên Gantt.
    const ok = await onAdd({
      name: newName, power_w: Number(newPower), duration_hours: 1.0,
      quantity: Number(newQty), candidate_hours: [], is_flexible: false,
    });
    if (!ok) {
      setFixedError("Không thể thêm thiết bị. Kiểm tra kết nối mạng / backend rồi thử lại.");
      return;
    }
    setFixedError("");
    setNewName(""); setNewPower(100); setNewQty(1);
  }

  async function handleAddFixed(e) {
    e.preventDefault();
    // Tính candidate_hours từng khung, validate tất cả trước khi tạo bất kỳ row nào.
    const computed = windows.map((w) => ({
      duration: Number(w.duration),
      candidate_hours: computeCandidateHours(Number(w.start), Number(w.end), Number(w.duration)),
    }));
    const badIndex = computed.findIndex((c) => c.candidate_hours.length === 0);
    if (badIndex !== -1) {
      setFixedError(`Khung ${badIndex + 1}: khung giờ có thể chạy ngắn hơn số giờ cần chạy. Hãy mở rộng khung hoặc giảm số giờ.`);
      return;
    }
    setFixedError("");

    if (computed.length === 1) {
      // 1 khung: giữ nguyên hành vi cũ — không set group_name (tương thích ngược).
      const ok = await onAdd({
        name: newName, power_w: Number(newPower), duration_hours: computed[0].duration,
        quantity: Number(newQty), candidate_hours: computed[0].candidate_hours, is_flexible: true,
      });
      if (!ok) {
        setFixedError("Không thể thêm thiết bị. Kiểm tra kết nối mạng / backend rồi thử lại.");
        return;
      }
    } else {
      // >= 2 khung: mỗi khung là 1 row riêng (distinct name), cùng group_name để UI gom lại.
      // Tạo tuần tự (await từng cái) để thứ tự hiển thị ổn định.
      for (let i = 0; i < computed.length; i++) {
        const ok = await onAdd({
          name: `${newName} — Khung ${i + 1}`,
          power_w: Number(newPower), duration_hours: computed[i].duration,
          quantity: Number(newQty), candidate_hours: computed[i].candidate_hours,
          is_flexible: true, group_name: newName,
        });
        if (!ok) {
          setFixedError("Không thể thêm thiết bị. Kiểm tra kết nối mạng / backend rồi thử lại.");
          return;
        }
      }
    }

    setNewName(""); setNewPower(100); setNewQty(1);
    setWindows([{ start: 22, end: 6, duration: 4 }]);
    // Thiết bị đã được thêm ở trên (onAdd) — tự tối ưu chỉ là bước tiện lợi. runOptimize không
    // ném lỗi (tự bắt bên trong) mà trả về true/false, nên await ở đây an toàn: 422 (vượt ngưỡng
    // công suất / quá nhiều biến) hiện thông báo thân thiện thay vì để promise reject tràn màn hình.
    const ok = await runOptimize();
    if (ok) {
      setAddedHint(true);
    } else {
      setAddedHint(false);
      setFixedError("Đã thêm thiết bị, nhưng không thể tự tối ưu: tổng công suất có thể vượt ngưỡng cho phép — hãy kiểm tra lại công suất/số lượng thiết bị.");
    }
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
              <th>Số lượng</th><th></th>
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
              <td colSpan={mode === "flex" ? 4 : 6}
                style={{ color: "var(--text-muted)", textAlign: "center", padding: "1rem" }}>
                Chưa có thiết bị {mode === "flex" ? "cố định" : "linh hoạt"} nào.
              </td>
            </tr>
          ) : mode === "flex" ? (
            shown.map((a) => <FlexRow key={a.id} appliance={a} onSave={handleRowSave} onDelete={handleRowDelete} />)
          ) : (
            fixedGroups.order.map((entry) =>
              entry.type === "single" ? (
                <FixedRow key={entry.appliance.id} appliance={entry.appliance} onSave={handleRowSave} onDelete={handleRowDelete} />
              ) : (
                <GroupRow
                  key={`group:${entry.name}`}
                  name={entry.name}
                  items={fixedGroups.groups.get(entry.name)}
                  expanded={!!expandedGroups[entry.name]}
                  onToggle={() => toggleGroup(entry.name)}
                  onSave={handleRowSave}
                  onDelete={handleRowDelete}
                />
              )
            )
          )}
        </tbody>
      </table>
      <div className="add-type-switch">
        <button type="button" onClick={() => switchMode("flex")}
          className={"type-toggle" + (mode === "flex" ? " type-toggle--flex" : "")}>
          Cố định · theo nhu cầu
        </button>
        <button type="button" onClick={() => switchMode("fixed")}
          className={"type-toggle" + (mode === "fixed" ? " type-toggle--flex" : "")}>
          Linh hoạt · tự lên lịch
        </button>
      </div>

      <div className="recognize-block" style={{ margin: "0.75rem 0" }}>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleRecognize}
          style={{ display: "none" }}
        />
        <button
          type="button"
          className="btn-ink"
          disabled={recognizing}
          onClick={() => fileInputRef.current?.click()}
        >
          {recognizing ? "Đang nhận diện..." : "📷 Chụp / tải ảnh nhận diện"}
        </button>
        {recognizeBadge && (
          <span
            className="tag"
            style={{
              marginLeft: "0.6rem",
              background: recognizeBadge.verified
                ? "var(--green, #16a34a)"
                : recognizeBadge.estimated
                ? "var(--blue, #2563eb)"
                : "var(--amber, #d97706)",
              color: "#fff",
            }}
          >
            {recognizeBadge.verified
              ? "✓ Đã xác minh theo catalog"
              : recognizeBadge.estimated
              ? "⚠ Ước tính theo loại thiết bị — kiểm tra lại nếu có tem"
              : "⚠ [CẦN XÁC MINH]"}
          </span>
        )}
        {recognizeError && (
          <p className="add-error" style={{ color: "var(--error)", margin: "0.4rem 0 0" }}>
            {recognizeError}
          </p>
        )}
      </div>

      {mode === "flex" ? (
        <form onSubmit={handleAdd} className="add-form">
          <input placeholder="Tên thiết bị mới" value={newName}
            onChange={(e) => setNewName(e.target.value)} required />
          <input type="number" placeholder="Công suất (W)" value={newPower} min={1}
            onChange={(e) => setNewPower(e.target.value)} required />
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
          <input type="number" placeholder="Số lượng" value={newQty} min={1} step={1}
            onChange={(e) => setNewQty(e.target.value)} required style={{ width: "80px" }} />
          <div className="window-list" style={{ display: "flex", flexDirection: "column", gap: "0.4rem", width: "100%" }}>
            {windows.map((w, i) => (
              <div key={i} className="window-row" style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
                <input type="number" placeholder="Khung giờ: từ (0-23)" value={w.start} min={0} max={23} step={1}
                  onChange={(e) => updateWindow(i, "start", e.target.value)} required style={{ width: "150px" }} />
                <input type="number" placeholder="đến (0-23)" value={w.end} min={0} max={23} step={1}
                  onChange={(e) => updateWindow(i, "end", e.target.value)} required style={{ width: "120px" }} />
                <input type="number" placeholder="Số giờ cần chạy" value={w.duration} min={1} max={24} step={1}
                  onChange={(e) => updateWindow(i, "duration", e.target.value)} required style={{ width: "130px" }} />
                {windows.length > 1 && (
                  <button type="button" className="row-delete" onClick={() => removeWindow(i)} title="Xóa khung giờ này">×</button>
                )}
              </div>
            ))}
            <button type="button" onClick={addWindow}
              style={{ alignSelf: "flex-start", background: "none", border: "1px dashed var(--border, #ccc)",
                cursor: "pointer", padding: "0.3rem 0.6rem", borderRadius: "6px" }}>
              + Thêm khung giờ
            </button>
          </div>
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
