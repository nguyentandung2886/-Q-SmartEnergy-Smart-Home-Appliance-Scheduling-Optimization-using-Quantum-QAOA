# Q-SmartEnergy — Scaffold & Build Brief (Claude Code)

> Brief dựng repo + skeleton 5 module core. Paste vào Claude Code (agentic) để chạy. Tách riêng khỏi `Q-SmartEnergy_Implementation_Plan.md` (sprint 2 tuần).

---

## Objective

Scaffold toàn bộ cây thư mục repo Q-SmartEnergy và viết skeleton 5 module core theo Implementation Plan đã có, sao cho chạy được end-to-end pipeline (data → QUBO → QAOA → visualize → app) với số liệu khớp `calc.py`.

**WHY:** 4 thành viên cần code song song không đụng nhau, nên cấu trúc + module contract phải dựng trước.

## Context (carry forward — đã chốt, KHÔNG đổi)

- Dự án: Q-SmartEnergy — lập lịch thiết bị điện gia dụng bằng QAOA, thi Coding Inspiration 2026 (Smart Life).
- **Single source of truth:** `calc.py` giữ MỌI số liệu (530 kWh/tháng, solar 5kWp, self-consumption 30%→45%, hóa đơn 896.125đ→658.125đ, giảm 26,6%, 6 bậc giá: 1.800/1.900/2.200/2.700/3.050/3.150 đ/kWh). Module khác PHẢI import từ `calc.py`, KHÔNG hard-code số ở nơi khác.
- **Biểu giá EVN là BẬC THANG (tiered/lũy tiến), KHÔNG phải time-of-use.** TUYỆT ĐỐI không dùng framing "giờ cao điểm" trong code/comment/docstring/biến. Hai trục value: (1) tránh nhảy bậc giá, (2) tối đa self-consumption solar.
- Palette UI: Indigo `#3730A3`, Teal `#0F766E`, Gold `#CA8A04`.
- Stack: Python 3.x, `qiskit` + `qiskit-optimization` + `qiskit-aer`, `numpy`, `pandas`, `matplotlib`, `streamlit`. PoC quy mô 4–5 qubits trên Aer Simulator.

## Target State (done = đúng các điểm sau)

Cây thư mục dựng xong:

```
q-smartenergy/
  calc.py              # single source of truth, đã có giá trị baseline
  data_prep.py
  qubo_builder.py
  quantum_runner.py
  visualizer.py
  app.py               # Streamlit
  tests/test_baseline.py
  requirements.txt
  README.md
```

- 3 class core (OOP): `Appliance` (công suất, thời gian chạy, độ linh hoạt), `TimeSlot` (khung giờ, bậc giá, sản lượng solar dự kiến), `QuantumScheduler` (đóng gói QUBO → QAOA → kết quả).
- Mỗi module có docstring nêu input/output + ý nghĩa kinh tế/vật lý của tham số, type hints PEP 484 đầy đủ.
- Hàm mục tiêu QUBO có comment LaTeX: cost theo bậc giá − reward solar + penalty λ (chỉ chạy 1 lần / không vượt ngưỡng công suất).
- `quantum_runner.py` bọc try/except quanh lệnh gọi simulator + parse kết quả; CÓ sẵn classical brute-force solver làm fallback.
- `tests/test_baseline.py` kiểm tra tổng kWh/tháng = 530 và bill khớp `calc.py`.

## Scope

- Work only in: thư mục `q-smartenergy/` và các file con của nó.
- Do NOT touch: bất kỳ file nào ngoài `q-smartenergy/`, `.env`, lock files, config hệ thống.

## Constraints

- Mỗi module phải map được tới ít nhất 1 tiêu chí rubric — ghi tiêu chí đó vào docstring đầu file (vd: `# Rubric III.3 - chất lượng kỹ thuật`).
- Khi thêm constraint vào QUBO: viết comment giải thích TẠI SAO chọn quadratic penalty và cách chọn λ (nhỏ→vi phạm ràng buộc, lớn→optimizer kẹt).
- Không thêm dependency mới ngoài stack đã liệt kê mà chưa hỏi.
- Chỉ làm đúng phần được yêu cầu. Không thêm feature/abstraction ngoài skeleton + module contract trên.

## Acceptance Criteria

- [ ] `python -c "import calc, data_prep, qubo_builder, quantum_runner, visualizer"` chạy không lỗi import.
- [ ] `pytest tests/` pass (tổng kWh = 530, bill khớp `calc.py`).
- [ ] `grep -ri "giờ cao điểm\|peak hour\|time-of-use" q-smartenergy/` trả về RỖNG.
- [ ] grep mọi số liệu baseline trong các module → đều truy về `calc.py`, không có số hard-code rời.
- [ ] `streamlit run app.py` mở được UI dùng đúng 3 mã màu palette.

## Stop Conditions

Stop và hỏi trước khi:

- Xóa bất kỳ file nào.
- Thêm dependency mới.
- Đụng vào file ngoài Scope.
- Thay đổi giá trị baseline trong `calc.py`.

## Progress

Sau mỗi bước hoàn thành, output: ✅ [đã làm gì] — [file ảnh hưởng].

Think carefully and step-by-step before starting.

## Session Strategy

New session — bắt đầu fresh từ repo trống.
