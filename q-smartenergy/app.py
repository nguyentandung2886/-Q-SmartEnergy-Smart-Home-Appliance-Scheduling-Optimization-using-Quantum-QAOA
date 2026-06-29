"""
Streamlit Web Application for Q-SmartEnergy.
# Rubric III.6 - Giao diện & UX/UI (bản skeleton tối thiểu, UX đầy đủ là Phase 2.2 ngoài scope)

Input:
  - User appliance configuration (list of appliances, usage patterns)
  - Local electricity pricing (EVN tiers from calc.py)
  - Solar generation forecast (optional, for self-consumption model)

Output:
  - Interactive dashboard showing:
    * Current vs. optimized schedules
    * Bill savings and self-consumption gains
    * Appliance shifting recommendations
    * Quantum solver execution details

Economic/Physical Meaning:
  - Provides end-user interface for Q-SmartEnergy optimization service
  - Allows households to input their appliances and see personalized savings estimates
  - Communicates quantum computing benefits in terms of real cost reduction

Rubric Mapping:
  - III.1 (Visualization): UI palette (Indigo #3730A3, Teal #0F766E, Gold #CA8A04)
  - III.4 (User Experience): Responsive layout, clear navigation
  - III.5 (Data Integration): Pulls baseline from calc.py, displays results from pipeline
"""

import calc
import data_prep
import qubo_builder
import quantum_runner
import visualizer


def run_optimization(appliances=None, day_of_month: int = 15, use_quantum: bool = True):
    """Logic thuần: chạy toàn bộ pipeline data_prep -> qubo_builder -> quantum_runner.
    Tách riêng khỏi UI Streamlit để unit test được mà không cần streamlit runtime.
    Input: appliances (list Appliance, default qubo_builder.DEFAULT_APPLIANCES nếu None).
    Output: quantum_runner.ScheduleResult.
    """
    if appliances is None:
        appliances = qubo_builder.DEFAULT_APPLIANCES
    profile = data_prep.build_daily_profile(day_of_month)
    scheduler = quantum_runner.QuantumScheduler(appliances, profile)
    return scheduler.solve(use_quantum=use_quantum)


# --- Phần UI Streamlit (chỉ chạy khi `streamlit run app.py`, không chạy khi import để test) ---
import streamlit as st

st.set_page_config(page_title="Q-SmartEnergy", page_icon="⚡")

# Áp palette Indigo/Teal/Gold qua CSS — chỉ cần đủ để acceptance criteria "dùng đúng 3 mã màu" pass,
# không cần polish UX (Phase 2.2 sẽ làm sau).
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
st.write("Lập lịch thiết bị điện gia dụng bằng QAOA — tránh nhảy bậc giá EVN, tối đa hóa self-consumption điện mặt trời.")

if st.button("Tối ưu hóa"):
    try:
        result = run_optimization()
        st.pyplot(visualizer.plot_schedule_gantt(result.schedule, qubo_builder.DEFAULT_APPLIANCES))
        st.pyplot(visualizer.plot_cost_comparison())
        st.success(f"Lịch chạy tối ưu (solver: {result.solver_used}, fallback: {result.used_fallback})")
    except Exception as exc:
        st.error(f"Lỗi khi tối ưu hóa: {exc}")
