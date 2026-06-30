# Subsystem 2 Design: Storytelling + Interactive Gantt Editor

**Date:** 2026-06-30  
**Branch:** feature/subsystem2-storytelling-gantt (to be created)  
**Status:** Approved — ready for implementation plan

---

## Overview

Extend the existing Q-SmartEnergy Dashboard with two features:

1. **Interactive Gantt Editor** — replace the static matplotlib PNG with a React drag-and-drop schedule editor. Dragging a flexible appliance to a new time slot triggers a QAOA re-run that pins that appliance and re-optimizes the rest, then auto-saves to history.

2. **Storytelling** — an on-demand "Giải thích kết quả" button that calls the Gemini API and streams a natural-language Vietnamese explanation of why the schedule was chosen and what the savings mean.

**Approach chosen:** Approach A — HTML5 drag native + FastAPI SSE → Gemini API. No new npm packages. One new pip package: `google-generativeai`.

---

## Global Constraints (MUST PRESERVE)

- NEVER use "giờ cao điểm" / "peak hour" / "time-of-use" anywhere (code, comments, strings, variables)
- All baseline numbers imported from `calc.py` — never hard-coded elsewhere
- Palette: only Indigo `#3730A3`, Teal `#0F766E`, Gold `#CA8A04`
- JWT secret from environment variable, never hard-coded
- Passwords bcrypt hashed, never plaintext
- `GEMINI_API_KEY` must come from `server/.env`, never hard-coded in source
- Per-user bill uses user's OWN appliance list total (not static global calc.py numbers)
- `python -O` must NOT silently disable any safety checks

---

## Architecture

```
Client (React)                    Server (FastAPI)              External
─────────────────────────────     ─────────────────────────     ──────────
Dashboard.jsx
  ├── GanttEditor (NEW)  ──drag──→ POST /optimize
  │     24-col grid                 + pinned_schedule param ──→ QAOA pipeline
  │     draggable blocks            → auto-save to schedules
  │     400ms debounce  ←──result── ScheduleOut (unchanged)
  │
  ├── ResultsBillNumbers (unchanged)
  │
  ├── [Giải thích kết quả] ──────→ POST /explain (NEW)  ──────→ Gemini API
  │     button                       SSE stream          ←────── stream chunks
  │     streaming text  ←──SSE────
  │
  └── bill_chart_png (unchanged img tag)
```

---

## Section 1: Backend Changes

### 1a. `optimize_router.py` — pinned_schedule support

Add optional field to `OptimizeRequest`:

```python
class OptimizeRequest(BaseModel):
    day_of_month: int = 9
    weather_condition: str = "sunny"
    use_quantum: bool = True
    pinned_schedule: Optional[Dict[str, int]] = None  # NEW
```

In `optimize()`, before splitting by flexibility:

```python
pinned = payload.pinned_schedule or {}
# Validate: pinned hours must be in candidate_hours
for app in user_appliances:
    if app.name in pinned:
        hour = pinned[app.name]
        if app.candidate_hours and hour not in app.candidate_hours:
            raise HTTPException(422, f"{app.name}: hour {hour} not in candidate_hours")

# Override: pinned appliances become fixed for this run only
def _apply_pins(appliances, pins):
    result = []
    for a in appliances:
        if a.name in pins:
            result.append(Appliance(
                name=a.name, power_w=a.power_w, duration_hours=a.duration_hours,
                candidate_hours=(pins[a.name],), is_flexible=False,
            ))
        else:
            result.append(a)
    return result

user_appliances = _apply_pins(user_appliances, pinned)
```

After QAOA: merge pinned hours into result.schedule:

```python
for name, hour in pinned.items():
    result.schedule[name] = hour
```

### 1b. `routers/explain_router.py` (NEW)

```python
POST /explain
Auth: JWT required (same as /optimize)
Body: ExplainRequest
  - schedule: Dict[str, int]
  - appliances: List[{name, power_w, duration_hours, is_flexible}]
  - bill_before_vnd: float
  - bill_after_vnd: float
  - savings_percent: float
  - weather_condition: str
  - solver_used: str

Response: StreamingResponse, media_type="text/event-stream"
  - Yields: "data: {chunk}\n\n" per Gemini chunk
  - Terminates: "data: [DONE]\n\n"
```

