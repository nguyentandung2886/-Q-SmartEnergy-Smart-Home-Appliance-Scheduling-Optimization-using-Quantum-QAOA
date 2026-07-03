import { useEffect, useRef, useState } from "react";

const HOURS = Array.from({ length: 24 }, (_, i) => i);

export default function GanttEditor({
  schedule,
  fixedHours = {},
  appliances,
  onPinnedChange,
  onFixedHoursChange,
  disabled,
  simulatedTime = null,
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
  // Vị trí CŨ của mỗi khối linh hoạt vừa bị dịch (kéo -> tối ưu lại): { name: giờ_trước }. Dùng để
  // vẽ "bóng mờ" ở chỗ cũ, giúp người xem phân biệt lịch TRƯỚC và SAU khi kéo trên cùng một bảng —
  // nếu không, khối chỉ nhảy sang chỗ mới và giám khảo dễ hiểu nhầm đang xem hai lịch khác nhau.
  const prevScheduleRef = useRef(schedule);
  const [movedFrom, setMovedFrom] = useState({});

  useEffect(() => {
    // So lịch mới với lịch ngay trước đó: khối linh hoạt nào đổi giờ thì ghi lại giờ cũ để vẽ bóng.
    const prev = prevScheduleRef.current || {};
    const moved = {};
    for (const a of appliances) {
      if (!a.is_flexible) continue;
      const before = prev[a.name];
      const after = schedule?.[a.name];
      if (before != null && after != null && before !== after) moved[a.name] = before;
    }
    setMovedFrom(moved);
    setLocalSchedule({ ...schedule });
    prevScheduleRef.current = schedule;
  }, [schedule, appliances]);
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
          {simulatedTime !== null && (
            <div 
              className="time-scanner" 
              style={{ left: `${((simulatedTime + 0.5) / 24) * 100}%` }} 
            />
          )}
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
                const isActive = simulatedTime === h && onHours.has(h);
                return (
                  <div
                    key={h}
                    className={[
                      "gantt-cell",
                      "gantt-cell-clickable",
                      onHours.has(h) ? "gantt-cell-on" : "",
                      isActive ? "gantt-cell-active" : "",
                    ].filter(Boolean).join(" ")}
                    style={{ gridColumn: h + 1 }}
                    title={`${name}: ${h}h — bấm để ${onHours.has(h) ? "tắt" : "bật"}`}
                    onClick={() => toggleHour(name, h)}
                  />
                );
              })}
              {/* Bóng mờ ở vị trí CŨ của khối vừa bị kéo (giờ trước tối ưu), vẽ dưới khối hiện tại. */}
              {flexible && movedFrom[name] != null && (
                <div
                  className="gantt-block gantt-block-ghost"
                  style={{ gridColumn: `${movedFrom[name] + 1} / span ${Math.min(blockLen, 24 - movedFrom[name])}` }}
                  title={`${name}: vị trí trước khi kéo (${movedFrom[name]}h)`}
                />
              )}
              {/* Flexible appliances get a draggable block on top of the cells */}
              {flexible && (() => {
                const movedFromHour = movedFrom[name];
                const len1 = Math.min(blockLen, 24 - blockStart);
                const len2 = blockStart + blockLen > 24 ? (blockStart + blockLen - 24) : 0;
                const renderBlock = (start, len, isPart2) => {
                  const isActive = simulatedTime !== null && simulatedTime >= start && simulatedTime < start + len;
                  return (
                    <div
                      key={`block-${isPart2 ? '2' : '1'}`}
                      className={[
                        "gantt-block",
                        "gantt-block-flex",
                        isBeingDragged ? "gantt-block-dragging" : "",
                        isActive ? "gantt-block-active" : "",
                        movedFromHour != null && !isPart2 ? "gantt-block-moved" : "",
                      ].filter(Boolean).join(" ")}
                      style={{
                        gridColumn: `${start + 1} / span ${len}`,
                        pointerEvents: isBeingDragged && pointerOff ? "none" : "auto",
                        borderLeft: isPart2 ? "none" : undefined,
                        borderRight: (len2 > 0 && !isPart2) ? "none" : undefined,
                        opacity: isPart2 ? 0.7 : 1, // Slight visual cue for the wrapped part
                      }}
                      draggable={!disabled && !isPart2} // Only main block is draggable
                      onDragStart={!disabled && !isPart2 ? (e) => handleDragStart(e, name) : undefined}
                      onDragEnd={!isPart2 ? handleDragEnd : undefined}
                      title={`${name}: ${blockStart}h – ${(blockStart + blockLen) % 24 || 24}h (kéo để tối ưu lại)`}
                    />
                  );
                };

                return (
                  <>
                    {renderBlock(blockStart, len1, false)}
                    {len2 > 0 && renderBlock(0, len2, true)}
                  </>
                );
              })()}
            </div>
          </div>
        );
      })}

      {/* Chú thích chỉ hiện khi vừa có khối bị dịch — tự giải thích trước/sau khi kéo, không cần lời. */}
      {Object.keys(movedFrom).length > 0 && (
        <div className="gantt-legend">
          <span><span className="gantt-swatch gantt-swatch-ghost" /> Vị trí trước khi kéo</span>
          <span><span className="gantt-swatch gantt-swatch-now" /> Vị trí sau tối ưu</span>
        </div>
      )}
    </div>
  );
}
