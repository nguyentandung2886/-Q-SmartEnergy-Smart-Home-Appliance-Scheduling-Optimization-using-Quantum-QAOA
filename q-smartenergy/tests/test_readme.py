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
