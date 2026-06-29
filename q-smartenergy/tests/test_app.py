"""
Tests for app.py.

Verifies (per Task 6 brief):
1. run_optimization() (no args) returns a valid quantum_runner.ScheduleResult —
   schedule has exactly 2 entries (matching qubo_builder.DEFAULT_APPLIANCES), and
   each chosen hour is one of that appliance's candidate_hours.
2. run_optimization(use_quantum=False) returns solver_used == "classical_bruteforce".
3. Importing app.py does not raise and does not auto-open a UI/crash when run under
   pytest (Streamlit module-level code executes in "bare mode" on import — no
   ScriptRunContext, no exception; verified manually via `python -c "import app"`
   before writing this test, per brief instructions).
"""

import app
import data_prep
import qubo_builder
from quantum_runner import ScheduleResult


def test_run_optimization_default_returns_valid_schedule():
    result = app.run_optimization()
    assert isinstance(result, ScheduleResult)
    assert len(result.schedule) == len(qubo_builder.DEFAULT_APPLIANCES)
    for appliance in qubo_builder.DEFAULT_APPLIANCES:
        assert appliance.name in result.schedule
        assert result.schedule[appliance.name] in appliance.candidate_hours


def test_run_optimization_classical_solver():
    result = app.run_optimization(use_quantum=False)
    assert result.solver_used == "classical_bruteforce"


def test_import_app_does_not_raise():
    # If `import app` (module-level Streamlit calls included) raised, this test
    # module would already have failed to collect. This test just asserts the
    # module object is present and exposes the expected pure-logic function.
    assert hasattr(app, "run_optimization")


def test_default_day_has_nonflat_tier_price():
    # Regression-guard (Task 7): day 12 must have a genuine intraday tier jump
    # (>=2 distinct marginal prices across its 24 hours), unlike day 15 (flat all
    # day). This protects app.run_optimization's default day_of_month=12 from being
    # silently reverted to a flat-pricing day without anyone re-checking the signal.
    profile = data_prep.generate_tier_price_profile(day_of_month=12)
    assert len(set(profile.values)) >= 2


def test_run_optimization_default_day_returns_valid_schedule():
    # Same shape check as test_run_optimization_default_returns_valid_schedule, but
    # explicit about exercising the new default day_of_month=12 end-to-end: the
    # pipeline must still produce a valid schedule, not just "day 12 has price signal".
    result = app.run_optimization()
    assert isinstance(result, ScheduleResult)
    assert len(result.schedule) == len(qubo_builder.DEFAULT_APPLIANCES)
    for appliance in qubo_builder.DEFAULT_APPLIANCES:
        assert appliance.name in result.schedule
        assert result.schedule[appliance.name] in appliance.candidate_hours
