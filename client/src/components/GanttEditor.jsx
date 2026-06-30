import { useEffect, useState } from "react";

const HOURS = Array.from({ length: 24 }, (_, i) => i);

export default function GanttEditor({
  schedule,
  fixedWindows = {},
  appliances,
  onPinnedChange,
  onFixedWindowsChange,
  disabled,
}) {
  // Flexible appliances: single start hour (drag re-optimizes). Fixed appliances: list of usage
  // windows the user can drag to their real habits (drag does NOT re-optimize, only updates display
  // + the power-safety check). Both kept in local state for optimistic updates.
  const [localSchedule, setLocalSchedule] = useState({ ...schedule });
  const [localFixed, setLocalFixed] = useState(fixedWindows);
  const [dragging, setDragging] = useState(null); // { name, index }
  const [dragOverInfo, setDragOverInfo] = useState(null); // { name, hour }
  const [pointerOff, setPointerOff] = useState(false);

  useEffect(() => { setLocalSchedule({ ...schedule }); }, [schedule]);
  useEffect(() => { setLocalFixed(fixedWindows); }, [fixedWindows]);

  function getApp(name) {
    return appliances.find((a) => a.name === name);
  }

  function candidateHours(name) {
    return getApp(name)?.candidate_hours ?? [];
  }

  function blockLength(name, index) {
    const app = getApp(name);
    if (app?.is_flexible) return Math.max(1, Math.ceil(app.duration_hours));
    return (localFixed[name]?.[index]?.[1]) ?? 1;
  }

  // A drop at `hour` is valid if: flexible → hour is a candidate; fixed → the block fits in 0–23.
  function canDropAt(name, index, hour) {
    const app = getApp(name);
    if (app?.is_flexible) {
      const cands = candidateHours(name);
      return cands.length === 0 || cands.includes(hour);
    }
    return hour + blockLength(name, index) <= 24;
  }

  function handleDragStart(e, name, index) {
    setDragging({ name, index });
    e.dataTransfer.setData("text/plain", name);
    e.dataTransfer.effectAllowed = "move";
    requestAnimationFrame(() => setPointerOff(true));
  }

  function handleDragOver(e, rowName, hour) {
    if (!dragging || rowName !== dragging.name) return;
    if (!canDropAt(dragging.name, dragging.index, hour)) return;
    e.preventDefault();
    setDragOverInfo({ name: rowName, hour });
  }

  function handleDragLeave(rowName, hour) {
    if (dragOverInfo?.name === rowName && dragOverInfo?.hour === hour) {
      setDragOverInfo(null);
    }
  }

  function handleDrop(e, rowName, hour) {
    e.preventDefault();
    setDragOverInfo(null);
    setPointerOff(false);
    if (!dragging || rowName !== dragging.name) return;
    const { name, index } = dragging;
    setDragging(null);
    if (!canDropAt(name, index, hour)) return;

    const app = getApp(name);
    if (app?.is_flexible) {
      const newSchedule = { ...localSchedule, [name]: hour };
      setLocalSchedule(newSchedule);
      const pinned = Object.fromEntries(
        Object.entries(newSchedule).filter(([n]) => getApp(n)?.is_flexible)
      );
      onPinnedChange(pinned); // re-optimize for flexible loads
    } else {
      const windows = (localFixed[name] ?? []).map((w, i) =>
        i === index ? [hour, w[1]] : w
      );
      const newFixed = { ...localFixed, [name]: windows };
      setLocalFixed(newFixed);
      onFixedWindowsChange?.(newFixed); // update display + power-safety only (no re-optimize)
    }
  }

  function handleDragEnd() {
    setDragging(null);
    setPointerOff(false);
    setDragOverInfo(null);
  }

  // One row per appliance. Flexible → a single draggable block; fixed → one draggable block per
  // usage window (the user can place each at the hours they actually use the appliance).
  const rows = appliances.map((app) => {
    const flexible = app.is_flexible;
    const blocks = flexible
      ? [{ start: localSchedule[app.name] ?? 0, len: Math.max(1, Math.ceil(app.duration_hours)), index: 0 }]
      : (localFixed[app.name] ?? []).map(([start, len], index) => ({ start, len, index }));
    return { name: app.name, app, flexible, blocks };
  });

  return (
    <div
      className={["gantt-editor", disabled ? "gantt-disabled" : ""].filter(Boolean).join(" ")}
      aria-label="Lịch thiết bị"
    >
      {/* Hour header */}
      <div className="gantt-row gantt-header-row">
        <div className="gantt-label" />
        <div className="gantt-track">
          {HOURS.map((h) => (
            <div key={h} className="gantt-header-cell" style={{ gridColumn: h + 1 }}>
              {h}
            </div>
          ))}
        </div>
      </div>

      {/* Appliance rows */}
      {rows.map(({ name, app, flexible, blocks }) => {
        const cands = candidateHours(name);
        const draggableRow = !disabled;

        return (
          <div key={name} className="gantt-row">
            <div className="gantt-label" title={name}>
              {name.length > 16 ? name.slice(0, 15) + "…" : name}
              {flexible
                ? <span className="gantt-flex-badge" title="Tự động tối ưu">⟳</span>
                : <span className="gantt-flex-badge" title="Kéo để đặt giờ dùng" style={{ color: "var(--text-muted)" }}>⠿</span>}
            </div>
            <div className="gantt-track">
              {/* Drop-zone / grid cells (z-index 1) */}
              {HOURS.map((h) => {
                const isCandidate = flexible ? (cands.length === 0 || cands.includes(h)) : true;
                const isHover = dragOverInfo?.name === name && dragOverInfo?.hour === h;
                return (
                  <div
                    key={h}
                    className={[
                      "gantt-cell",
                      flexible && isCandidate ? "gantt-cell-valid" : "",
                      isHover ? "gantt-cell-hover" : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    style={{ gridColumn: h + 1 }}
                    onDragOver={draggableRow ? (e) => handleDragOver(e, name, h) : undefined}
                    onDragLeave={draggableRow ? () => handleDragLeave(name, h) : undefined}
                    onDrop={draggableRow ? (e) => handleDrop(e, name, h) : undefined}
                  />
                );
              })}
              {/* Blocks (z-index 2) — each independently draggable */}
              {blocks.map((block) => {
                const isBeingDragged =
                  dragging?.name === name && dragging?.index === block.index;
                return (
                  <div
                    key={block.index}
                    className={[
                      "gantt-block",
                      flexible ? "gantt-block-flex" : "gantt-block-fixed",
                      isBeingDragged ? "gantt-block-dragging" : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    style={{
                      gridColumn: `${block.start + 1} / span ${block.len}`,
                      pointerEvents: isBeingDragged && pointerOff ? "none" : "auto",
                      cursor: draggableRow ? "grab" : "default",
                    }}
                    draggable={draggableRow}
                    onDragStart={
                      draggableRow ? (e) => handleDragStart(e, name, block.index) : undefined
                    }
                    onDragEnd={handleDragEnd}
                    title={
                      flexible
                        ? `${name}: ${block.start}h – ${block.start + block.len}h (kéo để tối ưu lại)`
                        : `${name}: ${block.start}h – ${block.start + block.len}h (kéo để đặt giờ dùng)`
                    }
                  />
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
