# ML Duration Forecasting — Thiết kế (Vòng Phụ Mức Trung Bình, +15đ)

**Ngày:** 2026-06-30
**Mục tiêu:** Module ML cổ điển dự báo *thời gian chạy* của các thiết bị linh hoạt từ đặc trưng
công việc thực tế, rồi đưa duration dự báo vào QAOA — đúng yêu cầu Mức Trung Bình của rubric
("Viết một module nhỏ dự báo (Forecasting) bằng ML cổ điển để đoán thời gian hoàn thành công việc
của máy giặt, sau đó đưa vào QAOA").

## Vì sao điều này feed thật vào QAOA
`duration_hours` quyết định `energy_kwh = power_w/1000 * duration_hours` của thiết bị. Năng lượng
này nằm trong cả hai trục mục tiêu QUBO (`H_cost = E·P`, `H_solar = -min(E,S)·P`) và quyết định
độ dài block trên Gantt + tín dụng solar hiển thị trên hóa đơn. Thay duration cố định bằng duration
*dự báo từ ML* nghĩa là lớp classical (ML) thực sự cấp dữ liệu cho lớp quantum (QAOA) qua một giao
diện sạch — đúng tinh thần Hybrid Quantum-Classical.

## Quyết định đã chốt
- **Thư viện:** numpy thuần (không thêm dependency). Tự cài `LinearRegression` bằng least-squares
  (`np.linalg.lstsq`), có train/test split + báo MAE — thể hiện hiểu thuật toán từ gốc.
- **Phạm vi:** cả 3 thiết bị linh hoạt (Máy giặt, Bình nước nóng gián tiếp, Bình nước nóng trực tiếp),
  mỗi thiết bị một model nhỏ riêng.
- **Hiện diện:** backend (`/forecast` + override duration trong `/optimize`) **và** input trên UI
  Dashboard để giám khảo thấy ML hoạt động trực tiếp.

## Kiến trúc

### `q-smartenergy/forecaster.py` (lớp classical, cùng tầng với weather_model.py)
- `class LinearRegression`: `.fit(X, y)` (normal equations qua lstsq, có intercept), `.predict(X)`,
  thuộc tính `coef_`, `intercept_`. Type hint đầy đủ.
- `mean_absolute_error(y_true, y_pred) -> float`.
- `generate_training_data(appliance_name, n, seed)`: sinh dataset vật lý hợp lý + nhiễu Gaussian.
  - Máy giặt: features `[load_kg ∈ 1..9, program ∈ {quick:0, normal:1, heavy:2}]`,
    `duration = 0.6 + 0.13·load_kg + 0.35·program + noise`.
  - Bình nước nóng gián tiếp (storage 2500W): feature `[people ∈ 1..6]`,
    `duration = 0.25 + 0.12·people + noise`.
  - Bình nước nóng trực tiếp (instant 3500W): feature `[people ∈ 1..6]`,
    `duration = 0.15 + 0.09·people + noise`.
- `class JobDurationForecaster`: với mỗi tên thiết bị, sinh data → split 80/20 → fit → lưu `test_mae`.
  `.predict(features: dict) -> float` (clamp ≥ 0.25h). Train 1 lần ở module-level (seed cố định).
- `FORECAST_SCHEMA: dict[str, list[str]]` — đặc trưng mỗi thiết bị cần (để UI/route biết hỏi gì).
- `PROGRAM_LEVELS = {"quick":0, "normal":1, "heavy":2}`.

### Backend
- `server/forecast_router.py`: `POST /forecast` nhận `{jobs: {name: {feature: value}}}`,
  trả `{name: {predicted_hours, test_mae}}`. Bọc lỗi → không crash.
- `optimize_router.py`: `OptimizeRequest` thêm `duration_overrides: Optional[Dict[str, float]]`.
  Nếu có, override `duration_hours` của thiết bị tương ứng trước khi build QUBO (ảnh hưởng năng lượng,
  Gantt, và tín dụng solar trên bill — nhất quán end-to-end).

### UI (`client/src/pages/Dashboard.jsx`)
- Card "🔮 Dự báo thời gian chạy (ML)": input khối lượng đồ (kg) + chọn chương trình cho Máy giặt,
  input số người cho 2 bình nóng. Nút "Dự báo" gọi `/forecast`, hiện "⏱ <thiết bị>: X.Xh
  (MAE mô hình: Y.YYh)". Duration dự báo được dùng làm `duration_overrides` khi bấm Tối ưu.
- Dùng đúng palette Indigo/Teal/Gold. Không thêm npm dependency.

## Tiêu chí rubric
- Vòng Phụ Mức Trung Bình (+15đ): ML forecasting feed vào QAOA.
- III.3 chất lượng kỹ thuật (train/test split, MAE, model tự cài).
- III.4 UX (input thật, hiển thị dự báo trực quan).

## Test
- `q-smartenergy/tests/test_forecaster.py`: LinearRegression khôi phục đúng hệ số tuyến tính;
  MAE test dưới ngưỡng; predict đơn điệu tăng theo load_kg/people; clamp ≥ 0.25.
- `server/tests/test_forecast.py`: `/forecast` trả dự báo hợp lệ; `/optimize` với `duration_overrides`
  cho năng lượng/bill khác baseline.

## Ràng buộc tuân thủ
- Không "giờ cao điểm"/"peak hour"/"time-of-use" ở bất kỳ đâu.
- Không thêm dependency (numpy/pandas đã có; không npm mới).
- Không sửa baseline trong calc.py. Không xóa file.
