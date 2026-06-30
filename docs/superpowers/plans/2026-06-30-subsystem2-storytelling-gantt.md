# Subsystem 2: Storytelling + Interactive Gantt Editor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Q-SmartEnergy Dashboard with a drag-and-drop Gantt chart that re-runs QAOA when an appliance is pinned to a time slot, and an on-demand Gemini-powered Vietnamese explanation of results streamed via SSE.

**Architecture:** Backend gains optional `pinned_schedule` on `POST /optimize` (pinned appliances are overridden to fixed, removed from QAOA, then merged back into the result) and a new `POST /explain` endpoint that builds a Vietnamese prompt and streams Gemini output as SSE. React replaces the static gantt PNG with a `GanttEditor` component (HTML5 drag-and-drop, CSS Grid, 24 columns) and adds an explain button with streaming text — all within the existing Dashboard page, no new routes.

**Tech Stack:** FastAPI `StreamingResponse`, `google-generativeai` Python SDK (`gemini-2.0-flash`), React 19 + Vite, HTML5 Drag & Drop API, CSS Grid

## Global Constraints

- NEVER use "giờ cao điểm" / "peak hour" / "time-of-use" anywhere (code, comments, strings, variables)
- All baseline numbers imported from `calc.py` — never hard-coded elsewhere
- Palette: only Indigo `#3730A3`, Teal `#0F766E`, Gold `#CA8A04` — CSS vars are `--indigo`, `--teal`, `--gold` (defined in `client/src/App.css`)
- `GEMINI_API_KEY` must come from `server/.env`, never hard-coded in source
- JWT secret from environment variable only — never hard-coded
- Per-user bill uses user's OWN appliance list total, not static global `calc.py` numbers
- `python -O` must NOT silently disable any safety checks
- No new npm packages; only new pip package is `google-generativeai`

---

## File Map

### New files
| File | Responsibility |
|------|---------------|
| `server/routers/explain_router.py` | `POST /explain`: build Vietnamese prompt, call Gemini, stream SSE |
| `server/tests/test_optimize_pinned.py` | Tests for `pinned_schedule` behaviour |
| `server/tests/test_explain.py` | Tests for `/explain` SSE endpoint |
| `client/src/components/GanttEditor.jsx` | 24-col interactive drag-and-drop Gantt component |

### Modified files
| File | Change |
|------|--------|
| `server/routers/optimize_router.py` | Add `pinned_schedule` field + `_apply_pins` + merge-back logic |
| `server/main.py` | Register `explain_router` |
| `server/requirements.txt` | Add `google-generativeai` |
| `client/src/pages/Dashboard.jsx` | GanttEditor + explain UI + new state + debounce re-optimize |
| `client/src/api.js` | Add `explainSchedule()` using raw `fetch` for SSE |
| `client/src/App.css` | Gantt + explain-card styles (CSS vars already defined here) |

---

### Task 1: pinned_schedule support in POST /optimize

**Files:**
- Modify: `server/routers/optimize_router.py`
- Create: `server/tests/test_optimize_pinned.py`

**Interfaces:**
- Consumes: existing `OptimizeRequest`, `_db_rows_to_appliances()`, `Appliance` from `qubo_builder`
- Produces: `POST /optimize` accepts optional `pinned_schedule: dict[str, int]`; `result.schedule` always contains pinned entries at their pinned hours

**Context:** `server/tests/conftest.py` has `client` and `auth_headers` fixtures. Default seeded appliances: `Máy giặt` has `candidate_hours=(9, 14)`, `is_flexible=True`. Use `use_quantum=False` in tests for speed.

- [ ] **Step 1: Write failing tests**

Create `server/tests/test_optimize_pinned.py`:

