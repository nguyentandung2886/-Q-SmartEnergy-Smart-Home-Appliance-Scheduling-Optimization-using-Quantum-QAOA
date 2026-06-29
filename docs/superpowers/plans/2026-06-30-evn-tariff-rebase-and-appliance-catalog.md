# EVN Tariff Rebase + Appliance Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `calc.py`'s illustrative 6-tier EVN pricing and locked `MONTHLY_KWH=530` with the real, current EVN residential tariff (5 tiers + 8% VAT) and a `MONTHLY_KWH` derived from a new 10-type household appliance catalog with sourced power ratings — accepting that the resulting bill numbers will differ from the original proposal's 896,125đ/658,125đ/26.6%.

**Architecture:** New leaf module `appliance_catalog.py` (depends only on `qubo_builder.Appliance`, which gains one new optional field `is_flexible`) becomes the source of `MONTHLY_KWH` for `calc.py`. `calc.py`'s `BILL_BEFORE_VND`/`BILL_AFTER_VND`/`SAVINGS_PERCENT` become directly-computed expressions instead of locked literals, so the previous reconciliation-checking machinery (`BaselineReconciliationError`/`_check_reconciliation`) is removed as redundant. `qubo_builder.py`, `quantum_runner.py`, `visualizer.py`, and `data_prep.py`'s actual logic are untouched — only `calc.py`'s data and `qubo_builder.Appliance`'s shape change.

**Tech Stack:** Python 3.13, pytest. No new dependencies.

## Global Constraints

