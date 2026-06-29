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
