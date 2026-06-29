# Score Improvement (76→90+) + Solar Bonus Tier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the gaps an independent strict review found in Q-SmartEnergy (76/100 on Rubric III, 22/25 on the Vòng Phụ bonus tier) by (a) making the "Hybrid Quantum-Classical" architecture concrete via a weather-aware solar forecasting layer, (b) fixing a real correctness gap (`assert` strippable under `python -O`), (c) making documentation/pitch claims honest instead of overselling, (d) adding genuine QAOA hyperparameter comparison evidence, and (e) replacing `app.py`'s hard-coded demo inputs with real user controls.

**Architecture:** No existing module's public interface is removed or broken — `qubo_builder.py` and its QUBO formulation are untouched (the review's biggest concern, criterion 2, is fixed by being honest in docs/UI text and by giving users a "weather" lever that lets the tier-jump axis visibly dominate when solar is weak, not by changing the math). One new module (`weather_model.py`) is added as the classical forecasting layer; `data_prep.py` gains an optional `weather_condition` parameter; `quantum_runner.py` gains a hyperparameter-comparison utility; `app.py` is rewired with real input widgets; `calc.py` and `README.md` get correctness/honesty fixes.

**Tech Stack:** Python 3.13, numpy, pandas, matplotlib, streamlit, qiskit + qiskit-optimization + qiskit-aer + qiskit-algorithms, pytest. No new third-party dependencies are added by this plan.

## Global Constraints

- Work only inside `q-smartenergy/` (and its `tests/` subdirectory) plus `README.md` inside that directory. Do not touch files outside `q-smartenergy/`.
- Single source of truth discipline: no baseline number (530, 525, 896125, 658125, the six EVN tier thresholds/prices, 0.30/0.45, 5000) may be hard-coded in any file except `calc.py`. Every other module imports it.
- NEVER use "giờ cao điểm" / "peak hour" / "time-of-use" anywhere (code, comments, docstrings, strings, variable names). EVN pricing is tiered/cumulative-monthly (bậc thang/lũy tiến), not time-of-day.
- Every new/changed public function needs a docstring stating input/output and (where applicable) a `# Rubric ...` tag, matching the existing style in this codebase (see any current `.py` file for the pattern).
- Every task must leave `pytest tests/` fully green (no regressions) before its commit.
- Do not change the existing public signatures of `qubo_builder.build_qubo`, `Appliance`, `TimeSlot`, `QuantumScheduler.__init__`, or `ScheduleResult` — only ADD new optional parameters with defaults, never remove/rename/reorder existing ones, since existing tests and existing call sites depend on them exactly as they are.
- Weather conditions are exactly three strings: `"sunny"`, `"cloudy"`, `"rainy"`, with multipliers `1.0`, `0.6`, `0.25` respectively — these exact values are used throughout this plan's tests; do not substitute different numbers.
- This plan does not add any new pip dependency. If a task seems to need one, stop and report NEEDS_CONTEXT instead of adding it.

---

### Task 1: `calc.py` — replace strippable `assert` with a real exception; disclose EVN rate sourcing

**Files:**
- Modify: `q-smartenergy/calc.py:140-158`
- Modify: `q-smartenergy/calc.py:19-23` (EVN Tiered Pricing docstring section)
- Test: `q-smartenergy/tests/test_baseline.py`

**Interfaces:**
- Produces: `calc.BaselineReconciliationError` (new exception class), `calc._check_reconciliation(calculated: float, expected: float, label: str) -> None` (new internal function, raises `BaselineReconciliationError` if `abs(calculated - expected) > 1`).
- Consumes: nothing new — uses existing `calculate_bill`, `grid_purchase_kwh`, `SELF_CONSUMPTION_BEFORE/AFTER`, `BILL_BEFORE_VND/AFTER_VND`.

**Why:** the independent review found `calc.py:145,154` uses bare `assert` to lock the baseline reconciliation. Running Python with `-O` strips all `assert` statements, silently disabling this safety check. A real `raise` survives `-O`.

- [ ] **Step 1: Write the failing tests**

Open `q-smartenergy/tests/test_baseline.py` and add this new test class at the end of the file (after the existing classes, same indentation level as `class TestBaselineConstants:`):

```python
class TestReconciliationCheck:
    """Test calc._check_reconciliation() — the non-assert baseline lock (Task 1,
    score-improvement plan). Using `assert` here was a real bug: `python -O` strips
    assert statements, silently disabling the safety check."""

    def test_check_reconciliation_passes_within_tolerance(self):
        """Values within ±1đ must not raise."""
        from calc import _check_reconciliation
        _check_reconciliation(896125.4, 896125, "TEST")  # should not raise

    def test_check_reconciliation_raises_outside_tolerance(self):
        """Values differing by more than ±1đ must raise BaselineReconciliationError."""
        from calc import _check_reconciliation, BaselineReconciliationError
        with pytest.raises(BaselineReconciliationError):
            _check_reconciliation(900000, 896125, "TEST")

    def test_baseline_reconciliation_error_is_exception_subclass(self):
        from calc import BaselineReconciliationError
        assert issubclass(BaselineReconciliationError, Exception)

    def test_module_level_reconciliation_still_holds(self):
        """The module-level checks (BEFORE/AFTER) must still pass at import time —
        this is implicitly verified by `import calc` succeeding at all, but assert it
        explicitly here so a future regression fails this test, not just import."""
        from calc import (
            BILL_AFTER_VND,
            BILL_BEFORE_VND,
            SELF_CONSUMPTION_AFTER,
            SELF_CONSUMPTION_BEFORE,
            calculate_bill,
            grid_purchase_kwh,
        )
        assert abs(calculate_bill(grid_purchase_kwh(SELF_CONSUMPTION_BEFORE)) - BILL_BEFORE_VND) <= 1
        assert abs(calculate_bill(grid_purchase_kwh(SELF_CONSUMPTION_AFTER)) - BILL_AFTER_VND) <= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd q-smartenergy && pytest tests/test_baseline.py::TestReconciliationCheck -v`