```python
"""Tests for POST /optimize pinned_schedule parameter."""


def test_pinned_appliance_fixed_in_result(client, auth_headers):
    """Pinned appliance must appear in result.schedule at the pinned hour."""
    headers = auth_headers("pinuser1")
    # Máy giặt has candidate_hours=(9, 14) in the default seed — pin to 14
    response = client.post(
        "/optimize",
        json={
            "day_of_month": 9,
            "weather_condition": "sunny",
            "use_quantum": False,
            "pinned_schedule": {"Máy giặt": 14},
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Máy giặt" in data["schedule"]
    assert data["schedule"]["Máy giặt"] == 14


def test_pinned_empty_dict_behaves_same_as_omitting(client, auth_headers):
    """pinned_schedule={} must not crash and must return 200."""
    headers = auth_headers("pinuser2")
    response = client.post(
        "/optimize",
        json={"day_of_month": 9, "weather_condition": "sunny", "pinned_schedule": {}},
        headers=headers,
    )
    assert response.status_code == 200


def test_pinned_invalid_hour_returns_422(client, auth_headers):
    """Pinning to an hour outside candidate_hours must return 422."""
    headers = auth_headers("pinuser3")
    # Máy giặt candidate_hours=(9, 14) — hour 3 is invalid
    response = client.post(
        "/optimize",
        json={
            "day_of_month": 9,
            "weather_condition": "sunny",
            "pinned_schedule": {"Máy giặt": 3},
        },
        headers=headers,
    )
    assert response.status_code == 422
```

- [ ] **Step 2: Run tests — verify they fail**

```
cd server
pytest tests/test_optimize_pinned.py -v
```

Expected: tests fail (422 test may accidentally pass via Pydantic int validation, but hour-validation logic is not yet implemented).

- [ ] **Step 3: Implement pinned_schedule in optimize_router.py**

**3a.** Change the imports line at top of `server/routers/optimize_router.py`:

```python
# Before:
from typing import List, Optional
from fastapi import APIRouter, Depends

# After:
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
```

**3b.** Add `pinned_schedule` field to `OptimizeRequest` (the class around line 30):

```python
class OptimizeRequest(BaseModel):
    day_of_month: int = 9
    weather_condition: str = "sunny"
    use_quantum: bool = True
    pinned_schedule: Optional[Dict[str, int]] = None
```

**3c.** In the `optimize()` function, right after `user_appliances = _db_rows_to_appliances(rows)`, add:

```python
    # --- pinned_schedule: validate hours then override flexibility for this run only ---
    pinned = payload.pinned_schedule or {}
    if pinned:
        for app in user_appliances:
            if app.name in pinned:
                hour = pinned[app.name]
                if app.candidate_hours and hour not in app.candidate_hours:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"'{app.name}': hour {hour} not in "
                            f"candidate_hours {list(app.candidate_hours)}"
                        ),
                    )
        user_appliances = [
            Appliance(
                name=a.name,
                power_w=a.power_w,
                duration_hours=a.duration_hours,
                candidate_hours=(pinned[a.name],),
                is_flexible=False,
            )
            if a.name in pinned
            else a
            for a in user_appliances
        ]
```

**3d.** Right after `result = scheduler.solve(use_quantum=payload.use_quantum)`, add:

```python
    # Merge pinned entries back — QAOA only ran on remaining flexible appliances
    for name, hour in pinned.items():
        result.schedule[name] = hour
```

- [ ] **Step 4: Run tests — verify they pass**

```
cd server
pytest tests/test_optimize_pinned.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Run full backend suite (regression check)**

```
cd server
pytest tests/ -v
```

Expected: all existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add server/routers/optimize_router.py server/tests/test_optimize_pinned.py
git commit -m "feat: add pinned_schedule support to POST /optimize"
```

---

### Task 2: POST /explain SSE endpoint

**Files:**
- Create: `server/routers/explain_router.py`
- Create: `server/tests/test_explain.py`
- Modify: `server/main.py`
- Modify: `server/requirements.txt`

**Interfaces:**
- Consumes: `auth.get_current_user`, `os.environ["GEMINI_API_KEY"]`, `google.generativeai` SDK
- Produces: `POST /explain` → `text/event-stream`; each Gemini text chunk as `data: {text}\n\n`; terminates with `data: [DONE]\n\n`

**Pre-condition:** Add `GEMINI_API_KEY=any-fake-value-for-tests` to `server/.env` so the module imports without error in the test environment. The SDK is fully mocked in tests so the value doesn't matter.

- [ ] **Step 1: Add google-generativeai to requirements.txt**

