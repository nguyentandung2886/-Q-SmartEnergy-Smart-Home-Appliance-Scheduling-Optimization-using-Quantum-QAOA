"""
Billing must follow the ACTUAL schedule, not display fallbacks.

Bug #2: pinned/coerced appliances (is_flexible forced to False) were billed at the
usage_windows() fallback hour (18h) instead of the hour actually present in
flex_schedule — pinning to a sunny vs dark hour produced identical bills.

Bug #3 (reversed on purpose): fixed-branch appliances absent from
DEFAULT_USAGE_WINDOWS are now billed one FULL hour per ON hour — the hours the
user toggled on the Gantt (or the usage_windows() fallback window before any
toggle) — no longer capped at duration_hours. Every toggled hour counts toward
the bill; the trade-off is that the INITIAL estimate (before any toggle) rounds
up to the ceil(duration)-wide fallback window instead of the exact fractional
duration. Catalog appliances in DEFAULT_USAGE_WINDOWS keep their behavior
(pattern != duration).
"""
import pytest

from api.optimize_router import (
    _default_fixed_hours,
    _hourly_load,
    _worst_solar_schedule,
)
from core.qubo_builder import Appliance


# ---------- Bug #2: flex_schedule hour must win over is_flexible flag ----------

def test_pinned_appliance_billed_at_scheduled_hour_not_fallback():
    """A pinned appliance (coerced to is_flexible=False, name in flex_schedule)
    must contribute its load at the pinned hour, not at the 18h fallback window."""
    pinned = Appliance(name="Máy giặt", power_w=500, duration_hours=2,
                       candidate_hours=(13,), is_flexible=False)
    load = _hourly_load({"Máy giặt": 13}, _default_fixed_hours([pinned]), [pinned])
    assert load[13] == pytest.approx(0.5)
    assert load[14] == pytest.approx(0.5)
    assert load[18] == pytest.approx(0.0)
    assert load[19] == pytest.approx(0.0)


def test_different_pinned_hours_produce_different_loads():
    """Repro of the audit finding: pin=7 and pin=13 gave the SAME load profile
    (both fell into the 18h fallback). After the fix they must differ."""
    def load_for(pin_hour: int):
        app = Appliance(name="Máy giặt", power_w=500, duration_hours=2,
                        candidate_hours=(pin_hour,), is_flexible=False)
        return _hourly_load({"Máy giặt": pin_hour}, _default_fixed_hours([app]), [app])

    assert load_for(7) != load_for(13)


# ---------- Bug #3 reversed: every ON hour of a fallback fixed appliance bills full ----------

def test_fallback_fixed_appliance_bills_every_on_hour_in_full():
    """An unknown fixed appliance with duration 1.5h falls into the usage_windows()
    fallback (18h, ceil(1.5)=2 hours). Each ON hour bills a full hour regardless of
    duration_hours, so its daily energy is 1kW * 2h = 2.0 kWh — the deliberate
    trade-off for "every Gantt-toggled hour counts"."""
    app = Appliance(name="Thiết bị lạ", power_w=1000, duration_hours=1.5,
                    candidate_hours=(), is_flexible=False)
    load = _hourly_load({}, _default_fixed_hours([app]), [app])
    assert sum(load) == pytest.approx(2.0)


def test_catalog_fixed_appliance_keeps_usage_window_billing():
    """Catalog appliances in DEFAULT_USAGE_WINDOWS keep the current behavior: their
    real usage pattern is unrelated to duration_hours (e.g. Lò vi sóng runs 0.25h
    but is displayed/billed over its 1-hour lunch window)."""
    app = Appliance(name="Lò vi sóng", power_w=850, duration_hours=0.25,
                    candidate_hours=(), is_flexible=False)
    load = _hourly_load({}, _default_fixed_hours([app]), [app])
    assert load[12] == pytest.approx(0.85)
    assert sum(load) == pytest.approx(0.85)


# ---------- Regression: energy conservation between before and after ----------

def test_energy_conserved_with_pinned_coerced_and_fractional_mix():
    """sum(load_before) == sum(load_after) must hold for a mix of: a pinned
    appliance, a coerced one (single candidate hour), a fractional-duration
    fallback appliance, and a genuinely flexible one — as in _compute_schedule_bills."""
    pinned = Appliance(name="Máy giặt", power_w=500, duration_hours=2,
                       candidate_hours=(13,), is_flexible=False)
    coerced = Appliance(name="Máy lạ một giờ", power_w=800, duration_hours=1.5,
                        candidate_hours=(), is_flexible=False)
    flexible = Appliance(name="Bình nước nóng gián tiếp", power_w=2500,
                         duration_hours=0.5, candidate_hours=(6, 21), is_flexible=True)
    appliances = [pinned, coerced, flexible]

    solar = [0.0] * 24
    for h in range(6, 18):
        solar[h] = 1.0
    flex_before = _worst_solar_schedule([a for a in appliances if a.is_flexible], solar)
    flex_after = {"Máy giặt": 13, "Bình nước nóng gián tiếp": 6}
    fixed_hours = _default_fixed_hours(appliances)

    load_before = _hourly_load(flex_before, fixed_hours, appliances)
    load_after = _hourly_load(flex_after, fixed_hours, appliances)
    assert sum(load_before) == pytest.approx(sum(load_after))


# ---------- API level: pin to sunny hour must beat pin to dark hour ----------

def test_pin_sunny_hour_gives_lower_bill_than_dark_hour(client, auth_headers):
    """Audit repro end-to-end: Máy giặt reshaped to 500W/2h, candidate_hours (7, 13).
    Solar headroom at 13-14h beats 7-8h (day 9, sunny), so pinning to 13 must yield
    a strictly lower bill_after_vnd. Before the fix both pins billed at the 18h
    fallback and the two bills were identical."""
    headers = auth_headers("billpinuser")
    appliances = client.get("/appliances", headers=headers).json()
    washer = next(a for a in appliances if a["name"] == "Máy giặt")
    r = client.put(f"/appliances/{washer['id']}", headers=headers, json={
        "name": "Máy giặt", "power_w": 500, "duration_hours": 2,
        "candidate_hours": [7, 13], "is_flexible": True,
    })
    assert r.status_code == 200

    def optimize_with_pin(hour: int) -> dict:
        resp = client.post("/optimize", headers=headers, json={
            "day_of_month": 9, "weather_condition": "sunny", "use_quantum": False,
            "pinned_schedule": {"Máy giặt": hour},
        })
        assert resp.status_code == 200
        return resp.json()

    sunny_pin = optimize_with_pin(13)
    dark_pin = optimize_with_pin(7)

    # Gantt contract unchanged: pinned hour appears in schedule, not fixed_windows.
    assert sunny_pin["schedule"]["Máy giặt"] == 13
    assert "Máy giặt" not in sunny_pin["fixed_windows"]

    # bill_before is pin-independent; bill_after must reward the sunnier hour.
    assert sunny_pin["bill_before_vnd"] == pytest.approx(dark_pin["bill_before_vnd"])
    assert sunny_pin["bill_after_vnd"] < dark_pin["bill_after_vnd"]
