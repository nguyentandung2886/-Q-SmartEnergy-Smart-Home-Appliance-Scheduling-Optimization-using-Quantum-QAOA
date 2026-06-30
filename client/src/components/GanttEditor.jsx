import { useEffect, useState } from "react";

const HOURS = Array.from({ length: 24 }, (_, i) => i);

export default function GanttEditor({ schedule, appliances, onPinnedChange, disabled }) {
  const [localSchedule, setLocalSchedule] = useState({ ...schedule });
  const [draggingName, setDraggingName] = useState(null);
  const [dragOverInfo, setDragOverInfo] = useState(null); // { rowName, hour }
  const [pointerOff, setPointerOff] = useState(false);

  // Sync local schedule when QAOA returns a new result
  useEffect(() => {
    setLocalSchedule({ ...schedule });
  }, [schedule]);

  function getApp(name) {
    return appliances.find((a) => a.name === name);
  }

  function candidateHours(name) {
    return getApp(name)?.candidate_hours ?? [];
  }

  function isValidHour(name, hour) {
    const cands = candidateHours(name);
    return cands.length === 0 || cands.includes(hour);
  }

  function handleDragStart(e, name) {
    setDraggingName(name);
    e.dataTransfer.setData("text/plain", name);
    e.dataTransfer.effectAllowed = "move";
    // Delay pointer-events removal by one frame so the browser
    // captures the drag ghost image before cells take over events.
    requestAnimationFrame(() => setPointerOff(true));
  }

  function handleDragOver(e, rowName, hour) {
    if (!draggingName || rowName !== draggingName) return;
    if (!isValidHour(draggingName, hour)) return;
    e.preventDefault();
    setDragOverInfo({ rowName, hour });
  }

  function handleDragLeave(rowName, hour) {
    if (dragOverInfo?.rowName === rowName && dragOverInfo?.hour === hour) {
      setDragOverInfo(null);
    }
  }

  function handleDrop(e, rowName, hour) {
    e.preventDefault();
    setDragOverInfo(null);
    setPointerOff(false);
    if (!draggingName || rowName !== draggingName) return;
    if (!isValidHour(draggingName, hour)) return;

    const newSchedule = { ...localSchedule, [draggingName]: hour };
    setLocalSchedule(newSchedule); // optimistic update
    setDraggingName(null);

    // Report only flexible appliances as pinned
    const pinned = Object.fromEntries(
      Object.entries(newSchedule).filter(([n]) => getApp(n)?.is_flexible)
    );
    onPinnedChange(pinned);
  }

  function handleDragEnd() {
    setDraggingName(null);
    setPointerOff(false);
    setDragOverInfo(null);
  }

  const rows = Object.entries(localSchedule).map(([name, startHour]) => ({
    name,
    startHour,
    app: getApp(name),
  }));

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
      {rows.map(({ name, startHour, app }) => {
        const flexible = app?.is_flexible ?? false;
        const duration = Math.max(1, Math.ceil(app?.duration_hours ?? 1));
        const cands = candidateHours(name);
        const isBeingDragged = draggingName === name;

        return (
          <div key={name} className="gantt-row">
            <div className="gantt-label" title={name}>
              {name.length > 16 ? name.slice(0, 15) + "…" : name}
              {flexible && <span className="gantt-flex-badge">⟳</span>}
            </div>
            <div className="gantt-track">
              {/* Drop-zone cells (z-index 1) */}
              {HOURS.map((h) => {
                const isCandidate = cands.length === 0 || cands.includes(h);
                const isHover =
                  dragOverInfo?.rowName === name && dragOverInfo?.hour === h;
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
                    onDragOver={
                      flexible && !disabled ? (e) => handleDragOver(e, name, h) : undefined
                    }
                    onDragLeave={
                      flexible && !disabled ? () => handleDragLeave(name, h) : undefined
                    }
                    onDrop={
                      flexible && !disabled ? (e) => handleDrop(e, name, h) : undefined
                    }
                  />
                );
              })}
              {/* Block (z-index 2, spans duration columns) */}
              <div
                className={[
                  "gantt-block",
                  flexible ? "gantt-block-flex" : "gantt-block-fixed",
                  isBeingDragged ? "gantt-block-dragging" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                style={{
                  gridColumn: `${startHour + 1} / span ${duration}`,
                  pointerEvents: isBeingDragged && pointerOff ? "none" : "auto",
                }}
                draggable={flexible && !disabled}
                onDragStart={
                  flexible && !disabled ? (e) => handleDragStart(e, name) : undefined
                }
                onDragEnd={handleDragEnd}
                title={`${name}: ${startHour}h – ${startHour + duration}h`}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