In `server/requirements.txt`, add one line:

```
google-generativeai
```

Install:

```
cd server
pip install google-generativeai
```

- [ ] **Step 2: Write failing tests**

Create `server/tests/test_explain.py`:

```python
"""Tests for POST /explain SSE endpoint."""
import sys
from unittest.mock import MagicMock, patch


def _make_chunk(text: str):
    chunk = MagicMock()
    chunk.text = text
    return chunk


def test_explain_streams_sse(client, auth_headers):
    """POST /explain with mocked Gemini returns text/event-stream with data: lines."""
    headers = auth_headers("explainuser1")
    mock_chunks = [_make_chunk("Hệ thống đã"), _make_chunk(" tối ưu tốt.")]

    with patch("explain_router.genai.GenerativeModel") as mock_cls:
        mock_model = MagicMock()
        mock_cls.return_value = mock_model
        mock_model.generate_content.return_value = iter(mock_chunks)

        response = client.post(
            "/explain",
            json={
                "schedule": {"Máy giặt": 9},
                "appliances": [
                    {
                        "name": "Máy giặt",
                        "power_w": 500.0,
                        "duration_hours": 1.0,
                        "is_flexible": True,
                    }
                ],
                "bill_before_vnd": 500000.0,
                "bill_after_vnd": 415000.0,
                "savings_percent": 17.0,
                "weather_condition": "sunny",
                "solver_used": "qaoa",
            },
            headers=headers,
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    assert "data: Hệ thống đã" in body
    assert "data: [DONE]" in body


def test_explain_requires_auth(client):
    """POST /explain without JWT returns 401."""
    response = client.post(
        "/explain",
        json={
            "schedule": {},
            "appliances": [],
            "bill_before_vnd": 0.0,
            "bill_after_vnd": 0.0,
            "savings_percent": 0.0,
            "weather_condition": "sunny",
            "solver_used": "qaoa",
        },
    )
    assert response.status_code == 401


def test_explain_missing_gemini_key_raises_at_startup(monkeypatch):
    """If GEMINI_API_KEY is not set, importing explain_router raises RuntimeError."""
    import pytest

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    sys.modules.pop("explain_router", None)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        import explain_router  # noqa: F401
    # Restore module so later tests in this session are unaffected
    monkeypatch.setenv("GEMINI_API_KEY", "restored-fake-key")
    sys.modules.pop("explain_router", None)
    import explain_router  # noqa: F401, F811
```

- [ ] **Step 3: Run tests — verify they fail**

```
cd server
pytest tests/test_explain.py -v
```

Expected: ImportError or 3 FAILED (router does not exist yet).

- [ ] **Step 4: Create explain_router.py**

Create `server/routers/explain_router.py`:

```python
"""POST /explain: stream a Gemini-generated Vietnamese explanation of optimization results."""
import os

import google.generativeai as genai
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth import get_current_user
from models import User

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY environment variable is required. Set it in server/.env"
    )

genai.configure(api_key=GEMINI_API_KEY)

router = APIRouter(tags=["explain"])

_WEATHER_VI = {"sunny": "nắng", "cloudy": "có mây", "rainy": "mưa"}


class ApplianceInfo(BaseModel):
    name: str
    power_w: float
    duration_hours: float
    is_flexible: bool


class ExplainRequest(BaseModel):
    schedule: dict[str, int]
    appliances: list[ApplianceInfo]
    bill_before_vnd: float
    bill_after_vnd: float
    savings_percent: float
    weather_condition: str
    solver_used: str


def _build_prompt(req: ExplainRequest) -> str:
    weather_vi = _WEATHER_VI.get(req.weather_condition, req.weather_condition)
    schedule_lines = "\n".join(
        f"  - {name}: {hour}h00" for name, hour in sorted(req.schedule.items())
    )
    return (
        "Bạn là trợ lý AI phân tích năng lượng của Q-SmartEnergy. "
        "Hãy giải thích kết quả tối ưu hóa sau đây bằng tiếng Việt tự nhiên, "
        "ngắn gọn (4-5 câu). Tập trung vào: tại sao các giờ đó hợp lý "
        "(nắng → solar cao), ý nghĩa tiết kiệm thực tế, và một lời khuyên cụ thể.\n\n"
        f"Thời tiết: {weather_vi}\n"
        f"Solver: {req.solver_used}\n"
        f"Lịch tối ưu:\n{schedule_lines}\n"
        f"Hóa đơn: {req.bill_before_vnd:,.0f}đ → {req.bill_after_vnd:,.0f}đ "
        f"(tiết kiệm {req.savings_percent:.1f}%)"
    )


def _stream_explanation(prompt: str):
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt, stream=True)
    for chunk in response:
        if chunk.text:
            yield f"data: {chunk.text}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/explain")
def explain(
    payload: ExplainRequest,
    current_user: User = Depends(get_current_user),
):
    prompt = _build_prompt(payload)
    return StreamingResponse(
        _stream_explanation(prompt),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

- [ ] **Step 5: Register explain_router in main.py**

In `server/main.py`, update the routers import line and add the router:

```python
# Change this line:
from routers import auth_router, appliances_router, optimize_router

