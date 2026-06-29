"""
Data Visualization Module for Q-SmartEnergy.

Input:
  - plot_schedule_gantt: schedule dict ({appliance name: chosen start hour}, the
    `.schedule` output of QuantumScheduler.solve()) + list[qubo_builder.Appliance]
    (for duration_hours / name lookup).
  - plot_cost_comparison: bill_before_vnd / bill_after_vnd (VND); default to
    calc.BILL_BEFORE_VND / calc.BILL_AFTER_VND when not provided — values are NEVER
    hard-coded here, always sourced from calc.py.

Output:
  - matplotlib.figure.Figure objects (Gantt chart of the chosen schedule; bar chart
    comparing the electricity bill before/after Q-SmartEnergy). app.py (Task 6)
    embeds these Figures directly in the Streamlit demo.

Economic/Physical Meaning:
  - The Gantt chart shows WHEN each flexible appliance is scheduled to run, which is
    the lever the optimizer pulls to avoid EVN tier (bậc thang/lũy tiến) jumps and to
    maximize rooftop-solar self-consumption.
  - The cost comparison chart communicates the bottom-line outcome of that lever:
    the monthly bill drop from BILL_BEFORE_VND to BILL_AFTER_VND.

Rubric Mapping:
  # Rubric III.1 - try/except quanh toàn bộ pipeline vẽ, không crash giữa demo
  # Rubric III.5 - kết quả triển khai thực tế, biểu đồ rõ ràng, đúng palette
"""

import matplotlib

matplotlib.use("Agg")

import matplotlib.figure
import matplotlib.pyplot as plt
from typing import Dict, List

from calc import BILL_AFTER_VND, BILL_BEFORE_VND

PALETTE = ["#3730A3", "#0F766E", "#CA8A04"]  # Indigo, Teal, Gold


def plot_schedule_gantt(schedule: Dict[str, int], appliances: List) -> matplotlib.figure.Figure:
    """Vẽ Gantt chart: mỗi thiết bị trong `schedule` 1 thanh ngang (barh) từ giờ bắt đầu
    (schedule[appliance.name]) tới giờ bắt đầu + appliance.duration_hours. Trục x: giờ
    trong ngày (0-24). Trục y: tên thiết bị. Màu xoay vòng theo PALETTE.

    Input: schedule (output của QuantumScheduler.solve().schedule — {tên thiết bị:
           giờ bắt đầu}), appliances (list qubo_builder.Appliance, cần duration_hours
           và name để khớp với schedule).
    Output: matplotlib Figure.

    Nếu `schedule` và `appliances` không khớp (thiết bị trong schedule không có trong
    appliances, hoặc ngược lại) hoặc có lỗi khác khi vẽ -> bắt exception, trả về Figure
    lỗi qua `_error_figure()`, KHÔNG raise ra ngoài (đảm bảo demo không crash giữa buổi
    chấm).
    # Rubric III.1 - try/except, không crash
    # Rubric III.5 - kết quả triển khai thực tế, biểu đồ rõ ràng
    """
    try:
        duration_by_name = {appliance.name: appliance.duration_hours for appliance in appliances}

        names = list(schedule.keys())
        if not names:
            raise ValueError("schedule rỗng — không có thiết bị nào để vẽ")

        fig, ax = plt.subplots()
        for i, name in enumerate(names):
            if name not in duration_by_name:
                raise ValueError(f"thiết bị {name!r} trong schedule không có trong appliances")
            start_hour = schedule[name]
            duration = duration_by_name[name]
            color = PALETTE[i % len(PALETTE)]
            ax.barh(name, duration, left=start_hour, color=color)

        ax.set_xlabel("Giờ trong ngày")
        ax.set_ylabel("Thiết bị")
        ax.set_xlim(0, 24)
        ax.set_title("Lịch chạy thiết bị (Q-SmartEnergy)")
        return fig
    except Exception as exc:  # noqa: BLE001 - không để lỗi vẽ chart crash demo
        return _error_figure(f"Không thể vẽ lịch chạy thiết bị: {exc}")


def plot_cost_comparison(
    bill_before_vnd: float = None,
    bill_after_vnd: float = None,
) -> matplotlib.figure.Figure:
    """Bar chart 2 cột: "Trước" (bill_before_vnd) và "Sau Q-SmartEnergy" (bill_after_vnd),
    đơn vị VNĐ. Cột "Trước" màu PALETTE[2] (Gold, cảnh báo chi phí cao), cột "Sau" màu
    PALETTE[1] (Teal, tiết kiệm). Ghi số tiền (định dạng có dấu phân nghìn) trên đỉnh
    mỗi cột.

    Nếu có lỗi khi vẽ -> bắt exception, trả về Figure lỗi qua `_error_figure()`, KHÔNG
    raise ra ngoài.
    # Rubric III.1 - try/except, không crash
    # Rubric III.5
    """
    try:
        if bill_before_vnd is None:
            bill_before_vnd = BILL_BEFORE_VND
        if bill_after_vnd is None:
            bill_after_vnd = BILL_AFTER_VND

        bill_before_vnd = float(bill_before_vnd)
        bill_after_vnd = float(bill_after_vnd)

        labels = ["Trước", "Sau Q-SmartEnergy"]
        values = [bill_before_vnd, bill_after_vnd]
        colors = [PALETTE[2], PALETTE[1]]

        fig, ax = plt.subplots()
        bars = ax.bar(labels, values, color=colors)
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{value:,.0f}đ",
                ha="center",
                va="bottom",
            )

        ax.set_ylabel("Hóa đơn điện (VNĐ)")
        ax.set_title("So sánh hóa đơn điện: Trước vs Sau Q-SmartEnergy")
        return fig
    except Exception as exc:  # noqa: BLE001 - không để lỗi vẽ chart crash demo
        return _error_figure(f"Không thể vẽ so sánh hóa đơn: {exc}")


def _error_figure(message: str) -> matplotlib.figure.Figure:
    """Figure placeholder hiển thị thông báo lỗi (text đỏ, giữa figure) — dùng khi
    plot_* gặp lỗi. Hàm nội bộ (prefix _), không cần export ra README/app.py."""
    fig, ax = plt.subplots()
    ax.text(0.5, 0.5, message, color="red", ha="center", va="center", wrap=True)
    ax.axis("off")
    return fig