Expected: FAIL — `ImportError: cannot import name '_check_reconciliation' from 'calc'` (and `BaselineReconciliationError` doesn't exist yet).

- [ ] **Step 3: Replace the EVN Tiered Pricing docstring section**

In `q-smartenergy/calc.py`, replace lines 19-23 (the `EVN Tiered Pricing:` block inside the module docstring):

```python
EVN Tiered Pricing:
- The pricing follows Vietnam's standard tiered electricity pricing structure (EVN sinh hoạt).
- Thresholds (reference): 0-50 kWh (tier 1), 51-100 (tier 2), 101-200 (tier 3),
  201-300 (tier 4), 301-400 (tier 5), >400 (tier 6).
- These thresholds are configurable if EVN updates rates.
```

with:

```python
EVN Tiered Pricing:
- The pricing MECHANISM (price increases in steps as cumulative monthly kWh rises) follows
  Vietnam's residential tiered/lũy tiến structure mandated by QĐ 14/2025/QĐ-TTg, QĐ 1279/QĐ-BCT,
  and QĐ 963/QĐ-BCT (cited in the team's own proposal). This mechanism is real.
- The SPECIFIC threshold/price values below (1,800-3,150đ/kWh across 6 tiers) are illustrative
  numbers chosen to produce this PoC's locked baseline story (530 kWh/month, 896,125đ ->
  658,125đ) — they are NOT a verbatim transcription of the latest published EVN rate table.
  Do not present them to a judge as "the current official EVN price list" without checking
  the latest published rates first.
- Thresholds used here: 0-50 kWh (tier 1), 51-100 (tier 2), 101-200 (tier 3),
  201-300 (tier 4), 301-400 (tier 5), >400 (tier 6).
- These thresholds/prices are configurable if real, current EVN rates need to be substituted.
```

- [ ] **Step 4: Replace the assert-based validation with a real exception**

In `q-smartenergy/calc.py`, replace lines 140-158 (everything from `# Validation: calculate_bill...` to the end of the file):

```python
class BaselineReconciliationError(Exception):
    """Raised at import time if calc.py's locked baseline bills don't reconcile with
    calculate_bill(grid_purchase_kwh(...)). A real exception is used here instead of
    `assert` deliberately: `python -O` strips all `assert` statements, which would
    silently disable this safety check."""


def _check_reconciliation(calculated: float, expected: float, label: str) -> None:
    """Raise BaselineReconciliationError if `calculated` and `expected` don't
    reconcile within ±1đ (float rounding tolerance only — these must match almost
    exactly). Extracted as a standalone function (not an inline assert) so it survives
    `python -O` and is directly unit-testable with both passing and failing inputs.
    """
    diff = abs(calculated - expected)
    if diff > 1:
        raise BaselineReconciliationError(
            f"Bill mismatch ({label}): calculated={calculated:.0f}đ, expected={expected:.0f}đ. "
            f"Difference: {diff:.0f}đ. This indicates EVN tier thresholds or "
            f"SOLAR_MONTHLY_GENERATION_KWH need adjustment."
        )


# Validation: calculate_bill(grid_purchase_kwh(...)) must match the locked baseline bills.
# Tolerance: ±1đ (float rounding only; these must reconcile almost exactly).
_check_reconciliation(
    calculate_bill(grid_purchase_kwh(SELF_CONSUMPTION_BEFORE)), BILL_BEFORE_VND, "BEFORE"
)
_check_reconciliation(
    calculate_bill(grid_purchase_kwh(SELF_CONSUMPTION_AFTER)), BILL_AFTER_VND, "AFTER"
)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd q-smartenergy && pytest tests/test_baseline.py -v`
Expected: ALL PASS, including the 4 new `TestReconciliationCheck` tests.

- [ ] **Step 6: Run the full suite to check for regressions**

Run: `cd q-smartenergy && pytest tests/ -v`
Expected: all tests pass (63 existing + 4 new = 67), no regressions.

- [ ] **Step 7: Commit**

```bash
git add q-smartenergy/calc.py q-smartenergy/tests/test_baseline.py
git commit -m "Fix: calc.py baseline lock uses raise instead of assert; disclose EVN rate sourcing"
```

---

### Task 2: `weather_model.py` — new classical weather-forecast module (Vòng Phụ bonus tier)

**Files:**
- Create: `q-smartenergy/weather_model.py`
- Test: `q-smartenergy/tests/test_weather_model.py`

**Interfaces:**
- Produces: `weather_model.WEATHER_MULTIPLIERS: dict[str, float]` (exactly `{"sunny": 1.0, "cloudy": 0.6, "rainy": 0.25}`), `weather_model.solar_multiplier(weather_condition: str) -> float` (raises `ValueError` for any other string).
- Consumes: nothing — this is a leaf module with no project imports.

**Why:** the proposal's own pitch describes "dự báo sản lượng điện mặt trời theo giờ dựa trên ... dữ liệu thời tiết đơn giản (nắng/mây)" as the classical half of a Hybrid Quantum-Classical architecture (Vòng Phụ Mức Khó, +25đ). Today nothing in the code models weather at all — solar generation is a fixed curve regardless of conditions. This task adds that classical layer as an isolated, trivially-testable module.

- [ ] **Step 1: Write the failing tests**

Create `q-smartenergy/tests/test_weather_model.py`:

```python
"""
Tests for weather_model.py — the classical weather-forecast layer of the Hybrid
Quantum-Classical architecture (Vòng Phụ Mức Khó, +25đ).
"""

import pytest

from weather_model import WEATHER_MULTIPLIERS, solar_multiplier


def test_sunny_multiplier_is_one():
    assert solar_multiplier("sunny") == 1.0


def test_cloudy_multiplier_is_zero_point_six():
    assert solar_multiplier("cloudy") == 0.6


def test_rainy_multiplier_is_zero_point_two_five():
    assert solar_multiplier("rainy") == 0.25


def test_invalid_weather_condition_raises_value_error():
    with pytest.raises(ValueError):
        solar_multiplier("snowy")


def test_all_multipliers_in_valid_range():
    for condition, multiplier in WEATHER_MULTIPLIERS.items():
        assert 0 < multiplier <= 1.0, f"{condition} multiplier {multiplier} out of (0,1] range"


def test_exactly_three_weather_conditions_defined():
    assert set(WEATHER_MULTIPLIERS.keys()) == {"sunny", "cloudy", "rainy"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd q-smartenergy && pytest tests/test_weather_model.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'weather_model'`.

- [ ] **Step 3: Write the implementation**

Create `q-smartenergy/weather_model.py`:

```python
"""
Weather Model for Q-SmartEnergy — the CLASSICAL layer of the Hybrid Quantum-Classical
architecture (Vòng Phụ Mức Khó, +25đ).

Input:
  - weather_condition: str, one of "sunny", "cloudy", "rainy" — a simulated daily weather
    state (the proposal's "dữ liệu thời tiết đơn giản nắng/mây").

Output:
  - solar_multiplier(): a float in (0, 1] that scales expected solar generation for that day.

Economic/Physical Meaning:
  Cloud cover and rain materially reduce rooftop solar output. This module is the CLASSICAL
  forecasting layer: it converts a simple weather observation into a numeric adjustment that
  data_prep.py applies to the solar generation curve BEFORE that curve is handed to
  qubo_builder.py (the QUANTUM/QUBO layer). The QUBO/QAOA layer never needs to know weather
  exists — it only ever sees the resulting solar_kwh numbers. This is what makes the
  architecture "Hybrid": classical forecasting feeds quantum optimization through a clean
  data interface, not a quantum-aware weather model.

Rubric Mapping:
  # Vòng Phụ Mức Khó (+25đ) - kiến trúc Hybrid Quantum-Classical / năng lượng tái tạo trong objective
  # Rubric III.2 - ánh xạ đúng ràng buộc đời thực (thời tiết ảnh hưởng sản lượng solar thật)
"""

WEATHER_MULTIPLIERS = {
    "sunny": 1.0,
    "cloudy": 0.6,
    "rainy": 0.25,
}


def solar_multiplier(weather_condition: str) -> float:
    """Hệ số điều chỉnh sản lượng solar theo thời tiết mô phỏng (0 < hệ số <= 1).

    Args:
        weather_condition: một trong "sunny", "cloudy", "rainy".

    Returns:
        Hệ số nhân áp vào đường cong sản lượng solar (xem data_prep.generate_solar_profile).

    Raises:
        ValueError: nếu weather_condition không thuộc WEATHER_MULTIPLIERS.
    """
    if weather_condition not in WEATHER_MULTIPLIERS:
        valid = ", ".join(sorted(WEATHER_MULTIPLIERS))
        raise ValueError(
            f"weather_condition {weather_condition!r} không hợp lệ — phải là 1 trong: {valid}"
        )
    return WEATHER_MULTIPLIERS[weather_condition]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd q-smartenergy && pytest tests/test_weather_model.py -v`
Expected: ALL 6 PASS.

- [ ] **Step 5: Run the full suite to check for regressions**

Run: `cd q-smartenergy && pytest tests/ -v`
Expected: all tests pass, no regressions.

- [ ] **Step 6: Commit**

```bash
git add q-smartenergy/weather_model.py q-smartenergy/tests/test_weather_model.py
git commit -m "Add weather_model.py: classical weather-forecast layer for solar bonus tier"
```

---

### Task 3: `data_prep.py` — thread `weather_condition` through the solar profile

**Files:**
- Modify: `q-smartenergy/data_prep.py` (imports, `generate_solar_profile`, `build_daily_profile`, module docstring)
- Test: `q-smartenergy/tests/test_data_prep.py`

**Interfaces:**
- Consumes: `weather_model.solar_multiplier(weather_condition: str) -> float` (Task 2).
- Produces: `generate_solar_profile(monthly_generation_kwh: float = SOLAR_MONTHLY_GENERATION_KWH, weather_condition: str = "sunny") -> pd.Series` (new optional param, default preserves old behavior exactly), `build_daily_profile(day_of_month: int = 15, weather_condition: str = "sunny") -> pd.DataFrame` (same — new optional param, default preserves old behavior). `qubo_builder.py` and `quantum_runner.py` are NOT modified by this task and need no changes — they only ever consumed the `solar_kwh`/`price_per_kwh` columns of the DataFrame `build_daily_profile` returns, never cared how those numbers were derived.

- [ ] **Step 1: Write the failing tests**

Open `q-smartenergy/tests/test_data_prep.py` and add these test functions at the end of the file (top-level functions, matching the existing file's style — it already imports `generate_solar_profile` and `build_daily_profile` directly at the top, so no new imports are needed):

```python
def test_generate_solar_profile_cloudy_scales_by_point_six():
    """weather_condition='cloudy' must scale the total daily solar output by exactly 0.6
    relative to the 'sunny' (default) profile."""
    sunny = generate_solar_profile(weather_condition="sunny")
    cloudy = generate_solar_profile(weather_condition="cloudy")
    assert cloudy.sum() == pytest.approx(sunny.sum() * 0.6, rel=1e-9)


def test_generate_solar_profile_rainy_scales_by_point_two_five():
    sunny = generate_solar_profile(weather_condition="sunny")
    rainy = generate_solar_profile(weather_condition="rainy")
    assert rainy.sum() == pytest.approx(sunny.sum() * 0.25, rel=1e-9)


def test_generate_solar_profile_default_weather_is_sunny():
    """Calling with no weather_condition must behave identically to weather_condition='sunny'
    (this is what preserves the existing 'flat'/no-weather behavior of every caller that
    doesn't pass the new parameter)."""
    default = generate_solar_profile()
    explicit_sunny = generate_solar_profile(weather_condition="sunny")
    assert list(default.values) == list(explicit_sunny.values)


def test_generate_solar_profile_invalid_weather_raises():
    with pytest.raises(ValueError):
        generate_solar_profile(weather_condition="snowy")


def test_build_daily_profile_passes_through_weather_condition():
    sunny_profile = build_daily_profile(day_of_month=12, weather_condition="sunny")
    rainy_profile = build_daily_profile(day_of_month=12, weather_condition="rainy")
    assert rainy_profile["solar_kwh"].sum() == pytest.approx(
        sunny_profile["solar_kwh"].sum() * 0.25, rel=1e-9
    )
    # price_per_kwh must be unaffected by weather (weather only touches solar, never price)
    assert list(sunny_profile["price_per_kwh"]) == list(rainy_profile["price_per_kwh"])


def test_build_daily_profile_default_weather_unchanged():
    """Calling build_daily_profile(day_of_month=...) with no weather_condition must match
    the pre-existing behavior exactly — this is the regression guard for this task."""
    default = build_daily_profile(day_of_month=12)
    explicit_sunny = build_daily_profile(day_of_month=12, weather_condition="sunny")
    assert list(default["solar_kwh"]) == list(explicit_sunny["solar_kwh"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd q-smartenergy && pytest tests/test_data_prep.py -v`
Expected: FAIL — `TypeError: generate_solar_profile() got an unexpected keyword argument 'weather_condition'`.

- [ ] **Step 3: Add the import**

In `q-smartenergy/data_prep.py`, in the imports section (currently lines 33-36):

```python
import numpy as np
import pandas as pd

from calc import MONTHLY_KWH, SOLAR_MONTHLY_GENERATION_KWH, EVN_TIERS
```

change to:

```python
import numpy as np
import pandas as pd

from calc import MONTHLY_KWH, SOLAR_MONTHLY_GENERATION_KWH, EVN_TIERS
from weather_model import solar_multiplier
```

- [ ] **Step 4: Update `generate_solar_profile`**

Replace the current `generate_solar_profile` function (lines 39-49):

```python
def generate_solar_profile(monthly_generation_kwh: float = SOLAR_MONTHLY_GENERATION_KWH) -> pd.Series:
    """24 hourly solar generation values (kWh) for a representative day, bell-shaped
    (Gaussian) curve peaking at hour 12, generating only within the 06:00-18:00 window.
    Total for the day equals monthly_generation_kwh / 30."""
    hours = np.arange(24)
    sigma = 3.0
    raw = np.exp(-((hours - 12.0) ** 2) / (2 * sigma ** 2))
    raw[(hours < 6) | (hours > 18)] = 0.0
    daily_avg = monthly_generation_kwh / 30.0
    scaled = raw / raw.sum() * daily_avg
    return pd.Series(scaled, index=hours, name="solar_kwh")
```

with:

```python
def generate_solar_profile(
    monthly_generation_kwh: float = SOLAR_MONTHLY_GENERATION_KWH,
    weather_condition: str = "sunny",
) -> pd.Series:
    """24 hourly solar generation values (kWh) for a representative day, bell-shaped
    (Gaussian) curve peaking at hour 12, generating only within the 06:00-18:00 window.
    Total for a "sunny" day equals monthly_generation_kwh / 30; weather_condition scales
    that total via weather_model.solar_multiplier() — the classical forecasting layer of
    the Hybrid Quantum-Classical architecture (see weather_model.py). Raises ValueError
    for any weather_condition not in weather_model.WEATHER_MULTIPLIERS."""
    hours = np.arange(24)
    sigma = 3.0
    raw = np.exp(-((hours - 12.0) ** 2) / (2 * sigma ** 2))
    raw[(hours < 6) | (hours > 18)] = 0.0
    daily_avg = monthly_generation_kwh / 30.0 * solar_multiplier(weather_condition)
    scaled = raw / raw.sum() * daily_avg
    return pd.Series(scaled, index=hours, name="solar_kwh")
```

- [ ] **Step 5: Update `build_daily_profile`**

Replace the current `build_daily_profile` function (lines 79-88):

```python
def build_daily_profile(day_of_month: int = 15) -> pd.DataFrame:
    """24-row DataFrame (columns: hour, solar_kwh, price_per_kwh), one row per hour of the
    representative day."""
    solar = generate_solar_profile()
    price = generate_tier_price_profile(day_of_month)
    return pd.DataFrame({
        "hour": range(24),
        "solar_kwh": solar.values,
        "price_per_kwh": price.values,
    })
```

with:

```python
def build_daily_profile(day_of_month: int = 15, weather_condition: str = "sunny") -> pd.DataFrame:
    """24-row DataFrame (columns: hour, solar_kwh, price_per_kwh), one row per hour of the
    representative day. weather_condition ("sunny"/"cloudy"/"rainy") scales solar_kwh via
    weather_model.solar_multiplier() — see generate_solar_profile(). price_per_kwh is never
    affected by weather (EVN tiered pricing has nothing to do with weather)."""
    solar = generate_solar_profile(weather_condition=weather_condition)
    price = generate_tier_price_profile(day_of_month)
    return pd.DataFrame({
        "hour": range(24),
        "solar_kwh": solar.values,
        "price_per_kwh": price.values,
    })
```

- [ ] **Step 6: Update the module docstring**

In `q-smartenergy/data_prep.py`, in the module docstring's `Output:` bullet list (around line 9-16), add one bullet right after the `generate_solar_profile()` bullet:

Find:
```
  - generate_solar_profile(): 24 hourly solar generation values (kWh) for a representative
    day, bell-shaped (Gaussian) around noon, daylight-only (06:00-18:00).
```

Replace with:
```
  - generate_solar_profile(): 24 hourly solar generation values (kWh) for a representative
    day, bell-shaped (Gaussian) around noon, daylight-only (06:00-18:00). Accepts an optional
    weather_condition ("sunny"/"cloudy"/"rainy", default "sunny") that scales the total via
    weather_model.solar_multiplier() — the classical forecasting layer feeding this PoC's
    Hybrid Quantum-Classical architecture (see weather_model.py).
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd q-smartenergy && pytest tests/test_data_prep.py -v`
Expected: ALL PASS.

- [ ] **Step 8: Run the full suite to check for regressions**

Run: `cd q-smartenergy && pytest tests/ -v`
Expected: all tests pass, no regressions. In particular `tests/test_qubo_builder.py` and `tests/test_quantum_runner.py` must still pass unmodified, since `build_daily_profile()`'s default behavior (no weather_condition passed) is unchanged.

- [ ] **Step 9: Verify the import chain still works**

Run: `cd q-smartenergy && python -c "import calc, data_prep, qubo_builder, quantum_runner, visualizer, app, weather_model"`
Expected: no error.

- [ ] **Step 10: Commit**

```bash
git add q-smartenergy/data_prep.py q-smartenergy/tests/test_data_prep.py
git commit -m "Wire weather_condition through data_prep.py solar profile generation"
```

---

### Task 4: `quantum_runner.py` — genuine QAOA hyperparameter comparison evidence

**Files:**
- Modify: `q-smartenergy/quantum_runner.py`
- Test: `q-smartenergy/tests/test_quantum_runner.py`

**Interfaces:**
- Produces: `quantum_runner.compare_qaoa_hyperparameters(Q: np.ndarray, configs: List[Tuple[int, int]] = None, seed: int = 42) -> List[Dict[str, object]]`.
- Consumes: existing `solve_qaoa`, `solve_classical_bruteforce`, `QAOAExecutionError` (all already in this file — no new imports of other project modules needed).

**Why:** the independent review found that `reps=1, maxiter=50` are hardcoded defaults never tuned or compared against alternatives, while the project's docstrings and the rubric itself (III.3: "hiểu rõ cách tuning các tham số (hyperparameters) ... để đạt độ chính xác cao") claim genuine hyperparameter understanding. This task makes that claim true by adding a function that runs several `(reps, maxiter)` configurations on the same QUBO, measures runtime, and checks each result against the classical brute-force global optimum.

- [ ] **Step 1: Write the failing tests**

Open `q-smartenergy/tests/test_quantum_runner.py` and add this import to the existing `from quantum_runner import (...)` block at the top of the file — add `compare_qaoa_hyperparameters` to the list of names already being imported (alongside `QAOAExecutionError`, `QuantumScheduler`, etc.), then add these test functions at the end of the file:

```python
def test_compare_qaoa_hyperparameters_returns_one_row_per_config():
    Q = np.array([[1.0, 2.0], [0.0, -1.0]])
    results = compare_qaoa_hyperparameters(Q, configs=[(1, 25), (2, 50)])
    assert len(results) == 2
    for row in results:
        assert row["reps"] in (1, 2)
        assert row["runtime_seconds"] > 0
        assert "matches_global_optimum" in row


def test_compare_qaoa_hyperparameters_flags_global_optimum_correctly():
    """On the hand-computed Q from solve_classical_bruteforce's own test (minimum is
    bitstring '01', energy -1.0), every successful QAOA run that actually finds energy
    -1.0 must be flagged matches_global_optimum=True, and none may be flagged True at a
    different energy."""
    Q = np.array([[1.0, 2.0], [0.0, -1.0]])
    results = compare_qaoa_hyperparameters(Q, configs=[(1, 50), (2, 50), (3, 100)])
    for row in results:
        if row["error"] is None:
            if row["matches_global_optimum"]:
                assert row["energy"] == pytest.approx(-1.0, abs=1e-6)
            else:
                assert row["energy"] != pytest.approx(-1.0, abs=1e-6)


def test_compare_qaoa_hyperparameters_default_configs_on_default_scenario():
    """On the project's own DEFAULT_APPLIANCES scenario (4 qubits), at least one of the
    default hyperparameter configs must find the global optimum — this is the concrete,
    checkable evidence backing the project's "understands QAOA hyperparameter tuning"
    claim (rubric III.3)."""
    Q, _ = build_qubo(DEFAULT_APPLIANCES, build_daily_profile())
    results = compare_qaoa_hyperparameters(Q)
    assert len(results) == 4
    assert any(row["matches_global_optimum"] for row in results if row["error"] is None)
```

This requires two more imports at the top of `tests/test_quantum_runner.py`: add `from qubo_builder import build_qubo` (the file already imports `DEFAULT_APPLIANCES` from `qubo_builder`, just add `build_qubo` alongside it on the same `from qubo_builder import ...` line) and confirm `from data_prep import build_daily_profile` is present (it already is, per the file's existing imports).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd q-smartenergy && pytest tests/test_quantum_runner.py -v`
Expected: FAIL — `ImportError: cannot import name 'compare_qaoa_hyperparameters' from 'quantum_runner'`.

- [ ] **Step 3: Write the implementation**

In `q-smartenergy/quantum_runner.py`, add this function after `solve_qaoa` (i.e., right after the function ending at line 124, before `def is_valid_one_hot`):

```python
def compare_qaoa_hyperparameters(
    Q: np.ndarray,
    configs: List[Tuple[int, int]] = None,
    seed: int = 42,
) -> List[Dict[str, object]]:
    """Chạy QAOA với nhiều cấu hình (reps, maxiter) trên cùng Q, đo runtime + energy đạt
    được, và so sánh với global optimum (brute-force) để đánh giá độ chính xác — minh
    chứng hiểu rõ trade-off tuning tham số QAOA.
    # Rubric III.3 - hiểu rõ cách tuning các tham số (hyperparameters) của thuật toán
    #                 lượng tử để đạt độ chính xác cao

    Args:
        Q: ma trận QUBO upper-triangular (cùng convention với build_qubo/solve_qaoa).
        configs: list (reps, maxiter) cần so sánh. Default 4 cấu hình từ rẻ -> đắt:
                 [(1, 25), (1, 50), (2, 50), (3, 100)].
        seed: seed cố định cho mọi lần chạy (so sánh công bằng giữa các cấu hình).

    Returns:
        List[dict], mỗi dict có các khóa: "reps", "maxiter", "bitstring", "energy",
        "runtime_seconds", "matches_global_optimum" (so với solve_classical_bruteforce(Q)),
        "error" (None nếu chạy thành công, ngược lại str mô tả lỗi). Nếu 1 cấu hình QAOA
        lỗi, dict đó có bitstring/energy/matches_global_optimum = None/None/False và
        "error" chứa thông báo — KHÔNG để exception lan ra ngoài (không crash khi hiển thị
        phân tích này trong demo).
    """
    if configs is None:
        configs = [(1, 25), (1, 50), (2, 50), (3, 100)]

    _, optimal_energy = solve_classical_bruteforce(Q)

    results: List[Dict[str, object]] = []
    for reps, maxiter in configs:
        start = time.perf_counter()
        try:
            bitstring, energy = solve_qaoa(Q, reps=reps, maxiter=maxiter, seed=seed)
            runtime = time.perf_counter() - start
            results.append({
                "reps": reps,
                "maxiter": maxiter,
                "bitstring": bitstring,
                "energy": energy,
                "runtime_seconds": runtime,
                "matches_global_optimum": abs(energy - optimal_energy) < 1e-6,
                "error": None,
            })
        except QAOAExecutionError as exc:
            results.append({
                "reps": reps,
                "maxiter": maxiter,
                "bitstring": None,
                "energy": None,
                "runtime_seconds": time.perf_counter() - start,
                "matches_global_optimum": False,
                "error": str(exc),
            })
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd q-smartenergy && pytest tests/test_quantum_runner.py -v`
Expected: ALL PASS. Note: these tests run real QAOA several times (up to 4 configs × 2 tests using the 4-qubit scenario) and may take 10-30 seconds total — this is expected, not a hang.

- [ ] **Step 5: Run the full suite to check for regressions**

Run: `cd q-smartenergy && pytest tests/ -v`
Expected: all tests pass, no regressions.

- [ ] **Step 6: Commit**

```bash
git add q-smartenergy/quantum_runner.py q-smartenergy/tests/test_quantum_runner.py
git commit -m "Add compare_qaoa_hyperparameters: real evidence for QAOA tuning claims"
```

---

### Task 5: `app.py` — real user input, weather control, and honest narrative

**Files:**
- Modify: `q-smartenergy/app.py` (full rewrite)
- Test: `q-smartenergy/tests/test_app.py`

**Interfaces:**
- Consumes: `weather_model` (Task 2, via `data_prep.build_daily_profile(weather_condition=...)`, Task 3), `quantum_runner.compare_qaoa_hyperparameters` (Task 4), `qubo_builder.Appliance` / `qubo_builder.DEFAULT_APPLIANCES` (existing, unchanged).
- Produces: `run_optimization(appliances=None, day_of_month: int = 12, weather_condition: str = "sunny", use_quantum: bool = True) -> quantum_runner.ScheduleResult` — same return type as before, with two new optional parameters (`weather_condition`) inserted; existing callers `run_optimization()` and `run_optimization(use_quantum=False)` remain valid since all new parameters have defaults.

**Why:** the independent review found `app.py` is a one-button skeleton with zero real user input (appliances and day hard-coded) despite its own docstring promising "user appliance configuration" — this directly caps rubric criterion 6 (Giao diện & UX/UI) at 6/10. This task adds real Streamlit widgets for weather, day-of-month, and per-appliance power/duration, and softens the "avoids tier jumps" narrative to the honest "balances both axes" framing the review flagged as criterion 2/4's biggest risk.

- [ ] **Step 1: Write the failing tests**

Open `q-smartenergy/tests/test_app.py` and add these test functions at the end of the file:

```python
def test_run_optimization_with_weather_condition_returns_valid_schedule():
    result = app.run_optimization(weather_condition="rainy")
    assert isinstance(result, ScheduleResult)
    assert len(result.schedule) == len(qubo_builder.DEFAULT_APPLIANCES)
    for appliance in qubo_builder.DEFAULT_APPLIANCES:
        assert appliance.name in result.schedule
        assert result.schedule[appliance.name] in appliance.candidate_hours


def test_run_optimization_with_custom_appliances():
    custom = [
        qubo_builder.Appliance(
            name="Test Appliance", power_w=1000, duration_hours=1, candidate_hours=(6, 12)
        ),
    ]
    result = app.run_optimization(appliances=custom)
    assert result.schedule["Test Appliance"] in (6, 12)


def test_run_optimization_invalid_weather_raises_value_error():
    with pytest.raises(ValueError):
        app.run_optimization(weather_condition="snowy")
```

This requires adding `import pytest` to the top of `tests/test_app.py` if it isn't already imported (check the file's existing imports first — if `pytest` is not imported, add `import pytest` alongside the existing `import app`, `import data_prep`, `import qubo_builder`, `from quantum_runner import ScheduleResult` lines).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd q-smartenergy && pytest tests/test_app.py -v`
Expected: FAIL — `TypeError: run_optimization() got an unexpected keyword argument 'weather_condition'`.

- [ ] **Step 3: Replace `app.py` entirely**

Replace the full contents of `q-smartenergy/app.py` with:

```python
"""
Streamlit Web Application for Q-SmartEnergy.
# Rubric III.6 - Giao diện & UX/UI

Input:
  - User-editable appliance configuration (power_w, duration_hours per appliance —
    candidate_hours stay fixed per appliance so the QUBO's variable count is well-defined)
  - day_of_month (1-30): vị trí trong chu kỳ bậc giá EVN tháng (xem data_prep.py)
  - weather_condition ("sunny"/"cloudy"/"rainy"): lớp classical dự báo solar (weather_model.py)

Output:
  - Interactive dashboard showing:
    * Lịch chạy tối ưu (Gantt chart)
    * So sánh hóa đơn dự báo cả tháng (calc.py — số dự báo cố định, KHÔNG đổi theo input
      demo; xem ghi chú minh bạch hiển thị cùng kết quả)
    * Kết quả solve thật (2 thiết bị demo) + phân tích tuning hyperparameter QAOA

Economic/Physical Meaning:
  - Người dùng thử các kịch bản khác nhau (công suất thiết bị, ngày trong tháng, thời tiết)
    và thấy lịch chạy + nghiệm QUBO thay đổi theo thời gian thực — đây là cách demo thể hiện
    rằng optimizer thực sự cân bằng 2 trục giá trị (tránh nhảy bậc giá vs tối đa solar), không
    chỉ lúc nào cũng làm đúng 1 việc.

Rubric Mapping:
  - III.1 (Visualization): UI palette (Indigo #3730A3, Teal #0F766E, Gold #CA8A04)
  - III.4 (User Experience): input thật cho thiết bị/ngày/thời tiết, không hard-code
  - III.5 (Data Integration): Pulls baseline from calc.py, displays results from pipeline
  - Vòng Phụ Mức Khó (+25đ): weather_condition là lớp classical feed vào QUBO/QAOA
"""

import calc
import data_prep
import qubo_builder
import quantum_runner
import visualizer
import weather_model


def run_optimization(
    appliances=None,
    day_of_month: int = 12,
    weather_condition: str = "sunny",
    use_quantum: bool = True,
):
    """Logic thuần: chạy toàn bộ pipeline data_prep -> qubo_builder -> quantum_runner.
    Tách riêng khỏi UI Streamlit để unit test được mà không cần streamlit runtime.

    Input: appliances (list qubo_builder.Appliance, default DEFAULT_APPLIANCES nếu None),
           day_of_month (1-30), weather_condition ("sunny"/"cloudy"/"rainy", default "sunny").
    Output: quantum_runner.ScheduleResult.

    day_of_month default = 12 (KHÔNG phải 15): đã verify bằng tay ngày 12/30 có nhảy bậc giá
    THẬT trong ngày (lũy kế trước ngày 12 ~194.33 kWh, ngưỡng 200kWh rơi giữa ngày -> giá
    chuyển 2200đ sang 2700đ/kWh ngay trong 24 giờ đó). Ngày 15 cho giá PHẲNG suốt ngày. Đừng
    đổi lại 15 nếu chưa kiểm tra data_prep.generate_tier_price_profile(day_of_month=...) có
    >=2 giá khác nhau.

    LƯU Ý TRUNG THỰC (xem qubo_builder.build_qubo để biết công thức đầy đủ): khi solar đủ
    mạnh (vd thời tiết "sunny"), optimizer có thể CHỦ ĐỘNG chọn giờ ở bậc giá cao hơn nếu
    phần solar che được lớn hơn phần chênh lệch bậc giá — đây KHÔNG phải lỗi, optimizer đang
    tối ưu đúng theo H_cost + H_solar. Khi thời tiết xấu (vd "rainy"), solar yếu đi và trục
    "tránh nhảy bậc giá" trở thành yếu tố quyết định rõ hơn — đổi weather_condition trong UI
    để thấy cả 2 trục giá trị hoạt động, đừng chỉ demo với "sunny".
    """
    if appliances is None:
        appliances = qubo_builder.DEFAULT_APPLIANCES
    profile = data_prep.build_daily_profile(day_of_month, weather_condition=weather_condition)
    scheduler = quantum_runner.QuantumScheduler(appliances, profile)
    return scheduler.solve(use_quantum=use_quantum)


# --- Phần UI Streamlit (chỉ chạy khi `streamlit run app.py`, không chạy khi import để test) ---
import streamlit as st

st.set_page_config(page_title="Q-SmartEnergy", page_icon="⚡")

st.markdown(
    """
    <style>
    h1 { color: #3730A3; }
    .stButton>button { background-color: #0F766E; color: white; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Q-SmartEnergy")
st.write(
    "Lập lịch thiết bị điện gia dụng bằng QAOA — cân bằng giữa tránh nhảy bậc giá EVN và "
    "tối đa hóa self-consumption điện mặt trời (xem ghi chú minh bạch bên dưới sau khi tối ưu)."
)

st.subheader("Cấu hình demo")

_WEATHER_LABEL_TO_CONDITION = {"Nắng": "sunny", "Có mây": "cloudy", "Mưa": "rainy"}
weather_label = st.selectbox("Thời tiết hôm nay", list(_WEATHER_LABEL_TO_CONDITION.keys()))
weather_condition = _WEATHER_LABEL_TO_CONDITION[weather_label]

day_of_month = st.slider(
    "Ngày trong tháng (vị trí lũy kế trong bậc giá EVN)", min_value=1, max_value=30, value=12
)

edited_appliances = []
for appliance in qubo_builder.DEFAULT_APPLIANCES:
    st.write(f"**{appliance.name}** (giờ khả dụng: {appliance.candidate_hours})")
    col1, col2 = st.columns(2)
    with col1:
        power_w = st.number_input(
            f"Công suất {appliance.name} (W)",
            min_value=1.0,
            value=float(appliance.power_w),
            key=f"power_{appliance.name}",
        )
    with col2:
        duration_hours = st.number_input(
            f"Thời gian chạy {appliance.name} (giờ)",
            min_value=0.1,
            value=float(appliance.duration_hours),
            key=f"duration_{appliance.name}",
        )
    edited_appliances.append(
        qubo_builder.Appliance(
            name=appliance.name,
            power_w=power_w,
            duration_hours=duration_hours,
            candidate_hours=appliance.candidate_hours,
        )
    )

if st.button("Tối ưu hóa"):
    try:
        result = run_optimization(
            appliances=edited_appliances,
            day_of_month=day_of_month,
            weather_condition=weather_condition,
        )
        st.pyplot(visualizer.plot_schedule_gantt(result.schedule, edited_appliances))
        st.pyplot(visualizer.plot_cost_comparison())
        st.success(f"Lịch chạy tối ưu (solver: {result.solver_used}, fallback: {result.used_fallback})")

        st.subheader("Kết quả demo (lịch chạy thật từ QAOA/fallback)")
        for name, hour in result.schedule.items():
            st.write(f"- {name}: chạy lúc {hour}h")
        st.caption(
            f"Thời tiết: {weather_label} | Ngày: {day_of_month}/30 | "
            f"Solver: {result.solver_used} | Fallback: {result.used_fallback} | "
            f"QUBO energy: {result.energy:.0f}"
        )
        st.info(
            "Biểu đồ hóa đơn ở trên là số liệu dự báo cho hộ mẫu 530 kWh/tháng (calc.py, minh "
            "họa quy mô tiết kiệm cả tháng khi áp dụng rộng) — KHÔNG phải số tính trực tiếp từ "
            "2 thiết bị demo phía trên."
        )

        with st.expander("Phân tích tuning hyperparameter QAOA (reps/maxiter)"):
            analysis_profile = data_prep.build_daily_profile(
                day_of_month, weather_condition=weather_condition
            )
            analysis_scheduler = quantum_runner.QuantumScheduler(edited_appliances, analysis_profile)
            comparison = quantum_runner.compare_qaoa_hyperparameters(analysis_scheduler.Q)
            st.table(comparison)
            st.caption(
                "So sánh nhiều cấu hình (reps, maxiter) trên cùng bài toán QUBO của demo này — "
                "matches_global_optimum đối chiếu với nghiệm brute-force chính xác (ở quy mô PoC "
                "nhỏ, brute-force luôn cho global optimum để kiểm chứng QAOA)."
            )
    except Exception as exc:
        st.error(f"Lỗi khi tối ưu hóa: {exc}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd q-smartenergy && pytest tests/test_app.py -v`
Expected: ALL PASS (existing tests + 3 new ones).

- [ ] **Step 5: Verify `import app` still works outside Streamlit's runtime**

Run: `cd q-smartenergy && python -c "import app"`
Expected: no exception (Streamlit prints `ScriptRunContext`-related warnings to stderr — that is expected and non-fatal, matching this project's established pattern from Tuần 1's app.py work; widgets like `st.selectbox`/`st.slider`/`st.number_input` return their default value in this "bare mode" without raising). If this actually raises an exception (not just warnings), STOP and report NEEDS_CONTEXT — do not silently work around it, since the whole test suite for `app.py` depends on import-time safety.

- [ ] **Step 6: Run the full suite to check for regressions**

Run: `cd q-smartenergy && pytest tests/ -v`
Expected: all tests pass, no regressions.

- [ ] **Step 7: Commit**

```bash
git add q-smartenergy/app.py q-smartenergy/tests/test_app.py
git commit -m "app.py: real user input (weather/day/appliance config) + honest narrative + QAOA tuning panel"
```

---

### Task 6: Documentation pass — `README.md` and `qubo_builder.py` honesty/accuracy fixes

**Files:**
- Modify: `q-smartenergy/README.md` (full rewrite)
- Modify: `q-smartenergy/qubo_builder.py:18-30` (module docstring — add one clarifying paragraph, no code changes)
- Test: `q-smartenergy/tests/test_readme.py` (new, lightweight content-assertion test)

**Why:** the independent review found `README.md`'s rubric-mapping table (lines 74-82) doesn't match the actual competition rubric's criteria, the project tree is stale (missing `weather_model.py` and 4 of the 6 existing test files, since it was written in Task 1 of Tuần 1 before those existed), and the overview paragraph oversells "avoiding tier jumps" the same way `app.py` did before Task 5. None of this is a code-logic change — it's purely bringing documentation in line with what the code (after Tasks 1-5) actually does.

- [ ] **Step 1: Write the failing test**

Create `q-smartenergy/tests/test_readme.py`:

```python
"""
Lightweight content checks for README.md — guards against documentation drifting from
what the code actually does (score-improvement plan, Task 6).
"""

from pathlib import Path

README_PATH = Path(__file__).resolve().parent.parent / "README.md"


def _read_readme() -> str:
    return README_PATH.read_text(encoding="utf-8")


def test_readme_mentions_weather_model():
    content = _read_readme()
    assert "weather_model.py" in content


def test_readme_does_not_overclaim_tier_jump_avoidance():
    """The overview must not assert the system simply 'avoids' tier jumps — it balances
    that against solar self-consumption and may deliberately accept a higher tier. This
    guards against the exact overclaim an independent review flagged."""
    content = _read_readme()
    assert "helping families avoid expensive EVN tier jumps" not in content


def test_readme_discloses_illustrative_evn_rates():
    content = _read_readme()
    assert "illustrative" in content.lower()
```

Note: this file deliberately does NOT add a test asserting the forbidden-phrase substrings ("giờ cao điểm" / "peak hour" / "time-of-use") are absent from README.md — writing those substrings as Python string literals inside a file under `q-smartenergy/tests/` would itself violate the Global Constraint banning their use "anywhere (code, comments, docstrings, strings, variable names)" and would trip Task 7's project-wide grep check on this very test file. That check is already covered, without this self-referential trap, by Task 7 Step 3's shell `grep` command — don't duplicate it here.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd q-smartenergy && pytest tests/test_readme.py -v`
Expected: at least `test_readme_mentions_weather_model` and `test_readme_does_not_overclaim_tier_jump_avoidance` and `test_readme_discloses_illustrative_evn_rates` FAIL (the current README has none of this).

- [ ] **Step 3: Replace `README.md` in full**

Replace the full contents of `q-smartenergy/README.md` with:

```markdown
# Q-SmartEnergy

Quantum-optimized home appliance scheduling leveraging QAOA (Quantum Approximate Optimization Algorithm) to balance Vietnam's tiered EVN electricity pricing against rooftop solar self-consumption.

## Overview

Q-SmartEnergy is a PoC (Proof of Concept) that uses quantum computing to solve the appliance scheduling problem: given a household's flexible appliances, a tiered electricity pricing structure, and expected rooftop solar output, when should each appliance run to minimize the monthly bill?

The optimizer balances two value axes inside a single QUBO objective: avoiding EVN tier-price jumps (the more total kWh purchased from the grid this month, the higher the marginal price) and maximizing solar self-consumption (kWh covered by free rooftop solar is never billed at all). These two axes can pull in different directions — when solar at a given hour is strong enough, the optimizer may deliberately schedule an appliance into a higher-priced tier because the solar-covered savings outweigh the tier difference. The system is honest about this tradeoff rather than claiming it always avoids tier jumps; see `qubo_builder.py`'s module docstring for the exact math.

A weather-aware classical forecasting layer (`weather_model.py`) feeds simulated daily conditions ("sunny"/"cloudy"/"rainy") into the solar generation forecast, making the Hybrid Quantum-Classical architecture concrete: when solar is weak (e.g. "rainy"), the tier-avoidance axis becomes the dominant signal; when solar is strong, self-consumption dominates.

## Project Structure

```
q-smartenergy/
├── calc.py                  # Single source of truth for baseline constants & bill calculation
├── data_prep.py              # EVN tier price profile + solar generation profile (weather-aware)
├── weather_model.py          # Classical weather-forecast layer (Hybrid Quantum-Classical bonus)
├── qubo_builder.py           # QUBO formulation for quantum optimization
├── quantum_runner.py         # QAOA execution on Qiskit Aer Simulator + classical fallback
├── visualizer.py              # Gantt chart & bill comparison chart
├── app.py                     # Streamlit web UI dashboard
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── tests/
    ├── __init__.py
    ├── test_baseline.py        # Tests for calc.py baseline constants
    ├── test_data_prep.py       # Tests for data_prep.py
    ├── test_weather_model.py   # Tests for weather_model.py
    ├── test_qubo_builder.py    # Tests for qubo_builder.py
    ├── test_quantum_runner.py  # Tests for quantum_runner.py
    ├── test_visualizer.py      # Tests for visualizer.py
    ├── test_app.py             # Tests for app.py
    └── test_readme.py          # Content checks for this file
```

### Module Roles

| Module | Purpose |
|--------|---------|
| `calc.py` | **Baseline lock**: all project constants (530 kWh/month, EVN tier prices, bill targets). Every other module imports from here — never hard-code. |
| `data_prep.py` | Prepares the EVN marginal-tier-price profile and the (weather-aware) solar generation profile for a representative day. |
| `weather_model.py` | Classical forecasting layer: converts a simulated weather condition into a solar-output multiplier — the "classical" half of the Hybrid Quantum-Classical architecture. |
| `qubo_builder.py` | Encodes the appliance scheduling problem as a QUBO (Quadratic Unconstrained Binary Optimization) matrix. |
| `quantum_runner.py` | Executes QAOA on Qiskit Aer Simulator to find optimal schedules, with a mandatory classical brute-force fallback and a hyperparameter-comparison utility. |
| `visualizer.py` | Generates the schedule Gantt chart and the bill comparison bar chart. |
| `app.py` | Streamlit dashboard — lets users edit appliance power/duration, pick a day of month, and pick a weather condition, then view the optimized schedule. |

## Setup & Usage

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Tests
```bash
pytest tests/
```

### Run the Web App
```bash
streamlit run app.py
```

## Baseline Numbers (Locked)

- **Monthly Consumption**: 530 kWh
- **Solar Capacity**: 5 kWp (525 kWh/month generation)
- **Self-Consumption Before Optimization**: 30%
- **Self-Consumption After Optimization**: 45%
- **Bill Before Optimization**: 896,125đ
- **Bill After Optimization**: 658,125đ
- **Savings**: 26.6%

These macro numbers represent a whole-month, whole-household projection (see `calc.py`) — they are a different scale from the 2-appliance live demo scenario shown in the Gantt chart, and `app.py` labels them separately so the two are never confused.

**EVN Tiered Pricing** (đ/kWh) used in this PoC:
- Tier 1 (0–50 kWh): 1,800
- Tier 2 (51–100 kWh): 1,900
- Tier 3 (101–200 kWh): 2,200
- Tier 4 (201–300 kWh): 2,700
- Tier 5 (301–400 kWh): 3,050
- Tier 6 (>400 kWh): 3,150

The tiered/lũy tiến MECHANISM (price rises in steps with cumulative monthly kWh, regardless of time of day) follows real EVN regulation (QĐ 14/2025/QĐ-TTg, QĐ 1279/QĐ-BCT, QĐ 963/QĐ-BCT). The specific threshold/price VALUES above are illustrative numbers chosen to produce this PoC's locked baseline story — they are not a verbatim transcription of the latest published EVN rate table (see `calc.py`'s module docstring for the full disclosure).

## Rubric Mapping

This project addresses the Vòng Chung Kết rubric (see `[Q-SmartEnergy] Khung Tiêu Chí Đánh Giá & AI Guidelines.md`, Section III):
- **III.1 — Tính năng & mức độ hoàn thiện**: OOP (`Appliance`, `TimeSlot`, `QuantumScheduler` dataclasses), full type hints, real try/except around every simulator call and every chart-drawing call so the demo cannot crash.
- **III.2 — Giải quyết vấn đề thực tiễn**: the QUBO's `H_cost`/`H_solar`/`H_onehot`/`H_power` terms map directly to real constraints (tiered pricing, solar self-consumption, "runs exactly once", simultaneous-power safety) — see `qubo_builder.py`.
- **III.3 — Chất lượng kỹ thuật**: real Qiskit-Optimization usage (QUBO → QuadraticProgram → QAOA on Aer), with `quantum_runner.compare_qaoa_hyperparameters()` providing concrete evidence of hyperparameter tuning understanding, not just a claim.
- **III.4 — Trình bày & thuyết phục**: docstrings throughout state the economic meaning of every parameter; the UI's transparency notes explicitly distinguish the macro projection from the live demo result.
- **III.5 — Kết quả triển khai thực tế**: `data_prep.py` generates a real tiered-pricing profile; `calc.py` discloses exactly which numbers are illustrative vs. which mechanism is real.
- **III.6 — Giao diện & trải nghiệm UX/UI**: Streamlit app with real user input (appliance power/duration, day of month, weather condition), Indigo/Teal/Gold palette, Qiskit results rendered live.

Also addresses the Vòng Phụ bonus tier (Section II, Mức Khó +25đ): `weather_model.py` is the classical forecasting layer of a Hybrid Quantum-Classical architecture, feeding renewable-energy (rooftop solar) data into the QUBO objective function.

## Notes

- All baseline constants must be imported from `calc.py` — never replicate numbers in other modules.
- The project runs quantum circuits on Qiskit Aer Simulator (no hardware backend required for PoC).
- EVN tiered pricing uses cumulative/lũy tiến (staircase) pricing structure — pricing depends only on total monthly kWh consumed, never on the hour of day or day of week.
```

- [ ] **Step 4: Add the clarifying paragraph to `qubo_builder.py`'s module docstring**

In `q-smartenergy/qubo_builder.py`, in the module docstring's `Economic/Physical Meaning:` section (lines 18-30), find the line:

```
  Note: price_per_kwh is the marginal EVN TIER price (bậc thang/lũy tiến) at that point
  in the monthly cumulative total — NOT a time-of-day rate. There is no time-of-day
  pricing in this market.
```

and add this paragraph immediately after it (still inside the docstring, before the `Rubric Mapping:` section):

```
  Honesty note: H_cost and H_solar can pull in different directions. When solar at an
  hour is strong enough to cover most/all of an appliance's energy, the optimizer may
  deliberately choose that hour even if its marginal tier price is HIGHER than another
  candidate hour — because the solar-covered savings outweigh the tier difference. This
  is correct behavior, not a bug: it is exactly what minimizing H_cost + H_solar together
  means. Do not claim this system "always avoids tier jumps" — claim that it balances tier
  avoidance against solar self-consumption, and let whichever axis has the bigger lever at
  that hour win.
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd q-smartenergy && pytest tests/test_readme.py -v`
Expected: ALL PASS.

- [ ] **Step 6: Run the full suite to check for regressions**

Run: `cd q-smartenergy && pytest tests/ -v`
Expected: all tests pass, no regressions.

- [ ] **Step 7: Commit**

```bash
git add q-smartenergy/README.md q-smartenergy/qubo_builder.py q-smartenergy/tests/test_readme.py
git commit -m "Docs: fix rubric mapping, disclose illustrative EVN rates, honest tier/solar tradeoff framing"
```

---

### Task 7: Full acceptance re-verification

**Files:**
- None created or modified — this task only runs verification commands and records results in its report. If any check fails, fix the specific failure in the file it points to before re-running (do not skip a failing check).

**Interfaces:** none — this is a read-only verification task.

**Why:** Tasks 1-6 touched 7 files across the project; this task is the final gate confirming the whole `q-smartenergy/` tree is still internally consistent (no broken import chain, no forbidden phrasing anywhere, no hard-coded baseline numbers leaked into a new file, the Streamlit app still boots) before calling this round of fixes complete.

- [ ] **Step 1: Run the full test suite**

Run: `cd q-smartenergy && pytest tests/ -v`
Expected: all tests pass (67 from before this plan + ~20 new across Tasks 1-6). Record the exact pass count in your report.

- [ ] **Step 2: Verify the full import chain**

Run: `cd q-smartenergy && python -c "import calc, data_prep, weather_model, qubo_builder, quantum_runner, visualizer, app"`
Expected: no error.

- [ ] **Step 3: Verify no forbidden phrasing anywhere in the project**

Run: `grep -rni "giờ cao điểm\|peak hour\|time-of-use" q-smartenergy/`
Expected: no output (empty match).

- [ ] **Step 4: Verify no new hard-coded baseline numbers**

Run: `grep -rn "896125\|658125\|530\b" q-smartenergy/*.py | grep -v "^q-smartenergy/calc.py"`
Expected: no output (these numbers must only appear in `calc.py`). If any line appears, go fix that file to import from `calc.py` instead before continuing.

- [ ] **Step 5: Smoke-test the Streamlit app headlessly**

Run:
```bash
cd q-smartenergy
streamlit run app.py --server.headless true --server.port 8765 &
sleep 5
python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8765').status)"
kill %1 2>/dev/null
```
Expected: prints `200`. Record the actual observed status code in your report — do not claim 200 without having actually seen it printed.

- [ ] **Step 6: Verify `requirements.txt` still matches actual imports**

Run: `cd q-smartenergy && python -c "import qiskit, qiskit_optimization, qiskit_aer, qiskit_algorithms, numpy, pandas, matplotlib, streamlit, pytest; print('all imports OK')"`
Expected: prints `all imports OK`. No new dependency should have been needed by Tasks 1-6 (per Global Constraints) — confirm `requirements.txt` was not modified by `git diff --stat` against the commit before Task 1.

- [ ] **Step 7: Write the final report**

In your task report, include: the full pytest pass count, the import chain result, the forbidden-phrasing grep result, the hard-coded-number grep result, the actual HTTP status from the Streamlit smoke test, and a short before/after summary mapping each of Tasks 1-6 back to the specific independent-review finding it addressed (Task 1 → criterion 1 assert/criterion 5 disclosure; Task 2+3 → Vòng Phụ bonus tier; Task 4 → criterion 3; Task 5 → criterion 2/4/6; Task 6 → criterion 2/4/5 documentation). Do not estimate a new numeric score — that requires a fresh independent review, not self-assessment.

- [ ] **Step 8: No commit for this task**

This task makes no file changes, so there is nothing to commit. If Step 4 found a violation and you fixed it, commit that fix with an appropriate message and re-run Steps 1-6 before writing the report.