# To:
from routers import auth_router, appliances_router, optimize_router, explain_router
```

After `app.include_router(optimize_router.router)`, add:

```python
app.include_router(explain_router.router)
```

- [ ] **Step 6: Run tests — verify they pass**

```
cd server
pytest tests/test_explain.py -v
```

Expected: 3 PASSED

- [ ] **Step 7: Run full backend suite (regression check)**

```
cd server
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add server/routers/explain_router.py server/tests/test_explain.py server/main.py server/requirements.txt
git commit -m "feat: add POST /explain SSE endpoint with Gemini streaming"
```

---

### Task 3: GanttEditor React component

**Files:**
- Create: `client/src/components/GanttEditor.jsx` (directory must be created)
- Modify: `client/src/App.css` (CSS vars `--indigo`, `--teal`, `--gold` already defined there)

**Interfaces:**
- Consumes: nothing from earlier tasks (standalone component)
- Produces: `<GanttEditor schedule={...} appliances={[...]} onPinnedChange={fn} disabled={bool} />` — Task 4 imports this

Props contract (exact names and types used by Task 4):
- `schedule`: `{ [applianceName: string]: startHour_int }` — from `result.schedule`
- `appliances`: array of `{ name: string, duration_hours: number, candidate_hours: number[], is_flexible: boolean }` — from `getAppliances()`
- `onPinnedChange(pinned: { [name: string]: hour_int })`: called on valid drop; argument contains **only flexible** appliances
- `disabled`: `boolean` — `true` while QAOA is re-running; makes grid non-interactive (opacity 0.6)

Layout (24-column CSS Grid, one row per appliance):
```
┌──────────────────┬──────────────────────────────────────────────────────┐
│                  │  0  1  2  3  4  5  6  7  8  9  ...  23              │
├──────────────────┼──────────────────────────────────────────────────────┤
│ Máy giặt ⟳      │              valid  valid [████]  valid  valid       │ draggable (Indigo)
│ Đèn              │  [████████████████████████████████████████████████]  │ fixed (grey)
└──────────────────┴──────────────────────────────────────────────────────┘
```

Drag mechanics:
- `candidate_hours` cells for flexible appliances lit in Teal on hover during drag
- Block overlaps cells via CSS Grid (`z-index: 2` over cells `z-index: 1`)
- `requestAnimationFrame` delay before setting `pointer-events: none` on block, so browser captures drag image before cells take over events

- [ ] **Step 1: Create client/src/components/ directory and GanttEditor.jsx**

```bash
mkdir "client/src/components"
```

Create `client/src/components/GanttEditor.jsx`:

```jsx
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
```

- [ ] **Step 2: Add Gantt styles to App.css**

Append to `client/src/App.css`:

```css
/* ── GanttEditor ─────────────────────────────────────── */
.gantt-editor {
  margin: 1rem 0;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #fff;
  overflow-x: auto;
}
.gantt-disabled {
  opacity: 0.6;
  pointer-events: none;
}
.gantt-row {
  display: flex;
  align-items: stretch;
  border-bottom: 1px solid #f3f4f6;
  min-height: 36px;
}
.gantt-row:last-child {
  border-bottom: none;
}
.gantt-header-row {
  border-bottom: 2px solid var(--border);
  font-size: 0.68rem;
  color: var(--text-muted);
  background: #f9fafb;
}
.gantt-label {
  width: 148px;
  min-width: 148px;
  padding: 0 0.5rem;
  font-size: 0.78rem;
  display: flex;
  align-items: center;
  gap: 4px;
  border-right: 1px solid var(--border);
  white-space: nowrap;
  overflow: hidden;
}
.gantt-flex-badge {
  color: var(--teal);
  font-size: 0.7rem;
}
.gantt-track {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(24, 1fr);
  position: relative;
  align-items: stretch;
}
.gantt-header-cell {
  text-align: center;
  padding: 6px 0 4px;
  grid-row: 1;
  border-right: 1px solid #f3f4f6;
  font-size: 0.65rem;
}
.gantt-cell {
  grid-row: 1;
  border-right: 1px solid #f3f4f6;
  transition: background 0.1s;
  z-index: 1;
}
.gantt-cell-valid {
  background: rgba(15, 118, 110, 0.06);
}
.gantt-cell-hover {
  background: rgba(15, 118, 110, 0.2) !important;
  outline: 2px dashed var(--teal);
  outline-offset: -2px;
}
.gantt-block {
  grid-row: 1;
  border-radius: 5px;
  margin: 4px 1px;
  z-index: 2;
  cursor: grab;
  transition: opacity 0.15s, box-shadow 0.15s;
}
.gantt-block-flex {
  background: var(--indigo);
  opacity: 0.85;
}
.gantt-block-flex:hover {
  opacity: 1;
  box-shadow: 0 2px 8px rgba(55, 48, 163, 0.35);
}
.gantt-block-fixed {
  background: #d1d5db;
  cursor: default;
}
.gantt-block-dragging {
  opacity: 0.35;
}
```

- [ ] **Step 3: Quick visual sanity check**

Temporarily in `Dashboard.jsx` (at bottom of the results section), add:

```jsx
import GanttEditor from "../components/GanttEditor";
// Inside results AnimatePresence block, after bill_chart_png img:
<GanttEditor
  schedule={result.schedule}
  appliances={appliances}
  onPinnedChange={(p) => console.log("pinned:", p)}
  disabled={false}
