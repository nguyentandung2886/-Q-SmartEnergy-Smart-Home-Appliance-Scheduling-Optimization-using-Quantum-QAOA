"""
Tests for visualizer.py.

Verifies (per Task 5 brief):
1. plot_cost_comparison() with no args (defaults from calc.py) returns a Figure
   with exactly 2 bars, bar heights matching calc.BILL_BEFORE_VND / BILL_AFTER_VND,
   and bar colors drawn from PALETTE.
2. plot_cost_comparison(bill_before_vnd=..., bill_after_vnd=...) — override args
   actually used instead of the calc.py defaults.
3. plot_schedule_gantt(schedule, DEFAULT_APPLIANCES) with a valid schedule returns
   a Figure with exactly 2 horizontal bars (one per appliance in schedule).
4. plot_schedule_gantt() with a schedule referencing an appliance not present in
   appliances must NOT raise — returns an (error) Figure instead.
5. plot_cost_comparison() with a non-numeric bill_before_vnd must NOT raise —
   returns an (error) Figure instead.
"""

import matplotlib

matplotlib.use("Agg")

import matplotlib.figure
import pytest

from calc import BILL_AFTER_VND, BILL_BEFORE_VND
from qubo_builder import DEFAULT_APPLIANCES
from visualizer import PALETTE, plot_cost_comparison, plot_schedule_gantt


def _facecolor_to_hex(patch) -> str:
    """Convert a matplotlib patch's RGBA facecolor to a #RRGGBB hex string."""
    r, g, b, _a = patch.get_facecolor()
    return "#{:02X}{:02X}{:02X}".format(round(r * 255), round(g * 255), round(b * 255))


class TestPlotCostComparisonDefaults:
    """Test 1: default args (None) pull from calc.py baseline numbers."""

    def setup_method(self):
        self.fig = plot_cost_comparison()

    def test_returns_figure(self):
        assert isinstance(self.fig, matplotlib.figure.Figure)

    def test_exactly_two_bars(self):
        ax = self.fig.axes[0]
        assert len(ax.patches) == 2

    def test_bar_heights_match_baseline(self):
        ax = self.fig.axes[0]
        heights = sorted(patch.get_height() for patch in ax.patches)
        expected = sorted([BILL_BEFORE_VND, BILL_AFTER_VND])
        assert heights[0] == pytest.approx(expected[0])
        assert heights[1] == pytest.approx(expected[1])

    def test_bar_colors_in_palette(self):
        ax = self.fig.axes[0]
        for patch in ax.patches:
            assert _facecolor_to_hex(patch) in PALETTE


class TestPlotCostComparisonOverride:
    """Test 2: explicit args override calc.py defaults."""

    def test_override_values_used(self):
        fig = plot_cost_comparison(bill_before_vnd=1_000_000, bill_after_vnd=500_000)
        ax = fig.axes[0]
        heights = sorted(patch.get_height() for patch in ax.patches)
        assert heights == [500_000, 1_000_000]


class TestPlotScheduleGantt:
    """Test 3: valid schedule -> Figure with one bar per appliance."""

    def test_returns_figure_with_two_bars(self):
        schedule = {"Máy giặt": 7, "Bình nước nóng": 6}
        fig = plot_schedule_gantt(schedule, DEFAULT_APPLIANCES)
        assert isinstance(fig, matplotlib.figure.Figure)
        ax = fig.axes[0]
        assert len(ax.patches) == 2


class TestPlotScheduleGanttErrorHandling:
    """Test 4: mismatched schedule/appliances must not raise; returns error Figure."""

    def test_unknown_appliance_does_not_raise(self):
        schedule = {"Thiết bị không tồn tại": 5}
        fig = plot_schedule_gantt(schedule, DEFAULT_APPLIANCES)
        assert fig is not None
        assert isinstance(fig, matplotlib.figure.Figure)


class TestPlotCostComparisonErrorHandling:
    """Test 5: non-numeric bill_before_vnd must not raise; returns error Figure."""

    def test_non_numeric_bill_does_not_raise(self):
        fig = plot_cost_comparison(bill_before_vnd="không phải số")
        assert fig is not None
        assert isinstance(fig, matplotlib.figure.Figure)
