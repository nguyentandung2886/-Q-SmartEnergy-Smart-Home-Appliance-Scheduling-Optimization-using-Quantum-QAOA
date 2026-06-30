import { useEffect, useState } from "react";

const HOURS = Array.from({ length: 24 }, (_, i) => i);

export default function GanttEditor({
  schedule,
  fixedHours = {},
  appliances,
  onPinnedChange,
  onFixedHoursChange,
  disabled,
}) {
  // Flexible appliances: a single block at the QAOA hour, dragged within candidate hours
  // (drag re-optimizes). Fixed appliances: a 24-cell ON/OFF grid the user clicks to set their
  // real usage — any combination of hours, including several disjoint intervals (e.g. AC 0–3h
  // and 10–13h). Editing fixed hours updates the display + power-safety check, not the bill.
  const [localSchedule, setLocalSchedule] = useState({ ...schedule });
  const [localFixedHours, setLocalFixedHours] = useState(fixedHours);
  const [draggingName, setDraggingName] = useState(null);
  const [dragOverInfo, setDragOverInfo] = useState(null); // { name, hour }
  const [pointerOff, setPointerOff] = useState(false);

  useEffect(() => { setLocalSchedule({ ...schedule }); }, [schedule]);
  useEffect(() => { setLocalFixedHours(fixedHours); }, [fixedHours]);

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

  // ── Flexible appliances: drag a single block ───────────────────────────
  function handleDragStart(e, name) {
    setDraggingName(name);
    e.dataTransfer.setData("text/plain", name);
    e.dataTransfer.effectAllowed = "move";
    requestAnimationFrame(() => setPointerOff(true));
  }

  function handleDragOver(e, rowName, hour) {
    if (!draggingName || rowName !== draggingName) return;
    if (!isValidHour(draggingName, hour)) return;
    e.preventDefault();
    setDragOverInfo({ name: rowName, hour });
  }

  function handleDragLeave(rowName, hour) {
    if (dragOverInfo?.name === rowName && dragOverInfo?.hour === hour) setDragOverInfo(null);
  }

  function handleDrop(e, rowName, hour) {
    e.preventDefault();
    setDragOverInfo(null);
    setPointerOff(false);
    if (!draggingName || rowName !== draggingName) return;
    if (!isValidHour(draggingName, hour)) return;
    const newSchedule = { ...localSchedule, [draggingName]: hour };
    setLocalSchedule(newSchedule);
    setDraggingName(null);
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

  // ── Fixed appliances: click an hour cell to toggle ON/OFF ──────────────
  function toggleHour(name, hour) {
    if (disabled) return;
    const cur = new Set(localFixedHours[name] ?? []);
    cur.has(hour) ? cur.delete(hour) : cur.add(hour);
    const next = { ...localFixedHours, [name]: [...cur].sort((a, b) => a - b) };
    setLocalFixedHours(next);
    onFixedHoursChange?.(next);
  }

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
      {appliances.map((app) => {
        const name = app.name;
        const flexible = app.is_flexible;
        const cands = candidateHours(name);
        const isBeingDragged = draggingName === name;
        const onHours = new Set(localFixedHours[name] ?? []);
        const blockStart = localSchedule[name] ?? 0;
        const blockLen = Math.max(1, Math.ceil(app.duration_hours));

        return (
          <div key={name} className="gantt-row">
            <div className="gantt-label" title={name}>
              {name.length > 16 ? name.slice(0, 15) + "…" : name}
              {flexible
                ? <span className="gantt-flex-badge" title="Tự động tối ưu">⟳</span>
                : <span className="gantt-flex-badge" title="Bấm ô giờ để bật/tắt" style={{ color: "var(--text-muted)" }}>⠿</span>}
            </div>
            <div className="gantt-track">
              {HOURS.map((h) => {
                if (flexible) {
                  const isCandidate = cands.length === 0 || cands.includes(h);
                  const isHover = dragOverInfo?.name === name && dragOverInfo?.hour === h;
                  return (
                    <div
                      key={h}
                      className={[
                        "gantt-cell",
                        isCandidate ? "gantt-cell-valid" : "",
                        isHover ? "gantt-cell-hover" : "",
                      ].filter(Boolean).join(" ")}
                      style={{ gridColumn: h + 1 }}
                      onDragOver={!disabled ? (e) => handleDragOver(e, name, h) : undefined}
                      onDragLeave={!disabled ? () => handleDragLeave(name, h) : undefined}
                      onDrop={!disabled ? (e) => handleDrop(e, name, h) : undefined}
                    />
                  );
                }
                // Fixed appliance: clickable ON/OFF cell
                return (
                  <div
                    key={h}
                    className={[
                      "gantt-cell",
                      "gantt-cell-clickable",
                      onHours.has(h) ? "gantt-cell-on" : "",
                    ].filter(Boolean).join(" ")}
                    style={{ gridColumn: h + 1 }}
                    title={`${name}: ${h}h — bấm để ${onHours.has(h) ? "tắt" : "bật"}`}
                    onClick={() => toggleHour(name, h)}
                  />
                );
              })}
              {/* Flexible appliances get a draggable block on top of the cells */}
              {flexible && (
                <div
                  className={[
                    "gantt-block",
                    "gantt-block-flex",
                    isBeingDragged ? "gantt-block-dragging" : "",
                  ].filter(Boolean).join(" ")}
                  style={{
                    gridColumn: `${blockStart + 1} / span ${blockLen}`,
                    pointerEvents: isBeingDragged && pointerOff ? "none" : "auto",
                  }}
                  draggable={!disabled}
                  onDragStart={!disabled ? (e) => handleDragStart(e, name) : undefined}
                  onDragEnd={handleDragEnd}
                  title={`${name}: ${blockStart}h – ${blockStart + blockLen}h (kéo để tối ưu lại)`}
                />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
