# Q-SmartEnergy — Implementation Plan (Sprint 2 tuần)

**Đội:** Phá Đảo Thế Giới Ảo · **Cuộc thi:** Coding Inspiration 2026 — Smart Life
**Phạm vi:** Từ sau vòng Ý tưởng đến Vòng Chung kết + Vòng Phụ (bonus +25đ)
**Nguồn số liệu duy nhất:** `calc.py` (530 kWh/tháng, 5kWp solar, self-consumption 30%→45%, hóa đơn 896.125đ→658.125đ, giảm 26,6%, 6 bậc giá: 1.800/1.900/2.200/2.700/3.050/3.150 đ/kWh)

---

## 0. Nguyên tắc gatekeeping (áp dụng cho mọi phase dưới đây)

Trước khi merge bất kỳ module/slide/đoạn văn nào, Dũng (technical lead) trả lời 3 câu hỏi:

1. Phần này lấy điểm ở tiêu chí nào trong rubric Chung kết (mục III) hoặc rubric Phụ (mục II)?
2. Số liệu nào dùng — đã trace được về `calc.py` chưa, hay là số bịa tạm?
3. Có dùng đúng framing "biểu giá bậc thang/lũy tiến" không, hay đang lỡ viết "giờ cao điểm"?

Bất kỳ PR/slide nào không trả lời được câu 1 → loại khỏi sprint, đẩy vào "Mục tiêu tương lai".

---

## 1. Kiến trúc & Module Contract (chốt trước khi code song song)

```
data_prep.py        → load EVN tiers, profile phụ tải, sản lượng solar theo giờ
qubo_builder.py      → build Q matrix: cost term + solar reward term + penalty constraints
quantum_runner.py    → QAOA via Qiskit Aer, trả về bitstring tối ưu + energy
visualizer.py        → Gantt chart lịch thiết bị + bar chart chi phí trước/sau
app.py (Streamlit)   → orchestrate 4 module trên, UI theo palette Indigo/Teal/Gold
```

**Contract giữa các module** (chốt ngay đầu Tuần 1 để 4 người code song song không đụng nhau):

| Module | Input | Output | Owner |
| :-- | :-- | :-- | :-- |
| `data_prep.py` | config hộ gia đình (kWh/tháng, kWp, số thiết bị) | `DataFrame` 24 slot/ngày: bậc giá, sản lượng solar dự kiến (kWh) | Minh |
| `qubo_builder.py` | output của `data_prep` + list `Appliance` | ma trận Q (numpy) + dict ánh xạ biến x_i → (thiết bị, slot) | Sơn |
| `quantum_runner.py` | ma trận Q | bitstring nghiệm + lịch chạy thiết bị (JSON) | Sơn + Dũng (pair) |
| `visualizer.py` | lịch chạy + baseline `calc.py` | Gantt chart, bar chart so sánh chi phí | Minh |
| `app.py` | gọi 4 module trên | Web demo | Hiệp |

Class bắt buộc (OOP, rubric III.1): `Appliance`, `TimeSlot`, `QuantumScheduler`. Type hint đầy đủ, docstring nêu ý nghĩa kinh tế/vật lý của tham số, try/except quanh lệnh gọi simulator.

---

## 2. TUẦN 1 — Core Engine (Data → QUBO → QAOA → Visualizer)

### Phase 1.1 — Data Prep & baseline lock (Ngày 1–2)
- **Việc làm:** Viết `data_prep.py`, hard-code 6 bậc giá EVN, sinh profile solar 5kWp theo giờ (đường cong hình chuông, peak ~12h), đối chiếu lại với `calc.py` để baseline không lệch.
- **Owner:** Minh (Data Analysis), review bởi Dũng.
- **Rubric mapping:** III.5 (dùng data generator dựa trên biểu giá EVN thật) + III.2 (ánh xạ đúng ràng buộc đời thực).
- **Output nghiệm thu:** DataFrame export CSV, unit test kiểm tra tổng kWh/tháng = 530.

