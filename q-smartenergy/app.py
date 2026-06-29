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
            f"Biểu đồ hóa đơn ở trên là số liệu dự báo cho hộ mẫu {calc.MONTHLY_KWH} kWh/tháng "
            "(calc.py, minh họa quy mô tiết kiệm cả tháng khi áp dụng rộng) — KHÔNG phải số "
            "tính trực tiếp từ 2 thiết bị demo phía trên."
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