Prompt sent to Gemini (`gemini-2.0-flash`, stream=True):

```
Bạn là trợ lý AI phân tích năng lượng của Q-SmartEnergy. Hãy giải thích kết quả tối ưu hóa
sau đây bằng tiếng Việt tự nhiên, ngắn gọn (4-5 câu). Tập trung vào: tại sao các giờ đó
hợp lý (nắng → solar cao), ý nghĩa tiết kiệm thực tế, và một lời khuyên cụ thể.

Thời tiết: {weather_condition}
Solver: {solver_used}
Lịch tối ưu:
{schedule_lines}
Hóa đơn: {bill_before:,.0f}đ → {bill_after:,.0f}đ (tiết kiệm {savings:.1f}%)
```

`GEMINI_API_KEY` read from environment; raise `RuntimeError` if missing (same pattern as JWT_SECRET).

### 1c. `server/requirements.txt`

Add: `google-generativeai`

### 1d. `server/.env` (not committed)

Add: `GEMINI_API_KEY=<key>`

### 1e. `main.py`

Include `explain_router`:

```python
from routers import auth_router, appliances_router, optimize_router, explain_router
app.include_router(explain_router.router)
```

---

## Section 2: Data Flow

### Flow 1: Drag-and-drop → QAOA re-run

```
1. User kéo "Máy giặt" từ slot 6h → 8h trong GanttEditor
2. GanttEditor.onDrop() → update local display ngay (optimistic UI)
3. Gọi parent: onPinnedChange({ "Máy giặt": 8 })
4. Dashboard debounce 400ms → handleOptimize({ pinned_schedule: {"Máy giặt": 8} })
5. setReoptimizing(true)  ← KHÔNG setResult(null), Gantt vẫn hiện
6. POST /optimize { day_of_month, weather, use_quantum: true, pinned_schedule: {...} }
7. Backend: pin appliance → QAOA trên phần còn lại → merge → lưu DB → trả ScheduleOut
8. setResult(newResult) → GanttEditor + bill numbers re-render
9. setReoptimizing(false)
```

### Flow 2: Storytelling SSE

```
1. User nhấn "Giải thích kết quả"
2. setExplainText(""), setExplainLoading(true)
3. fetch POST /explain với JWT Bearer + result data
4. Backend: build prompt → Gemini stream → SSE chunks
5. Frontend ReadableStream loop: decode → parse "data: " lines → append to explainText
6. "[DONE]" chunk → setExplainLoading(false)
```

### New state in Dashboard

```js
const [pinnedSchedule, setPinnedSchedule] = useState({});
const [reoptimizing, setReoptimizing] = useState(false);
const [explainText, setExplainText] = useState("");
const [explainLoading, setExplainLoading] = useState(false);
```

Reset `pinnedSchedule = {}` when user clicks "Tối ưu hóa" gốc.  
Reset `explainText = ""` when new optimize result arrives.

---

## Section 3: Frontend Components

### GanttEditor.jsx (`client/src/components/GanttEditor.jsx`)

**Props:**
```js
{
  schedule,       // { "Máy giặt": 7, ... } from result.schedule
  appliances,     // user's appliance list (for candidate_hours, duration_hours)
  onPinnedChange, // (pinnedSchedule) => void
  disabled,       // bool — true when reoptimizing
}
```

**Layout:**
```
┌──────────────────┬──────────────────────────────────────────────────┐
│                  │  0  1  2  3  4  5  6  7  8  9 ... 23            │
├──────────────────┼──────────────────────────────────────────────────┤
│ Máy giặt (lh)   │                 [████]                           │  draggable (Indigo)
│ Máy lạnh (lh)   │                              [████████]          │  draggable (Indigo)
│ Đèn (cđ)        │  [████████████████████████████████████████████]  │  fixed (grey)
└──────────────────┴──────────────────────────────────────────────────┘
```