/>
```

Run `cd client && npm run dev`, trigger an optimize, confirm:
- Gantt rows appear, Indigo blocks for flexible (⟳ badge), grey for fixed
- Teal highlight on valid drop zone cells when dragging
- `console.log` fires with correct pinned object on drop

Remove the temporary addition — Task 4 does the proper integration.

- [ ] **Step 4: Commit**

```bash
git add client/src/components/GanttEditor.jsx client/src/App.css
git commit -m "feat: add GanttEditor drag-and-drop component with CSS Grid"
```

---

### Task 4: Dashboard integration + explain UI

**Files:**
- Modify: `client/src/pages/Dashboard.jsx`
- Modify: `client/src/api.js`
- Modify: `client/src/App.css`

**Interfaces:**
- Consumes: `GanttEditor` from Task 3 (import path `"../components/GanttEditor"`); `explainSchedule()` added to `api.js`; `POST /optimize` with `pinned_schedule` from Task 1; `POST /explain` from Task 2
- Produces: complete Subsystem 2 — interactive Gantt replaces gantt PNG, explain button streams Gemini text

New state in Dashboard:
```js
const [reoptimizing, setReoptimizing]   // true while drag-triggered QAOA runs
const [pinnedSchedule, setPinnedSchedule]  // accumulated pinned hours from drags
const [explainText, setExplainText]     // streamed Gemini output
const [explainLoading, setExplainLoading]
const debounceRef                        // useRef for 400ms debounce
```

- [ ] **Step 1: Add explainSchedule to api.js**

In `client/src/api.js`, append before `export default apiClient;`:

```js
// Returns raw fetch Response (not axios) — needed for SSE ReadableStream
export function explainSchedule(payload) {
  return fetch(`${API_BASE_URL}/explain`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem("token")}`,
    },
    body: JSON.stringify(payload),
  });
}
```

- [ ] **Step 2: Replace Dashboard.jsx with integrated version**

Replace the entire contents of `client/src/pages/Dashboard.jsx`:

```jsx
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  createAppliance, deleteAppliance, getAppliances,
  optimize as apiOptimize, updateAppliance, explainSchedule,
} from "../api";
import { useAuth } from "../AuthContext";
import { useCountUp } from "../useCountUp";
import GanttEditor from "../components/GanttEditor";

const WEATHER_OPTIONS = [
  { value: "sunny", label: "☀️ Nắng" },
  { value: "cloudy", label: "⛅ Có mây" },
  { value: "rainy", label: "🌧 Mưa" },
];

function ApplianceRow({ appliance, onSave, onDelete }) {
  const [power, setPower] = useState(appliance.power_w);
  const [duration, setDuration] = useState(appliance.duration_hours);

  function save() {
    if (Number(power) !== appliance.power_w || Number(duration) !== appliance.duration_hours) {
      onSave(appliance.id, { ...appliance, power_w: Number(power), duration_hours: Number(duration) });
    }
  }

  return (
    <tr>
      <td>{appliance.name}</td>
      <td>
        <input type="number" value={power} min={1}
          onChange={(e) => setPower(e.target.value)} onBlur={save} />
      </td>
      <td>
        <input type="number" value={duration} min={0.1} step={0.1}
          onChange={(e) => setDuration(e.target.value)} onBlur={save} />
      </td>
      <td style={{ color: appliance.is_flexible ? "var(--teal)" : "var(--text-muted)" }}>
        {appliance.is_flexible ? "Linh hoạt" : "Cố định"}
      </td>
      <td>
        <button onClick={() => onDelete(appliance.id)}>Xóa</button>
      </td>
    </tr>
  );
}

function ResultsBillNumbers({ billBefore, billAfter, savingsPct }) {
  const animBefore = useCountUp(billBefore);
  const animAfter = useCountUp(billAfter);
  const animSavings = useCountUp(savingsPct, 800, 1);

  return (
    <div className="bill-numbers">
      <div className="bill-item">
        <strong>{animBefore.toLocaleString("vi-VN")}đ</strong>
        Hóa đơn trước
      </div>
      <div style={{ fontSize: "1.5rem", alignSelf: "center" }}>→</div>
      <div className="bill-item">
        <strong style={{ color: "var(--teal)" }}>{animAfter.toLocaleString("vi-VN")}đ</strong>
        Sau tối ưu hóa
      </div>
      <div className="bill-item">
        <strong className="savings-highlight">↓ {animSavings.toFixed(1)}%</strong>
        Tiết kiệm
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [appliances, setAppliances] = useState([]);
  const [dayOfMonth, setDayOfMonth] = useState(9);
  const [weather, setWeather] = useState("sunny");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reoptimizing, setReoptimizing] = useState(false);
  const [error, setError] = useState("");
  const [newName, setNewName] = useState("");
  const [newPower, setNewPower] = useState(100);
  const [newDuration, setNewDuration] = useState(1);
  const [pinnedSchedule, setPinnedSchedule] = useState({});
  const [explainText, setExplainText] = useState("");
  const [explainLoading, setExplainLoading] = useState(false);
  const debounceRef = useRef(null);
  const { logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => { loadAppliances(); }, []);

  async function loadAppliances() {
    try {
      const data = await getAppliances();
      setAppliances(data);
    } catch (err) {
      if (err.response?.status === 401) { logout(); navigate("/login"); }
    }
  }

  async function handleSave(id, payload) {
    await updateAppliance(id, payload);
    await loadAppliances();
  }

  async function handleDelete(id) {
    await deleteAppliance(id);
    await loadAppliances();
  }

  async function handleAdd(e) {
    e.preventDefault();
    await createAppliance({
      name: newName, power_w: Number(newPower), duration_hours: Number(newDuration),
      candidate_hours: [], is_flexible: false,
    });
    setNewName(""); setNewPower(100); setNewDuration(1);
    await loadAppliances();
  }

  async function runOptimize(pinned = {}) {
    const isDrag = Object.keys(pinned).length > 0;
    setError("");
    if (isDrag) {
      setReoptimizing(true);
    } else {
      setLoading(true);
      setResult(null);
      setPinnedSchedule({});
      setExplainText("");
    }
    try {
      const data = await apiOptimize({
        day_of_month: Number(dayOfMonth),
        weather_condition: weather,
        use_quantum: true,
        ...(isDrag ? { pinned_schedule: pinned } : {}),
      });
      setResult(data);
    } catch {
      setError("Lỗi khi tối ưu hóa. Kiểm tra backend đã chạy chưa?");
    } finally {
      setLoading(false);
      setReoptimizing(false);
    }
  }

  function handlePinnedChange(newPinned) {
    setPinnedSchedule(newPinned);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runOptimize(newPinned), 400);
  }

  async function handleExplain() {
    setExplainText("");
    setExplainLoading(true);
    try {
      const response = await explainSchedule({
        schedule: result.schedule,
        appliances: appliances.map((a) => ({
          name: a.name,
          power_w: a.power_w,
          duration_hours: a.duration_hours,
          is_flexible: a.is_flexible,
        })),
        bill_before_vnd: result.bill_before_vnd,
        bill_after_vnd: result.bill_after_vnd,
        savings_percent: result.savings_percent,
        weather_condition: result.weather_condition,
        solver_used: result.solver_used,
      });
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value, { stream: true });
        for (const line of text.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          const content = line.slice(6);
          if (content === "[DONE]") { setExplainLoading(false); return; }
          if (content) setExplainText((prev) => prev + content);
        }
      }
    } catch {
      setExplainText("Không thể kết nối Gemini. Vui lòng thử lại.");
    } finally {
      setExplainLoading(false);
    }
  }

  function handleLogout() { logout(); navigate("/login"); }

  const totalKwh = appliances.reduce(
    (sum, a) => sum + (a.power_w / 1000) * a.duration_hours * 30, 0
  );

  return (
    <motion.div
      className="dashboard"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
    >
      <header className="dashboard-header">
        <h1>Q-SmartEnergy</h1>
        <nav>
          <button onClick={() => navigate("/history")}>📋 Lịch sử</button>
          <button onClick={handleLogout}>Đăng xuất</button>
        </nav>
      </header>

      {/* Appliance list */}
      <div className="section-card">
        <h2>Thiết bị của bạn — tổng ~{totalKwh.toFixed(0)} kWh/tháng</h2>
        <table>
          <thead>
            <tr>
              <th>Tên thiết bị</th><th>Công suất (W)</th>
              <th>Giờ dùng</th><th>Loại</th><th></th>
            </tr>
          </thead>
          <tbody>
            {appliances.map((a) => (
              <ApplianceRow key={a.id} appliance={a} onSave={handleSave} onDelete={handleDelete} />
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
          <button type="submit">+ Thêm thiết bị</button>
        </form>
      </div>

      {/* Optimize controls */}
      <div className="section-card">
        <h2>Tối ưu hóa lịch chạy</h2>
        <div className="optimize-controls">
          <label>
            Ngày trong tháng
            <input type="number" min={1} max={30} value={dayOfMonth}
              onChange={(e) => setDayOfMonth(e.target.value)} />
          </label>
          <label>
            Thời tiết hôm nay
            <select value={weather} onChange={(e) => setWeather(e.target.value)}>
              {WEATHER_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
          <motion.button
            className="btn-optimize"
            onClick={() => runOptimize()}
            disabled={loading}
            whileHover={{ scale: loading ? 1 : 1.03 }}
            whileTap={{ scale: loading ? 1 : 0.97 }}
          >
            {loading ? "⏳ Đang tối ưu..." : "⚡ Tối ưu hóa"}
          </motion.button>
        </div>
        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: [0.4, 1, 0.4] }}
            transition={{ repeat: Infinity, duration: 1.2 }}
            style={{ marginTop: "0.75rem", color: "var(--indigo)", fontWeight: 600 }}
          >
            ⚡ Thuật toán lượng tử đang xử lý...
          </motion.div>
        )}
        {error && <p className="auth-error" style={{ marginTop: "0.75rem" }}>{error}</p>}
      </div>

      {/* Results */}
      <AnimatePresence>
        {result && (
          <motion.div
            className="section-card results-section"
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
          >
            <h2>Kết quả</h2>
            <ResultsBillNumbers
              billBefore={result.bill_before_vnd}
              billAfter={result.bill_after_vnd}
              savingsPct={result.savings_percent}
            />
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
              Solver: {result.solver_used}
              {result.used_fallback ? " (dùng fallback cổ điển)" : ""}
            </p>

            {/* Re-optimize pulse */}
            {reoptimizing && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ repeat: Infinity, duration: 1.2 }}
                style={{
                  color: "var(--indigo)", fontWeight: 600,
                  marginBottom: "0.5rem", fontSize: "0.85rem",
                }}
              >
                ⚡ Đang tính lại lịch...
              </motion.div>
            )}

            {/* Interactive Gantt — replaces static gantt_chart_png */}
            <GanttEditor
              schedule={result.schedule}
              appliances={appliances}
              onPinnedChange={handlePinnedChange}
              disabled={reoptimizing}
            />

            {/* Bill comparison chart (static PNG, unchanged) */}
            {result.bill_chart_png && (
              <img
                src={`data:image/png;base64,${result.bill_chart_png}`}
                alt="So sánh hóa đơn điện"
                style={{ marginTop: "1rem" }}
              />
            )}

            {/* Storytelling section */}
            <div style={{ marginTop: "1rem" }}>
              <motion.button
                className="btn-explain"
                onClick={handleExplain}
                disabled={explainLoading}
                whileHover={{ scale: explainLoading ? 1 : 1.03 }}
                whileTap={{ scale: explainLoading ? 1 : 0.97 }}
              >
                ✨ Giải thích kết quả
              </motion.button>

              {explainLoading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: [0.4, 1, 0.4] }}
                  transition={{ repeat: Infinity, duration: 1.2 }}
                  style={{
                    marginTop: "0.75rem",
                    color: "var(--indigo)",
                    fontSize: "0.85rem",
                  }}
                >
                  ⟳ Gemini đang phân tích...
                </motion.div>
              )}

              {explainText && (
                <div className="explain-card">
                  <strong>💡 Phân tích kết quả</strong>
                  <p style={{ marginTop: "0.5rem", whiteSpace: "pre-wrap" }}>
                    {explainText}
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
```

- [ ] **Step 3: Add explain-card styles to App.css**

Append to `client/src/App.css`:

```css
/* ── Explain card ────────────────────────────────────── */
.explain-card {
  margin-top: 1rem;
  padding: 1rem 1.25rem;
  border-left: 3px solid var(--indigo);
  background: #eef2ff;
  border-radius: 0 8px 8px 0;
  line-height: 1.75;
  font-size: 0.9rem;
  color: #1e1b4b;
}
.btn-explain {
  background: var(--gold);
  color: #fff;
  border: none;
  padding: 0.5rem 1.25rem;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
}
.btn-explain:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
```

- [ ] **Step 4: Manual smoke test**

Start both servers:

```bash
# Terminal 1
cd server && uvicorn main:app --reload --port 8000

# Terminal 2
cd client && npm run dev
```

Work through this checklist:

```
☐ Optimize → GanttEditor appears: Indigo blocks (⟳) for flexible, grey for fixed
☐ Drag flexible block to valid hour (Teal highlight) → optimistic snap, ⚡ pulse loading
☐ After debounce (400ms): QAOA re-runs → Gantt + bill numbers update
☐ Drag to invalid hour → block snaps back to original position
☐ Fixed (grey) appliance block has no drag cursor
☐ While reoptimizing: Gantt is opacity 0.6, cannot drag
☐ "✨ Giải thích kết quả" button → Gemini text streams character-by-character in Vietnamese
☐ Trigger another optimize → explainText resets, Gantt resets
☐ History page (📋 Lịch sử) → new entry appears after each drag re-optimize
```

- [ ] **Step 5: Commit**

```bash
git add client/src/pages/Dashboard.jsx client/src/api.js client/src/App.css
git commit -m "feat: integrate GanttEditor + Gemini storytelling into Dashboard"
```