### Phase 1.2 — QUBO Formulation (Ngày 2–4)
- **Việc làm:** Viết hàm mục tiêu LaTeX trước, sau đó code `qubo_builder.py`. Hai trục: (a) chi phí điện theo bậc giá lũy tiến, (b) thưởng self-consumption solar. Penalty term cho ràng buộc "chỉ chạy 1 lần/thiết bị" và "không vượt ngưỡng công suất".
- **Owner:** Sơn (Algorithm lead), pair với Dũng cho phần penalty λ tuning.
- **Rubric mapping:** III.2 (QUBO ánh xạ ràng buộc thực tế) + III.3 (chất lượng kỹ thuật, hiểu rõ tuning hyperparameter) + nền cho bonus +25đ (II — yếu tố solar trong cost function).
- **Lưu ý:** Mỗi constraint mới phải có đoạn giải thích tại sao chọn quadratic penalty và cách chọn λ (quá nhỏ → vi phạm ràng buộc, quá lớn → optimizer kẹt ở nghiệm an toàn nhưng tệ).

### Phase 1.3 — Quantum Runner (Ngày 4–6)
- **Việc làm:** `quantum_runner.py` chạy QAOA trên Qiskit Aer, 4–5 qubits. Đo execution time thực tế trên laptop thường, ghi log để dùng cho slide tính khả thi.
- **Owner:** Sơn + Dũng (pair-coding, vì đây là phần "critical QUBO/QAOA component").
- **Rubric mapping:** III.3 (thành thạo Qiskit-Optimization) + tự thừa nhận trade-off tốc độ (tránh bị trừ điểm khả thi nếu chạy quá lâu).
- **Fallback bắt buộc:** nếu QAOA không converge ổn định trong demo → có sẵn classical brute-force solver làm fallback hiển thị, Dũng là người quyết định dùng fallback nào khi live demo.

### Phase 1.4 — Visualizer & Error Handling (Ngày 6–7)
- **Việc làm:** Gantt chart lịch thiết bị (matplotlib), bar chart "có Q-SmartEnergy vs không có" bằng đúng số `calc.py` (658.125đ vs 896.125đ). Bọc try/except quanh toàn bộ pipeline để không crash giữa demo.
- **Owner:** Minh, review Hiệp (vì sẽ nhúng vào app).
- **Rubric mapping:** III.1 (try/catch, không crash) + III.5 (kết quả triển khai thực tế, biểu đồ VNĐ rõ ràng).
- **Checkpoint cuối Tuần 1:** chạy full pipeline end-to-end 1 lần, output đúng số liệu baseline, không lỗi.

---

## 3. TUẦN 2 — Demo, UX & Pitch (+ Bonus Tier)

### Phase 2.1 — Bonus Tier: Solar Integration (Ngày 8–9, làm SỚM vì ROI cao nhất)
- **Việc làm:** Đưa yếu tố điện mặt trời mái nhà vào hàm mục tiêu (đã có nền từ Phase 1.2) — hoàn thiện thành kiến trúc Hybrid Quantum-Classical rõ ràng: phần classical xử lý dự báo sản lượng solar theo giờ, phần quantum tối ưu lịch.
- **Owner:** Sơn, Dũng quyết định kiến trúc cuối.
- **Rubric mapping:** Vòng Phụ — Mức Khó (+25đ): "đưa thêm yếu tố năng lượng tái tạo vào hàm mục tiêu". Lý do ưu tiên path này: baseline solar đã có sẵn trong `calc.py`, effort thấp, tác động điểm cao và lan sang nhiều tiêu chí khác (III.2, III.3, III.5) cùng lúc.
- **Lưu ý quan trọng:** Không build thêm "cảnh báo vượt ngưỡng công suất" (mức Dễ +8) hoặc "ML forecasting máy giặt" (mức Trung bình +15) làm path chính — chỉ làm nếu còn dư thời gian sau khi path Khó đã chắc chân, vì 2 path đó tốn effort riêng mà không tận dụng được baseline có sẵn.

### Phase 2.2 — Streamlit/Gradio App, UI theo Visual Identity (Ngày 9–11)
- **Việc làm:** `app.py` ghép 4 module Tuần 1, áp màu Indigo #3730A3 / Teal #0F766E / Gold #CA8A04 nhất quán với slide proposal. Layout: input hộ gia đình → nút "Tối ưu hóa" → Gantt chart + bar chart so sánh + số tiền tiết kiệm nổi bật.
- **Owner:** Hiệp (Web/App), review UX bởi Hiếu (góc nhìn người thuyết trình/giám khảo).
- **Rubric mapping:** III.6 (Giao diện & UX/UI, 10đ) — "đẹp mắt" là tiêu chí chấm trực tiếp.