- 24 columns (hours 0–23), CSS Grid
- `candidate_hours` cells = lit (droppable); others = dim (reject drop)
- Block width = `duration_hours` columns
- Hover over valid cell → highlight Teal border
- `disabled=true` → opacity 0.6, pointer-events none
- HTML5: block has `draggable`, cells have `onDragOver` + `onDrop`
- Drop on invalid hour → no-op (block stays at current position)

**Internal state:** `localSchedule` mirrors `schedule` prop for optimistic update on drop; resets when `schedule` prop changes (parent re-renders with QAOA result).

### Explain UI in Dashboard

Position in results section (after GanttEditor, before bill chart... actually after bill chart):

```
<ResultsBillNumbers />
<GanttEditor />          ← replaces <img gantt_chart_png>
<img bill_chart_png />   ← unchanged
<ExplainSection />       ← NEW: button + streaming card
```

**ExplainSection:**
```
[✨ Giải thích kết quả]   ← motion.button, Gold accent, disabled when explainLoading

When explainLoading:
  "⟳ Gemini đang phân tích..."  ← pulse animation (reuse existing pattern)

When explainText:
  ┌──────────────────────────────────────┐
  │ 💡 Phân tích kết quả                │   ← Indigo border-left
  │                                      │
  │  <streaming text...>▌               │
  └──────────────────────────────────────┘
```

### `api.js` additions

```js
export const explainSchedule = (payload) =>
  // Returns raw fetch Response (not axios) for SSE streaming
  fetch(`${API_BASE}/explain`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${getToken()}`,
    },
    body: JSON.stringify(payload),
  });
```

Note: use `fetch` not `axios` for SSE — axios buffers the full response.

---

## Section 4: Testing

### Backend tests

**`server/tests/test_optimize_pinned.py`:**
- `test_pinned_appliance_fixed_in_result`: POST /optimize với `pinned_schedule={"Máy giặt": 8}` → `result.schedule["Máy giặt"] == 8`
- `test_pinned_empty_dict`: `pinned_schedule={}` → same behavior as omitting it
- `test_pinned_invalid_hour`: pin vào giờ ngoài `candidate_hours` → 422

**`server/tests/test_explain.py`:**
- `test_explain_streams_sse`: mock Gemini SDK, check response is `text/event-stream`, body has `data:` lines ending with `[DONE]`
- `test_explain_requires_auth`: no JWT → 401
- `test_explain_missing_gemini_key`: `GEMINI_API_KEY` unset → RuntimeError at startup (test startup guard)

### Frontend

No unit tests for GanttEditor — HTML5 drag API unsupported in jsdom. Covered by manual smoke test.

### Manual Smoke Test Checklist

```
☐ Optimize → GanttEditor hiện đúng lịch, block đúng vị trí
☐ Kéo block flexible sang giờ hợp lệ → optimistic snap, pulse loading
☐ QAOA chạy lại → Gantt + bill numbers update với lịch mới
☐ Kéo vào giờ không hợp lệ → drop rejected, block về chỗ cũ
☐ Fixed appliance không kéo được
☐ Nhấn "Giải thích kết quả" → text stream ra từng chữ bằng tiếng Việt
☐ Optimize lại → explainText reset
☐ History page → entry mới sau mỗi lần kéo-thả re-optimize
☐ Reoptimizing → GanttEditor disabled (opacity 0.6, không kéo được)
☐ "Tối ưu hóa" gốc → pinnedSchedule reset
```

---

## Files Changed Summary

### New files
- `server/routers/explain_router.py`
- `server/tests/test_optimize_pinned.py`
- `server/tests/test_explain.py`
- `client/src/components/GanttEditor.jsx`

### Modified files
- `server/routers/optimize_router.py` — pinned_schedule support
- `server/main.py` — include explain_router
- `server/requirements.txt` — add google-generativeai
- `server/.env` — add GEMINI_API_KEY (not committed)
- `client/src/pages/Dashboard.jsx` — GanttEditor + explain UI + new state
- `client/src/api.js` — add explainSchedule()
- `client/src/index.css` — GanttEditor + explain-card styles