- Work only inside `q-smartenergy/` (including `tests/`).
- NEVER use "giờ cao điểm" / "peak hour" / "time-of-use" anywhere (code, comments, docstrings, strings).
- No baseline number may be hard-coded outside `calc.py` (the appliance catalog's power/duration figures live in `appliance_catalog.py`, which is the legitimate primary source for those specific figures — NOT a violation of the "single source of truth" rule, since `calc.py` imports its derived total FROM `appliance_catalog.py`, not the other way around).
- Every new/changed public function needs a docstring (input/output + economic meaning), matching this codebase's existing style.
- `pytest tests/` must be fully green after every task.
- Do not change `qubo_builder.build_qubo`'s signature or behavior, `QuantumScheduler.__init__`, or `ScheduleResult` — this plan does not touch the QUBO/QAOA layer at all.
- The exact EVN tariff figures below are sourced from QĐ 14/2025/QĐ-TTg (Thủ tướng Chính phủ) and QĐ 1279/QĐ-BCT ngày 09/5/2025 (Bộ Công Thương), effective 29/05/2025, cross-confirmed via evn.com.vn and independent aggregators (luatvietnam.vn, vietnamsolar.vn) — use them exactly as given, do not alter.
- The appliance catalog's power/duration figures below are sourced per-entry (see Task 2) — use them exactly as given, do not alter. Where a figure is marked `[CẦN XÁC MINH]` in this plan, the comment in the code must preserve that marker — do not present it as fully verified.

---

### Task 1: `qubo_builder.py` — add `is_flexible` field to `Appliance`

**Files:**
- Modify: `q-smartenergy/qubo_builder.py:57-70` (the `Appliance` dataclass)
- Test: `q-smartenergy/tests/test_qubo_builder.py`

**Interfaces:**
- Produces: `Appliance.is_flexible: bool = True` (new field, default preserves all existing behavior).
- Consumes: nothing new.

**Why:** the appliance catalog (Task 2) needs to distinguish flexible appliances (schedulable via the existing one-hot QUBO mechanism — máy giặt, bình nước nóng) from fixed-load appliances (tủ lạnh, điều hòa, etc. — always-on or demand-driven, never a QUBO decision variable). `build_qubo()` itself does not change; callers are responsible for only passing `is_flexible=True` appliances to it.

- [ ] **Step 1: Write the failing test**

Open `q-smartenergy/tests/test_qubo_builder.py` and add this test function at the end of the file:

```python
def test_appliance_is_flexible_defaults_to_true():
    """New is_flexible field must default to True so every existing Appliance
    construction (including DEFAULT_APPLIANCES) is unaffected by this change."""
    appliance = Appliance(name="Test", power_w=100, duration_hours=1, candidate_hours=(7, 13))
    assert appliance.is_flexible is True


def test_appliance_is_flexible_can_be_set_false():
    appliance = Appliance(
        name="Tủ lạnh", power_w=34, duration_hours=24, candidate_hours=(), is_flexible=False
    )
    assert appliance.is_flexible is False
```

Confirm `Appliance` is already imported in this test file (it should be, since the file already tests `Appliance.energy_kwh` per existing tests — check the top of the file; if not imported, add it to the existing import line from `qubo_builder`).

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd q-smartenergy && pytest tests/test_qubo_builder.py -v -k is_flexible`
Expected: FAIL — `TypeError: Appliance.__init__() got an unexpected keyword argument 'is_flexible'`.

- [ ] **Step 3: Add the field**

In `q-smartenergy/qubo_builder.py`, find the `Appliance` dataclass:

```python
@dataclass
class Appliance:
    """Thiết bị điện gia dụng có thể linh hoạt giờ chạy.
    # Rubric III.1 - OOP, type hint đầy đủ
    """
    name: str
    power_w: float
    duration_hours: float
    candidate_hours: Tuple[int, ...]   # >= 2 giờ ứng viên, optimizer chọn đúng 1

    @property
    def energy_kwh(self) -> float:
        """Năng lượng tiêu thụ (kWh) = power_w/1000 * duration_hours."""
        return self.power_w / 1000.0 * self.duration_hours
```

Replace with:

```python
@dataclass
class Appliance:
    """Thiết bị điện gia dụng. is_flexible=True (mặc định) nghĩa là thiết bị có thể dời giờ
    chạy trong số candidate_hours — đây là biến quyết định trong QUBO (xem build_qubo).
    is_flexible=False nghĩa là tải cố định (tủ lạnh 24/7, điều hòa theo nhu cầu nhiệt độ,
    v.v.) — KHÔNG đưa vào build_qubo làm biến quyết định, chỉ đóng góp kWh cố định vào tổng
    tiêu thụ tháng (xem appliance_catalog.py). candidate_hours không có ý nghĩa khi
    is_flexible=False — để tuple rỗng `()`.
    # Rubric III.1 - OOP, type hint đầy đủ
    """
    name: str
    power_w: float
    duration_hours: float              # flexible: giờ chạy/lần; KHÔNG flexible: giờ dùng/ngày
    candidate_hours: Tuple[int, ...]   # flexible: >= 2 giờ ứng viên; KHÔNG flexible: ()
    is_flexible: bool = True

    @property
    def energy_kwh(self) -> float:
        """Năng lượng tiêu thụ (kWh) = power_w/1000 * duration_hours."""
        return self.power_w / 1000.0 * self.duration_hours
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd q-smartenergy && pytest tests/test_qubo_builder.py -v -k is_flexible`
Expected: ALL PASS.

- [ ] **Step 5: Run the full suite to check for regressions**

Run: `cd q-smartenergy && pytest tests/ -v`
Expected: all tests pass, no regressions (this change is purely additive with a default that preserves old behavior).

- [ ] **Step 6: Commit**

```bash
git add q-smartenergy/qubo_builder.py q-smartenergy/tests/test_qubo_builder.py
git commit -m "Add is_flexible field to Appliance (additive, default True)"
```

---

### Task 2: `appliance_catalog.py` — new module, 10 household appliance types

**Files:**
- Create: `q-smartenergy/appliance_catalog.py`
- Test: `q-smartenergy/tests/test_appliance_catalog.py`

**Interfaces:**
- Consumes: `qubo_builder.Appliance` (Task 1).
- Produces: `appliance_catalog.HOUSEHOLD_APPLIANCES: List[Appliance]`, `appliance_catalog.total_monthly_kwh(appliances: List[Appliance] = None) -> float`, `appliance_catalog.split_by_flexibility(appliances: List[Appliance]) -> Tuple[List[Appliance], List[Appliance]]`.

**Why:** models a realistic Vietnamese household's appliance mix with sourced power ratings, replacing the previous practice of picking `MONTHLY_KWH` first and back-fitting a story to match it. Per project owner's explicit decision: do NOT force the total to match any prior number — use real figures and accept whatever total results.

- [ ] **Step 1: Write the failing tests**

Create `q-smartenergy/tests/test_appliance_catalog.py`:

```python
"""
Tests for appliance_catalog.py — 10-type household appliance catalog with sourced
power ratings, used to derive calc.MONTHLY_KWH (replaces the old locked literal).
"""

import pytest

from appliance_catalog import HOUSEHOLD_APPLIANCES, split_by_flexibility, total_monthly_kwh


def test_household_appliances_has_ten_distinct_types():
    """10 LOẠI khác nhau (Điều hòa và Bình nước nóng mỗi loại có 2 instance, nên list có
    12 entries nhưng chỉ 10 tên loại gốc khác nhau khi bỏ phần mô tả công suất/vị trí)."""
    assert len(HOUSEHOLD_APPLIANCES) == 12


def test_total_monthly_kwh_matches_hand_computed_value():
    """Regression guard: tổng kWh/tháng từ 12 entries, tính bằng tay từ power_w/duration_hours
    đã chốt trong appliance_catalog.py. KHÔNG phải số ép trước — đây là kết quả của input thật,
    chốt lại bằng test để không bị âm thầm đổi sau này."""
    assert total_monthly_kwh() == pytest.approx(723.075, abs=0.01)


def test_total_monthly_kwh_accepts_custom_list():
    from qubo_builder import Appliance

    custom = [Appliance(name="X", power_w=1000, duration_hours=1, candidate_hours=(), is_flexible=False)]
    # 1000W * 1h * 30 / 1000 = 30 kWh
    assert total_monthly_kwh(custom) == pytest.approx(30.0)


def test_split_by_flexibility_separates_correctly():
    flexible, fixed = split_by_flexibility(HOUSEHOLD_APPLIANCES)
    assert all(a.is_flexible for a in flexible)
    assert all(not a.is_flexible for a in fixed)
    assert len(flexible) + len(fixed) == len(HOUSEHOLD_APPLIANCES)
    # Bình nước nóng (2 entries) + Máy giặt (1 entry) là flexible theo thiết kế.
    assert len(flexible) == 3
    assert len(fixed) == 9


def test_flexible_appliances_have_at_least_two_candidate_hours():
    """Mọi appliance is_flexible=True phải có >=2 candidate_hours (yêu cầu của build_qubo's
    one-hot encoding) — nếu chỉ có 1 hoặc 0 giờ ứng viên, ràng buộc one-hot vô nghĩa."""
    flexible, _ = split_by_flexibility(HOUSEHOLD_APPLIANCES)
    for appliance in flexible:
        assert len(appliance.candidate_hours) >= 2, f"{appliance.name} cần >=2 candidate_hours"


def test_fixed_appliances_have_empty_candidate_hours():
    _, fixed = split_by_flexibility(HOUSEHOLD_APPLIANCES)
    for appliance in fixed:
        assert appliance.candidate_hours == (), f"{appliance.name} (is_flexible=False) phải có candidate_hours=()"


def test_refrigerator_present_and_always_on():
    fridge = next(a for a in HOUSEHOLD_APPLIANCES if a.name == "Tủ lạnh")
    assert fridge.is_flexible is False
    assert fridge.duration_hours == 24
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd q-smartenergy && pytest tests/test_appliance_catalog.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'appliance_catalog'`.

- [ ] **Step 3: Write the implementation**

Create `q-smartenergy/appliance_catalog.py`:

```python
"""
Household Appliance Catalog for Q-SmartEnergy — 10 loại thiết bị điện gia dụng phổ biến
ở Việt Nam, công suất có nguồn tham chiếu (datasheet/trang nhà sản xuất/đại lý uy tín).
KHÔNG ép tổng khớp con số nào có trước — tổng kWh/tháng tính ra bao nhiêu thì dùng đúng
con số đó (xem total_monthly_kwh()), kể cả khi khác với số liệu minh họa trong proposal cũ.

Input: không có (module-level catalog cố định).
Output:
  - HOUSEHOLD_APPLIANCES: List[Appliance] — danh sách đầy đủ.
  - total_monthly_kwh(): tổng kWh/tháng — calc.py dùng giá trị này làm MONTHLY_KWH.
  - split_by_flexibility(): tách (flexible, fixed) để caller chỉ truyền phần flexible vào
    qubo_builder.build_qubo() (phần fixed không phải biến quyết định QUBO).

Quy ước tính kWh/tháng cho MỖI appliance (áp dụng đều cho is_flexible=True/False):
  monthly_kwh = power_w / 1000 * duration_hours * 30
  - is_flexible=False: duration_hours = giờ DÙNG MỖI NGÀY (vd tủ lạnh=24, quạt=5).
  - is_flexible=True: duration_hours = giờ CHẠY MỖI LẦN, giả định 1 lần/ngày (khớp đúng
    cách qubo_builder's one-hot chọn đúng 1 giờ/ngày cho thiết bị này).

Rubric Mapping:
  # Rubric III.5 - data generator dựa trên số liệu thiết bị thật, có nguồn
  # Rubric III.2 - ánh xạ đúng ràng buộc đời thực (tải cố định vs linh hoạt)
"""

from typing import List, Tuple

from qubo_builder import Appliance

HOUSEHOLD_APPLIANCES: List[Appliance] = [
    # 1. Tủ lạnh — Panasonic Inverter NR-BL267PSVN (234L), công bố hiệu suất chính thức
    #    Panasonic VN: 296 kWh/năm ≈ 0.81 kWh/ngày ≈ 33.75W liên tục (24/7).
    #    Nguồn: panasonic.com/vn (công bố hiệu suất tiêu thụ điện năng tủ lạnh).
    Appliance(name="Tủ lạnh", power_w=33.75, duration_hours=24, candidate_hours=(), is_flexible=False),

    # 2. Điều hòa phòng ngủ, 12000 BTU — Daikin FTKC35TVMV (1.5HP, Inverter), 960W rated.
    #    Giờ dùng/ngày: 6h (theo khoảng 6-8h/ngày mùa nóng, thông lệ ngành) [CẦN XÁC MINH giờ].
    #    Nguồn công suất: datasheet Daikin FTKC35TVMV (đại lý dienlanhdaicoviet.com).
    Appliance(name="Điều hòa phòng ngủ (12000 BTU)", power_w=960, duration_hours=6, candidate_hours=(), is_flexible=False),

    # 3. Điều hòa phòng khách, 18000 BTU — Daikin FTKC50 (2HP, Inverter), 1670W rated (full load).
    #    Giờ dùng/ngày: 6h [CẦN XÁC MINH giờ]. Nguồn công suất: datasheet Daikin FTKC50UV16V
    #    (đại lý betterhomeapp.com).
    Appliance(name="Điều hòa phòng khách (18000 BTU)", power_w=1670, duration_hours=6, candidate_hours=(), is_flexible=False),

    # 4. Bình nước nóng gián tiếp (storage, vd Ariston/Ferroli) — 2500W.
    #    FLEXIBLE: có thể hẹn giờ làm nóng nước trước khi dùng. candidate_hours minh họa:
    #    6h (sáng sớm) hoặc 21h (tối). Giờ dùng/lần: 0.5h [CẦN XÁC MINH thời gian].
    #    Nguồn công suất: FPT Shop (so sánh máy nước nóng gián tiếp Ariston/Ferroli).
    Appliance(name="Bình nước nóng gián tiếp", power_w=2500, duration_hours=0.5, candidate_hours=(6, 21), is_flexible=True),

    # 5. Bình nước nóng trực tiếp (instant, vd Ariston/Ferroli) — 3500W (khoảng 2500-4500W).
    #    FLEXIBLE: candidate_hours minh họa 7h hoặc 20h. Giờ dùng/lần: 0.5h [CẦN XÁC MINH thời gian].
    #    Nguồn công suất: FPT Shop (so sánh máy nước nóng trực tiếp Ariston/Ferroli).
    Appliance(name="Bình nước nóng trực tiếp", power_w=3500, duration_hours=0.5, candidate_hours=(7, 20), is_flexible=True),

    # 6. Máy giặt — 500W (loại cửa trên, phổ biến). FLEXIBLE: candidate_hours minh họa 9h/14h.
    #    Giờ dùng/lần: 1h. Nguồn: Meta.vn, Điện máy HTech (công suất máy giặt).
    Appliance(name="Máy giặt", power_w=500, duration_hours=1, candidate_hours=(9, 14), is_flexible=True),

    # 7. Quạt điện (quạt cây/để bàn) — 60W. Giờ dùng/ngày: 5h [CẦN XÁC MINH giờ].
    #    Nguồn công suất: FPT Shop, Livotec (công suất quạt điện).
    Appliance(name="Quạt điện", power_w=60, duration_hours=5, candidate_hours=(), is_flexible=False),

    # 8. Bếp điện (bếp từ 1 bếp) — 2000W. Giờ dùng/ngày: 1h [CẦN XÁC MINH giờ].
    #    Nguồn công suất: Sunhouse VN (bếp điện bao nhiêu W).
    Appliance(name="Bếp điện", power_w=2000, duration_hours=1, candidate_hours=(), is_flexible=False),

    # 9. Bóng điện (gộp ~6 bóng LED trong nhà, ~10W/bóng) — 60W tổng. Giờ dùng/ngày: 5h
    #    (theo ví dụ minh họa cách tính tiền điện của Home Credit) [CẦN XÁC MINH số bóng+giờ].
    #    Nguồn công suất/bóng: Haledco (công suất bóng đèn LED).
    Appliance(name="Bóng điện", power_w=60, duration_hours=5, candidate_hours=(), is_flexible=False),

    # 10. Nồi cơm điện — Toshiba RC-18NTFV(W), 800W. Giờ dùng/ngày: 1h (nấu + giữ ấm)
    #     [CẦN XÁC MINH tần suất]. Nguồn công suất: Pico.vn (nồi cơm điện Toshiba RC-18NTFV).
    Appliance(name="Nồi cơm điện", power_w=800, duration_hours=1, candidate_hours=(), is_flexible=False),

    # 11. Tivi (LED 43 inch) — 100W (khoảng 65-140W tùy độ sáng/HDR). Giờ dùng/ngày: 4h
    #     [CẦN XÁC MINH giờ]. Nguồn công suất: manhnguyen.com.vn (công suất tivi Samsung).
    Appliance(name="Tivi", power_w=100, duration_hours=4, candidate_hours=(), is_flexible=False),

    # 12. Lò vi sóng — 850W (khoảng 800-900W). Giờ dùng/ngày: 0.25h (15 phút).
    #     Nguồn công suất: FPT Shop (so sánh lò vi sóng Sharp/Panasonic).
    Appliance(name="Lò vi sóng", power_w=850, duration_hours=0.25, candidate_hours=(), is_flexible=False),
]


def total_monthly_kwh(appliances: List[Appliance] = None) -> float:
    """Tổng kWh/tháng = Σ (power_w/1000 * duration_hours * 30) cho mọi appliance trong list.
    Default dùng HOUSEHOLD_APPLIANCES nếu không truyền list khác.
    KHÔNG ép khớp số nào có trước — gọi hàm này với HOUSEHOLD_APPLIANCES cho ra số thật."""
    if appliances is None:
        appliances = HOUSEHOLD_APPLIANCES
    return sum(a.power_w / 1000.0 * a.duration_hours * 30.0 for a in appliances)


def split_by_flexibility(appliances: List[Appliance]) -> Tuple[List[Appliance], List[Appliance]]:
    """Trả về (flexible_list, fixed_list). flexible_list (is_flexible=True) dùng để truyền
    vào qubo_builder.build_qubo() — fixed_list KHÔNG vào QUBO, chỉ đóng góp kWh cố định."""
    flexible = [a for a in appliances if a.is_flexible]
    fixed = [a for a in appliances if not a.is_flexible]
    return flexible, fixed
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd q-smartenergy && pytest tests/test_appliance_catalog.py -v`
Expected: ALL PASS. If `test_total_monthly_kwh_matches_hand_computed_value` fails because the actual sum differs from `723.075`, do NOT adjust the test tolerance to force a pass — recompute the sum by hand from the exact `power_w`/`duration_hours` values in the file above and report the discrepancy as a concern (likely a transcription typo in one entry).

- [ ] **Step 5: Run the full suite to check for regressions**

Run: `cd q-smartenergy && pytest tests/ -v`
Expected: all tests pass (this module isn't imported by anything yet, so zero regression risk).

- [ ] **Step 6: Verify the import chain**

Run: `cd q-smartenergy && python -c "import appliance_catalog; print(appliance_catalog.total_monthly_kwh())"`
Expected: prints `723.075` (or very close, floating point).

- [ ] **Step 7: Commit**

```bash
git add q-smartenergy/appliance_catalog.py q-smartenergy/tests/test_appliance_catalog.py
git commit -m "Add appliance_catalog.py: 10-type household catalog with sourced power ratings"
```

---

### Task 3: `calc.py` — rebase on real EVN tariff (5 tiers + VAT) and catalog-derived `MONTHLY_KWH`

**Files:**
- Modify: `q-smartenergy/calc.py` (full rewrite)
- Modify: `q-smartenergy/tests/test_baseline.py` (full rewrite)

**Interfaces:**
- Consumes: `appliance_catalog.total_monthly_kwh()` (Task 2).
- Produces: same public names as before (`MONTHLY_KWH`, `EVN_TIERS`, `BILL_BEFORE_VND`, `BILL_AFTER_VND`, `SAVINGS_PERCENT`, `calculate_bill`, `grid_purchase_kwh`, `SOLAR_CAPACITY_KWP`, `SOLAR_MONTHLY_GENERATION_KWH`, `SELF_CONSUMPTION_BEFORE`, `SELF_CONSUMPTION_AFTER`), PLUS new `VAT_RATE = 0.08`. REMOVES `BaselineReconciliationError` and `_check_reconciliation` (no longer needed — see below). Every other module (`data_prep.py`, `qubo_builder.py`, `quantum_runner.py`, `visualizer.py`, `app.py`) imports only the names that still exist with the same meaning, so none of them need code changes from this task alone (Task 4 updates their *documentation* only).

**Why:** `calc.py` currently defines 6 illustrative EVN tiers and a locked `MONTHLY_KWH=530` chosen to produce a pre-decided bill story. This task replaces both with real, sourced data: the actual 5-tier EVN tariff (incl. 8% VAT) and a `MONTHLY_KWH` computed from `appliance_catalog.py`. Because `BILL_BEFORE_VND`/`BILL_AFTER_VND`/`SAVINGS_PERCENT` become direct formula results instead of independently-chosen literals, the previous reconciliation-checking exception machinery has nothing left to check — it is removed as dead weight.

**Known consequence to preserve, not “fix”:** with the real 5-tier structure, `grid_purchase_kwh(SELF_CONSUMPTION_BEFORE)` (≈565.575 kWh) and `grid_purchase_kwh(SELF_CONSUMPTION_AFTER)` (≈486.825 kWh) both fall inside the SAME tier (Bậc 4: 401–700 kWh) — so the macro before/after bill comparison no longer demonstrates any "avoid tier jump" effect, only the solar self-consumption effect. This is the project owner's explicitly accepted, real finding — do not adjust `SELF_CONSUMPTION_BEFORE`/`SELF_CONSUMPTION_AFTER` or the appliance catalog to manufacture a tier-spanning scenario.

- [ ] **Step 1: Write the failing tests first**

Replace the full contents of `q-smartenergy/tests/test_baseline.py` with:

```python
"""
Tests for calc.py — rebased on the real EVN tariff (5 tiers + 8% VAT, effective
29/05/2025 per QĐ 14/2025/QĐ-TTg + QĐ 1279/QĐ-BCT) and a MONTHLY_KWH derived from
appliance_catalog.py (no longer a locked literal).
"""

import pytest

from calc import (
    BILL_AFTER_VND,
    BILL_BEFORE_VND,
    EVN_TIERS,
    MONTHLY_KWH,
    SAVINGS_PERCENT,
    SELF_CONSUMPTION_AFTER,
    SELF_CONSUMPTION_BEFORE,
    SOLAR_CAPACITY_KWP,
    SOLAR_MONTHLY_GENERATION_KWH,
    VAT_RATE,
    calculate_bill,
    grid_purchase_kwh,
)


class TestEVNTiers:
    """5-tier structure, real EVN figures (QĐ 14/2025/QĐ-TTg + QĐ 1279/QĐ-BCT)."""

    def test_evn_tiers_has_five_tiers(self):
        assert len(EVN_TIERS) == 5

    def test_evn_tier_prices_match_official_figures(self):
        expected_prices = [1984, 2380, 2998, 3571, 3967]
        actual_prices = [price for _, price in EVN_TIERS]
        assert actual_prices == expected_prices

    def test_evn_tier_thresholds_match_official_figures(self):
        expected_thresholds = [100, 200, 400, 700, float("inf")]
        actual_thresholds = [threshold for threshold, _ in EVN_TIERS]
        assert actual_thresholds == expected_thresholds

    def test_vat_rate_is_eight_percent(self):
        assert VAT_RATE == 0.08


class TestCalculateBillWithVAT:
    """calculate_bill() now includes 8% VAT — verified against hand-computed,
    single-tier cases to avoid any risk of a multi-tier arithmetic mistake."""

    def test_calculate_bill_zero(self):
        assert calculate_bill(0) == 0

    def test_calculate_bill_tier1_only_includes_vat(self):
        """50 kWh, entirely in tier 1 (0-100): 50 * 1984 = 99,200đ pre-VAT;
        *1.08 = 107,136đ exactly."""
        result = calculate_bill(50)
        assert result == pytest.approx(107136.0, abs=0.01)

    def test_calculate_bill_tier1_boundary_includes_vat(self):
        """100 kWh, exactly tier 1's upper boundary: 100 * 1984 = 198,400đ pre-VAT;
        *1.08 = 214,272đ exactly."""
        result = calculate_bill(100)
        assert result == pytest.approx(214272.0, abs=0.01)

    def test_calculate_bill_negative_input_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_bill(-10)

    def test_calculate_bill_is_monotonic(self):
        for kwh in [0, 50, 100, 200, 400, 600, 700, 900]:
            assert calculate_bill(kwh + 10) >= calculate_bill(kwh)


class TestMonthlyKwhDerivedFromCatalog:
    """MONTHLY_KWH is no longer a locked literal — it comes from appliance_catalog.py."""

    def test_monthly_kwh_matches_catalog_total(self):
        from appliance_catalog import total_monthly_kwh

        assert MONTHLY_KWH == pytest.approx(total_monthly_kwh())

    def test_monthly_kwh_is_realistic_household_scale(self):
        """Sanity bound, not a locked target: a single household's monthly consumption
        should plausibly be between 100 and 3000 kWh. This guards against a unit error
        (e.g. Wh vs kWh) in appliance_catalog.py, not a specific expected value."""
        assert 100 < MONTHLY_KWH < 3000


class TestGridPurchaseKwh:
    def test_grid_purchase_kwh_zero_consumption_equals_monthly_kwh(self):
        assert grid_purchase_kwh(0.0) == pytest.approx(MONTHLY_KWH)

    def test_grid_purchase_kwh_full_consumption(self):
        expected = MONTHLY_KWH - SOLAR_MONTHLY_GENERATION_KWH
        assert grid_purchase_kwh(1.0) == pytest.approx(expected)

    def test_grid_purchase_kwh_before_after_ordering(self):
        """Higher self-consumption must always mean less grid purchase."""
        before = grid_purchase_kwh(SELF_CONSUMPTION_BEFORE)
        after = grid_purchase_kwh(SELF_CONSUMPTION_AFTER)
        assert after < before


class TestBillBeforeAfterDerivation:
    """BILL_BEFORE_VND/BILL_AFTER_VND/SAVINGS_PERCENT are now direct formula results,
    not independently-chosen literals — these tests check the formula relationship and
    real-world properties, not a specific locked number."""

    def test_bill_before_equals_formula(self):
        expected = calculate_bill(grid_purchase_kwh(SELF_CONSUMPTION_BEFORE))
        assert BILL_BEFORE_VND == pytest.approx(expected)

    def test_bill_after_equals_formula(self):
        expected = calculate_bill(grid_purchase_kwh(SELF_CONSUMPTION_AFTER))
        assert BILL_AFTER_VND == pytest.approx(expected)

    def test_bill_after_is_less_than_bill_before(self):
        assert BILL_AFTER_VND < BILL_BEFORE_VND

    def test_savings_percent_matches_formula(self):
        expected = (BILL_BEFORE_VND - BILL_AFTER_VND) / BILL_BEFORE_VND * 100
        assert SAVINGS_PERCENT == pytest.approx(expected)

    def test_savings_percent_is_positive_but_modest(self):
        """Known consequence of the real 5-tier structure: BEFORE and AFTER grid-purchase
        both land in the same (wide) tier 4, so savings come from solar self-consumption
        alone, not tier-jump avoidance — expect single-digit-to-twenties percent, not the
        old illustrative 26.6%. This is intentional; do not adjust the catalog or
        self-consumption assumptions to force a different value here."""
        assert 0 < SAVINGS_PERCENT < 30

    def test_before_and_after_grid_purchase_fall_in_same_tier(self):
        """Documents the known real-data finding: with the actual 5-tier EVN structure,
        the BEFORE/AFTER macro comparison no longer crosses a tier boundary at all."""

        def tier_index(kwh: float) -> int:
            cumulative = 0.0
            for i, (threshold, _price) in enumerate(EVN_TIERS):
                if kwh <= threshold:
                    return i
                cumulative = threshold
            return len(EVN_TIERS) - 1

        before_tier = tier_index(grid_purchase_kwh(SELF_CONSUMPTION_BEFORE))
        after_tier = tier_index(grid_purchase_kwh(SELF_CONSUMPTION_AFTER))
        assert before_tier == after_tier == 3  # Bậc 4 (401-700 kWh), 0-indexed


class TestUnchangedConstants:
    """Solar/self-consumption assumptions are out of scope for this rebase — confirm
    they're still the same illustrative values as before."""

    def test_solar_capacity(self):
        assert SOLAR_CAPACITY_KWP == 5

    def test_solar_monthly_generation(self):
        assert SOLAR_MONTHLY_GENERATION_KWH == 525

    def test_self_consumption_tiers(self):
        assert SELF_CONSUMPTION_BEFORE == 0.30
        assert SELF_CONSUMPTION_AFTER == 0.45
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd q-smartenergy && pytest tests/test_baseline.py -v`
Expected: FAIL — `ImportError: cannot import name 'VAT_RATE' from 'calc'` (and several others, since `calc.py` hasn't changed yet).

- [ ] **Step 3: Rewrite `calc.py`**

Replace the full contents of `q-smartenergy/calc.py` with:

```python
"""
Single source of truth for Q-SmartEnergy baseline numbers.

This module defines all baseline constants and utility functions used across the project.
Every other module (data_prep, qubo_builder, quantum_runner, visualizer, app) MUST import
these values from here — DO NOT hard-code baseline numbers elsewhere.

Baseline numbers:
- Monthly consumption (MONTHLY_KWH): DERIVED from appliance_catalog.total_monthly_kwh() —
  a 10-type household appliance catalog with sourced power ratings. This is NOT a locked
  literal chosen to match a pre-decided bill story; it is whatever the real catalog sums to.
- Solar capacity: 5 kWp (illustrative, unchanged from earlier project phases)
- Solar monthly generation: 525 kWh/month (~105 kWh/kWp/month, illustrative)
- Self-consumption tiers: 30% (before optimization) → 45% (after optimization), illustrative
  (portion of solar output directly consumed; remainder is grid-exported)
- Grid-purchased kWh: MONTHLY_KWH - (SOLAR_MONTHLY_GENERATION_KWH * self_consumption_rate)
  This is the portion that incurs EVN tiered pricing charges
- Electricity bills (BILL_BEFORE_VND, BILL_AFTER_VND, SAVINGS_PERCENT): DERIVED directly
  from calculate_bill(grid_purchase_kwh(rate)) — not independently chosen literals. Because
  the real 5-tier structure's Bậc 4 (401-700 kWh) is wide, both the BEFORE and AFTER
  grid-purchase values land in that SAME tier — so this comparison demonstrates solar
  self-consumption savings only, not tier-jump avoidance. The day-level QAOA demo
  (data_prep.py's marginal-price profile) is where tier-jump avoidance still applies.

EVN Tiered Pricing (REAL, current rates — not illustrative):
- 5 bậc, hiệu lực từ 29/05/2025, theo Quyết định 14/2025/QĐ-TTg (Thủ tướng Chính phủ) và
  Quyết định 1279/QĐ-BCT ngày 09/5/2025 (Bộ Công Thương). Thay thế biểu giá 6 bậc cũ.
  Nguồn: trang chính chủ evn.com.vn ("Biểu giá bán lẻ điện theo Quyết định số 1279/QĐ-BCT"),
  đối chiếu khớp với luatvietnam.vn và vietnamsolar.vn.
- Giá CHƯA bao gồm VAT — calculate_bill() cộng thêm VAT_RATE (8%) ở bước cuối, vì hóa đơn
  EVN thật luôn gồm VAT.
- Bậc 1 (0-100 kWh): 1.984 đ/kWh
- Bậc 2 (101-200 kWh): 2.380 đ/kWh
- Bậc 3 (201-400 kWh): 2.998 đ/kWh
- Bậc 4 (401-700 kWh): 3.571 đ/kWh
- Bậc 5 (>700 kWh): 3.967 đ/kWh
- VAT điện: 8% (giảm từ 10%, áp dụng 01/07/2025-31/12/2026).

Rubric Mapping:
- III.5: Data generator based on the REAL, current EVN tiered pricing structure (not
  illustrative numbers) and a sourced household appliance catalog.
- III.3: Technical quality — accurate bill calculation (incl. VAT) as basis for
  optimization correctness.
"""

from appliance_catalog import total_monthly_kwh

# Baseline consumption and solar parameters
MONTHLY_KWH = total_monthly_kwh()  # Derived from appliance_catalog.py — NOT a locked literal
SOLAR_CAPACITY_KWP = 5
SOLAR_MONTHLY_GENERATION_KWH = 525  # Monthly solar output from 5kWp system (~105 kWh/kWp/month)
SELF_CONSUMPTION_BEFORE = 0.30
SELF_CONSUMPTION_AFTER = 0.45

# EVN tiered pricing structure (đ/kWh, NOT including VAT) — REAL rates, effective 29/05/2025
# per QĐ 14/2025/QĐ-TTg + QĐ 1279/QĐ-BCT ngày 09/5/2025. See module docstring for sourcing.
EVN_TIERS = [
    (100, 1984),
    (200, 2380),
    (400, 2998),
    (700, 3571),
    (float('inf'), 3967),
]

VAT_RATE = 0.08  # 8% VAT on electricity, effective 01/07/2025-31/12/2026


def calculate_bill(kwh: float, tiers: list = None) -> float:
    """
    Calculate electricity bill using tiered (lũy tiến) pricing structure, including VAT.

    Args:
        kwh: Grid-purchased kWh (after solar self-consumption is subtracted from total load).
        tiers: List of (threshold, price_per_kwh) tuples. Defaults to EVN_TIERS.

    Returns:
        Total bill in VND (đ), INCLUDING VAT_RATE (8%) — matches the actual amount due on
        a real EVN bill, not just the pre-VAT tariff calculation.

    Calculation logic:
        Applies cumulative tiered pricing: the first 100 kWh are charged at tier 1 rate,
        the next 100 kWh (101-200) at tier 2 rate, etc., then adds VAT_RATE on the total.

    Example:
        >>> calculate_bill(50)  # Entirely within tier 1
        107136.0  # = 50 * 1984 * 1.08
    """
    if tiers is None:
        tiers = EVN_TIERS

    if kwh < 0:
        raise ValueError("kwh must be non-negative")

    total_bill = 0.0
    remaining_kwh = kwh
    prev_threshold = 0

    for threshold, price_per_kwh in tiers:
        tier_max = threshold - prev_threshold
        if tier_max <= 0:
            # Handle edge case of inf threshold
            tier_max = remaining_kwh

        kwh_in_tier = min(remaining_kwh, tier_max)
        total_bill += kwh_in_tier * price_per_kwh
        remaining_kwh -= kwh_in_tier

        if remaining_kwh <= 0:
            break

        prev_threshold = threshold

    return total_bill * (1 + VAT_RATE)


def grid_purchase_kwh(self_consumption_rate: float) -> float:
    """
    Calculate grid-purchased kWh after solar self-consumption.

    Args:
        self_consumption_rate: Fraction of solar output self-consumed directly (0.0 to 1.0).
                              Remainder is exported to grid.

    Returns:
        kWh purchased from grid = MONTHLY_KWH - (SOLAR_MONTHLY_GENERATION_KWH * self_consumption_rate)
    """
    solar_self_consumed = SOLAR_MONTHLY_GENERATION_KWH * self_consumption_rate
    return MONTHLY_KWH - solar_self_consumed


# BILL_BEFORE_VND / BILL_AFTER_VND / SAVINGS_PERCENT are DIRECT formula results — no longer
# independently-chosen literals that need reconciliation-checking against this formula. The
# previous BaselineReconciliationError / _check_reconciliation machinery is removed because
# there is nothing left to reconcile: these ARE the formula's output, by construction.
BILL_BEFORE_VND = calculate_bill(grid_purchase_kwh(SELF_CONSUMPTION_BEFORE))
BILL_AFTER_VND = calculate_bill(grid_purchase_kwh(SELF_CONSUMPTION_AFTER))
SAVINGS_PERCENT = (BILL_BEFORE_VND - BILL_AFTER_VND) / BILL_BEFORE_VND * 100
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd q-smartenergy && pytest tests/test_baseline.py -v`
Expected: ALL PASS. If `test_before_and_after_grid_purchase_fall_in_same_tier` fails, double check your `EVN_TIERS` thresholds exactly match `[100, 200, 400, 700, float('inf')]` and that Task 2's `appliance_catalog.py` total is unchanged — do not adjust the test to force a different tier index without first confirming the inputs are exactly as specified.

- [ ] **Step 5: Run the full suite to check for regressions**

Run: `cd q-smartenergy && pytest tests/ -v`
Expected: most tests pass. `tests/test_qubo_builder.py` and `tests/test_quantum_runner.py` should be unaffected (they don't import anything from `calc.py`). If any other test file imports `calc.BILL_BEFORE_VND`/`calc.BILL_AFTER_VND` and asserts a specific old literal value (896125/658125), that test will now fail — this is Task 4's job to fix (documentation/UI text), not this task's. List any such failing tests in your report rather than fixing them here, so Task 4 has a complete list.

- [ ] **Step 6: Verify the import chain**

Run: `cd q-smartenergy && python -c "import calc; print(calc.MONTHLY_KWH, calc.BILL_BEFORE_VND, calc.BILL_AFTER_VND, calc.SAVINGS_PERCENT)"`
Expected: prints four numbers, no error. `MONTHLY_KWH` should be ≈723.075.

- [ ] **Step 7: Commit**

```bash
git add q-smartenergy/calc.py q-smartenergy/tests/test_baseline.py
git commit -m "Rebase calc.py on real EVN tariff (5 tiers + VAT) and catalog-derived MONTHLY_KWH"
```

---

### Task 4: Documentation pass — replace "6 bậc"/locked-530 references project-wide

**Files:**
- Modify: `q-smartenergy/README.md` (full rewrite of affected sections)
- Modify: any test file Task 3 flagged as failing due to old literal assertions (read Task 3's report first)
- Check (no change expected, but verify): `q-smartenergy/qubo_builder.py`, `q-smartenergy/data_prep.py`, `q-smartenergy/app.py` docstrings — none of these should mention a specific tier COUNT or the old 530/896125/658125 numbers as literals, but confirm by reading them

**Interfaces:** none new — this task only updates prose/test literals to match Task 3's rebased `calc.py`.

**Why:** `README.md`'s "Baseline Numbers" section and EVN tier table currently describe the old 6-tier illustrative system and the old locked bill figures. Any other test file that asserted the literal `896125`/`658125`/`530`/6-tier values needs updating to either import the values dynamically from `calc.py` (preferred) or be removed if it duplicated what `test_baseline.py` already verifies.

- [ ] **Step 1: Read Task 3's report**

Open the report Task 3's implementer wrote (ask the controller for its path, or check `.superpowers/sdd/task-3-report.md` if using the standard workflow) and note every test file it flagged as failing due to old literal assertions.

- [ ] **Step 2: Fix flagged test files**

For each flagged test, the fix is almost always: replace a hard-coded expected value (e.g. `assert calc.BILL_BEFORE_VND == 896125`) with either (a) deleting the assertion if `test_baseline.py` already covers the same property, or (b) importing the value dynamically and checking a property instead of a literal (e.g. `assert calc.BILL_BEFORE_VND > 0`). Do not hard-code the new computed numbers (≈1,757,450 / ≈1,453,736) as new literals — that would reintroduce the same brittleness this rebase is removing.

- [ ] **Step 3: Rewrite the README's Baseline Numbers and EVN Tiered Pricing sections**

In `q-smartenergy/README.md`, find the `## Baseline Numbers (Locked)` section and the `**EVN Tiered Pricing**` block beneath it. Replace both with:

```markdown
## Baseline Numbers

- **Monthly Consumption**: derived from `appliance_catalog.py`'s 10-type household catalog (≈723 kWh/month for the current catalog — NOT a locked target; see `appliance_catalog.py` for sourced power ratings per appliance)
- **Solar Capacity**: 5 kWp (illustrative)
- **Self-Consumption Before/After Optimization**: 30% / 45% (illustrative)
- **Bill Before/After, Savings %**: computed directly via `calc.calculate_bill(calc.grid_purchase_kwh(rate))` — not locked literals. With the real 5-tier EVN structure, both the before and after grid-purchase amounts land in the same tier (Bậc 4), so the resulting savings reflect solar self-consumption only, not tier-jump avoidance — see `calc.py`'s module docstring.

**EVN Tiered Pricing** (đ/kWh, real rates effective 29/05/2025 per QĐ 14/2025/QĐ-TTg + QĐ 1279/QĐ-BCT, NOT including 8% VAT — `calculate_bill()` adds VAT automatically):
- Bậc 1 (0–100 kWh): 1.984
- Bậc 2 (101–200 kWh): 2.380
- Bậc 3 (201–400 kWh): 2.998
- Bậc 4 (401–700 kWh): 3.571
- Bậc 5 (>700 kWh): 3.967
```

Also update the Project Structure tree and Module Roles table (if present) to add `appliance_catalog.py` and `tests/test_appliance_catalog.py`, following the same pattern used for `weather_model.py` earlier in the file.

- [ ] **Step 4: Verify no stale references remain**

Run: `grep -rn "896125\|658125\|26\.6\|1800.*1900.*2200\|six tiers\|6 bậc\|6 tiers" q-smartenergy/ --include=*.py --include=*.md`
Expected: no output. If anything appears, fix that specific file (likely a docstring or comment that wasn't updated).

- [ ] **Step 5: Run the full suite**

Run: `cd q-smartenergy && pytest tests/ -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add -A q-smartenergy/
git commit -m "Docs: update README and tests for real EVN tariff + catalog-derived MONTHLY_KWH"
```

---

### Task 5: Full acceptance re-verification

**Files:** none created or modified — read-only verification, except for fixing anything Step 3/4 below finds (then commit only that fix).

**Interfaces:** none.

**Why:** Tasks 1-4 touched the project's most foundational module (`calc.py`) plus added a new one — this is the final gate confirming the whole tree is consistent before considering this sub-project done.

- [ ] **Step 1: Run the full test suite**

Run: `cd q-smartenergy && pytest tests/ -v`
Expected: all tests pass. Record the exact pass count.

- [ ] **Step 2: Verify the full import chain**

Run: `cd q-smartenergy && python -c "import calc, appliance_catalog, data_prep, weather_model, qubo_builder, quantum_runner, visualizer, app"`
Expected: no error (Streamlit bare-mode warnings on stderr are fine).

- [ ] **Step 3: Verify no forbidden phrasing**

Run: `grep -rni "giờ cao điểm\|peak hour\|time-of-use" q-smartenergy/`
Expected: no output.

- [ ] **Step 4: Verify no stray old-tariff references**

Run: `grep -rn "896125\|658125\|1800, 1900\|1900, 2200" q-smartenergy/`
Expected: no output. If found, fix that file (it's a leftover from the old 6-tier system) and re-run Steps 1-3.

- [ ] **Step 5: Spot-check the live numbers**

Run:
```bash
cd q-smartenergy
python -c "
import calc
print(f'MONTHLY_KWH={calc.MONTHLY_KWH:.2f}')
print(f'BILL_BEFORE_VND={calc.BILL_BEFORE_VND:,.0f}')
print(f'BILL_AFTER_VND={calc.BILL_AFTER_VND:,.0f}')
print(f'SAVINGS_PERCENT={calc.SAVINGS_PERCENT:.2f}')
"
```
Record the exact printed values in your report.

- [ ] **Step 6: Smoke-test the Streamlit app headlessly**

Run:
```bash
cd q-smartenergy
streamlit run app.py --server.headless true --server.port 8765 &
sleep 5
python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8765').status)"
kill %1 2>/dev/null
```
Expected: prints `200`. Record the actual observed status code.

- [ ] **Step 7: Write the final report**

Include: full pytest pass count, import chain result, both grep results, the 4 live numbers from Step 5, the Streamlit HTTP status, and confirmation that `requirements.txt` was not modified (this plan adds no new dependency).

- [ ] **Step 8: No commit unless Step 4 required a fix**

If Step 4 found and you fixed a stray reference, commit that fix and re-run Steps 1-3 before writing the report. Otherwise, nothing to commit for this task.