### Phase 2.3 — Pitching Script & Storytelling (Ngày 11–13)
- **Việc làm:** Hiếu chủ trì viết kịch bản thuyết trình, Dũng/Sơn hỗ trợ "dịch" kiến thức lượng tử hàn lâm (QUBO, QAOA, Hamiltonian) thành câu chuyện đơn giản: "máy tính lượng tử thử nhiều phương án lịch chạy đồng thời, chọn ra phương án tiết kiệm điện nhất". Tránh mọi câu nói gợi "giờ cao điểm" — luôn dùng "tránh nhảy bậc giá" + "tối đa hóa dùng điện mặt trời".
- **Owner:** Hiếu, review Dũng (đảm bảo không sai chính sách giá điện).
- **Rubric mapping:** III.4 (Trình bày & thuyết phục, 15đ).

### Phase 2.4 — Dry-run, Stress Test & Fallback Plan (Ngày 13–14)
- **Việc làm:** Chạy demo end-to-end tối thiểu 5 lần với input khác nhau, đo execution time QAOA thực tế để chủ động trả lời câu hỏi giám khảo về tốc độ. Chuẩn bị sẵn 1 bản kết quả đã chạy trước (cached) làm fallback nếu live demo lỗi mạng/môi trường.
- **Owner:** Toàn team, Dũng là người quyết định cuối cùng dùng live hay fallback khi lên sân khấu.
- **Rubric mapping:** III.1 (mức độ hoàn thiện, không crash) + bảo vệ điểm số trước rủi ro "execution time quá lâu bị trừ điểm khả thi" nêu ở luật IV.3 của khung tiêu chí.

---

## 4. Bảng theo dõi tiến độ (cập nhật thủ công mỗi ngày)

| Phase | Ngày | Owner | Trạng thái | Rubric target |
| :-- | :-- | :-- | :-- | :-- |
| 1.1 Data Prep | 1–2 | Minh | ☐ | III.5, III.2 |
| 1.2 QUBO Builder | 2–4 | Sơn + Dũng | ☐ | III.2, III.3, Bonus |
| 1.3 Quantum Runner | 4–6 | Sơn + Dũng | ☐ | III.3 |
| 1.4 Visualizer | 6–7 | Minh + Hiệp | ☐ | III.1, III.5 |
| 2.1 Solar Bonus | 8–9 | Sơn + Dũng | ☐ | Bonus +25 |
| 2.2 Streamlit App | 9–11 | Hiệp + Hiếu | ☐ | III.6 |
| 2.3 Pitching Script | 11–13 | Hiếu + Dũng | ☐ | III.4 |
| 2.4 Dry-run & Fallback | 13–14 | Cả team | ☐ | III.1 |

---

## 5. Rủi ro & Phương án dự phòng

- **QAOA không converge ổn định ở 4–5 qubit:** chuẩn bị classical solver (brute-force/greedy) chạy song song, dùng làm fallback hiển thị nếu kết quả quantum bất thường khi demo.
- **Lệch số liệu giữa slide/app/proposal:** mọi module import trực tiếp từ `calc.py`, không hard-code số ở nơi khác — review cuối mỗi phase phải grep lại các số liệu trong code/slide đối chiếu `calc.py`.
- **Lỡ dùng framing "giờ cao điểm":** thêm bước review ngôn ngữ (đặc biệt ở Phase 2.3 — pitching script) trước khi chốt, vì đây là lỗi chính sách dễ tái phát khi thành viên không nhớ EVN dùng biểu giá bậc thang.
- **Hết thời gian cho bonus tier:** Phase 2.1 được đặt sớm nhất trong Tuần 2 (Ngày 8–9) chính vì lý do này — nếu trễ tiến độ Tuần 1, ưu tiên cắt bớt Phase 2.2 (UI polish) trước, không cắt Phase 2.1.

---

## 6. Mục tiêu tương lai (sau sprint, nếu vào chung kết và còn thời gian)

- Mức Dễ (+8đ — cảnh báo vượt ngưỡng công suất) và Mức Trung bình (+15đ — ML forecasting thời gian máy giặt) chỉ làm thêm nếu Phase 2.1 đã ổn định và còn dư thời gian, không phải mục tiêu chính của sprint này.
