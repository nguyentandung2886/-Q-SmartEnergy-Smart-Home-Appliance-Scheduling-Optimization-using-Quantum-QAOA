# Design: EVN Tariff Rebase (5 bậc + VAT) + Appliance Catalog (10 loại thiết bị)

## Mục tiêu

Hiện tại `calc.py` dùng 6 bậc giá EVN **minh họa** (1.800–3.150đ/kWh, không VAT) và `MONTHLY_KWH = 530` là một con số **khóa cứng** được chọn trước rồi suy ngược ra bill 896.125đ/658.125đ. Thiết kế này thay bằng:

1. **Biểu giá EVN thật, hiện hành** (5 bậc, có VAT) — không còn "minh họa", đối chiếu được trực tiếp với quyết định của Thủ tướng/Bộ Công Thương.
2. **`MONTHLY_KWH` derive từ catalog 10 loại thiết bị thật** (công suất có nguồn tham chiếu) — không ép khớp số nào có trước; chấp nhận hóa đơn cuối có thể khác con số đã dùng trong proposal Vòng Ý tưởng.

Điều này đổi `calc.py` từ "số khóa, validate ngược" sang "số tính trực tiếp từ input thật" — đơn giản hóa code (bỏ luôn cơ chế reconciliation/exception vừa thêm ở plan trước) và tăng độ tin cậy trước câu hỏi giám khảo "số này từ đâu ra".

## 1. Biểu giá EVN — nguồn dữ liệu (đã verify qua WebSearch, có trích dẫn)

**Hiệu lực từ 29/05/2025**, theo QĐ 14/2025/QĐ-TTg (Thủ tướng) và QĐ 1279/QĐ-BCT ngày 09/5/2025 (Bộ Công Thương) — biểu giá điện sinh hoạt rút từ 6 xuống **5 bậc**:

| Bậc | Khoảng kWh | Giá (đ/kWh, CHƯA VAT) |
|---|---|---|
| 1 | 0–100 | 1.984 |
| 2 | 101–200 | 2.380 |
| 3 | 201–400 | 2.998 |
| 4 | 401–700 | 3.571 |
| 5 | ≥701 | 3.967 |

**VAT điện: 8%** (giảm từ 10%, áp dụng 01/07/2025–31/12/2026) — cộng vào giá bán lẻ để ra số tiền thật trên hóa đơn.

Nguồn (đưa vào docstring `calc.py` để judge tự kiểm chứng được):
- Trang chính chủ EVN: "Biểu giá bán lẻ điện (theo Quyết định số 1279/QĐ-BCT ngày 09/5/2025 của Bộ Công Thương)" — evn.com.vn
- Tổng hợp số liệu: luatvietnam.vn, vietnamsolar.vn (đối chiếu khớp nhau giữa nhiều nguồn độc lập)

## 2. `calc.py` — thay đổi cấu trúc

### Trước (hiện tại)
```python
MONTHLY_KWH = 530                       # literal, khóa cứng
EVN_TIERS = [(50,1800),...,(inf,3150)]  # 6 bậc minh họa
BILL_BEFORE_VND = 896125                # literal, khóa cứng
BILL_AFTER_VND = 658125                 # literal, khóa cứng
SAVINGS_PERCENT = 26.6                  # literal
# + _check_reconciliation() đối chiếu calculate_bill() với 2 số trên, raise nếu lệch
```

### Sau (thiết kế mới)
```python
from appliance_catalog import total_monthly_kwh   # nguồn MỚI của MONTHLY_KWH

EVN_TIERS = [(100,1984),(200,2380),(400,2998),(700,3571),(float('inf'),3967)]  # 5 bậc THẬT
VAT_RATE = 0.08

MONTHLY_KWH = total_monthly_kwh()       # derive từ catalog, KHÔNG còn literal

def calculate_bill(kwh, tiers=None):
    ...  # logic lũy tiến giữ nguyên
    return total_bill * (1 + VAT_RATE)  # THÊM bước VAT

BILL_BEFORE_VND = calculate_bill(grid_purchase_kwh(SELF_CONSUMPTION_BEFORE))  # tính trực tiếp
BILL_AFTER_VND = calculate_bill(grid_purchase_kwh(SELF_CONSUMPTION_AFTER))    # tính trực tiếp
SAVINGS_PERCENT = (BILL_BEFORE_VND - BILL_AFTER_VND) / BILL_BEFORE_VND * 100  # tính trực tiếp
```

**Bỏ hoàn toàn** `BaselineReconciliationError` / `_check_reconciliation()` (thêm ở plan trước) — không còn gì để đối chiếu, vì `BILL_BEFORE_VND`/`BILL_AFTER_VND` giờ LÀ kết quả công thức, không phải số chọn trước rồi validate ngược.

**Giữ nguyên, KHÔNG đổi trong thiết kế này** (ngoài phạm vi yêu cầu lần này, vẫn giữ disclosure "minh họa" đã có):
- `SOLAR_CAPACITY_KWP = 5`, `SOLAR_MONTHLY_GENERATION_KWH = 525`
- `SELF_CONSUMPTION_BEFORE = 0.30`, `SELF_CONSUMPTION_AFTER = 0.45`
- `grid_purchase_kwh()` — logic giữ nguyên, chỉ input `MONTHLY_KWH` giờ derive khác đi

## 3. `appliance_catalog.py` (file mới) — 10 loại thiết bị

### Thay đổi `qubo_builder.Appliance` (thêm 1 field, default giữ tương thích ngược)
```python
@dataclass
class Appliance:
    name: str
    power_w: float
    duration_hours: float              # flexible: giờ chạy/lần; KHÔNG flexible: giờ dùng/ngày
    candidate_hours: Tuple[int, ...]    # flexible: >=2 giờ ứng viên; KHÔNG flexible: không dùng, để ()
    is_flexible: bool = True            # MỚI — False = tải cố định, không vào QUBO làm biến quyết định
```
`build_qubo()` **không đổi gì** — vẫn nhận `List[Appliance]` như cũ; caller (sau này) tự lọc `is_flexible=True` trước khi truyền vào.

### Nội dung `appliance_catalog.py`
```python
from qubo_builder import Appliance

# 10 LOẠI thiết bị (không phải 10 instance — điều hòa/bình nước nóng có thể nhiều cái/loại
# qua tham số quantity khi build danh sách, xem _expand() dưới).
# Công suất: trích nguồn datasheet/tiêu chuẩn ngành trong docstring từng entry; số chưa chắc
# đánh [CẦN XÁC MINH] — KHÔNG bịa số.

def total_monthly_kwh(appliances: List[Appliance] = None) -> float:
    """Tổng kWh/tháng = Σ fixed-load (power_w/1000 * duration_hours[giờ/ngày] * 30)
    + Σ flexible-load (power_w/1000 * duration_hours[giờ/lần] * số lần/tháng giả định).
    KHÔNG ép khớp số nào có trước — ra bao nhiêu dùng bấy nhiêu."""

def split_by_flexibility(appliances: List[Appliance]) -> Tuple[List[Appliance], List[Appliance]]:
    """Trả về (flexible_list, fixed_list) — dùng để lọc trước khi gọi qubo_builder.build_qubo."""

HOUSEHOLD_APPLIANCES: List[Appliance] = [
    # 1. Tủ lạnh — is_flexible=False, 24/7
    # 2. Điều hòa (2-3 cái, mỗi cái 1 entry riêng) — is_flexible=False (chạy theo nhu cầu nhiệt độ)
    # 3. Bình nước nóng (2 cái, mỗi cái 1 entry riêng) — is_flexible=True (candidate_hours linh hoạt)
    # 4. Máy giặt — is_flexible=True
    # 5. Quạt điện — is_flexible=False
    # 6. Bếp điện — is_flexible=False
    # 7. Bóng điện (tổng các bóng trong nhà, gộp 1 entry) — is_flexible=False
    # 8. Nồi cơm điện — is_flexible=False (dùng theo bữa, không thực tế để dời giờ)
    # 9. Tivi — is_flexible=False (dùng theo nhu cầu giải trí)
    # 10. Lò vi sóng — is_flexible=False (dùng theo bữa, thời gian ngắn)
]
```

Mỗi entry: công suất (W) + giờ dùng/ngày (fixed) hoặc giờ chạy/lần + candidate_hours (flexible), kèm docstring trích nguồn. Việc tra số liệu thật (datasheet/Energy Star/tiêu chuẩn ngành cho điều hòa BTU→W, tủ lạnh inverter, bình nước nóng, máy giặt...) thực hiện ở bước triển khai (mỗi task tra + trích nguồn cụ thể, đánh `[CẦN XÁC MINH]` nếu không chắc) — spec này chỉ chốt cấu trúc, không tự bịa số cụ thể.

## 4. Dọn tài liệu liên quan ("6 bậc" → "5 bậc", thêm VAT, MONTHLY_KWH không còn cố định)

File cần sửa câu chữ (không đổi logic): `README.md`, docstring `qubo_builder.py`, `data_prep.py`, `app.py` — mọi chỗ nói "6 bậc giá"/đưa ví dụ 1.800–3.150đ cần đổi thành 5 bậc 1.984–3.967đ + ghi chú VAT 8%. Chỗ nào nói "MONTHLY_KWH = 530 (locked)" cần đổi thành "derived từ appliance_catalog, có thể khác 530".

## 5. Ngoài phạm vi (không làm trong spec này)

- Wiring `HOUSEHOLD_APPLIANCES` vào `app.py` UI / Gantt chart / storytelling — đây là **subsystem 2** (storytelling + lịch chỉnh sửa), brainstorm riêng sau khi subsystem này xong.
- Database/auth/backend API (**subsystem 3**) — chưa brainstorm, chưa quyết định must-have/nice-to-have.
- Đổi `SELF_CONSUMPTION_BEFORE/AFTER`, `SOLAR_MONTHLY_GENERATION_KWH` — vẫn giữ nguyên minh họa như hiện tại.

## 6. Rủi ro / lưu ý triển khai

- Đổi `EVN_TIERS` từ 6→5 bậc + VAT sẽ làm `BILL_BEFORE_VND`/`BILL_AFTER_VND`/`SAVINGS_PERCENT` ra số **khác hẳn** 896.125đ/658.125đ/26.6% đã dùng trong proposal Vòng Ý tưởng đã nộp — người dùng đã xác nhận chấp nhận điều này.
- `qubo_builder.py`/`quantum_runner.py`/`visualizer.py`/`tests/test_qubo_builder.py`/`tests/test_quantum_runner.py` **không cần đổi gì** (Appliance chỉ thêm field có default, build_qubo không đổi) — rủi ro regression thấp.
- `tests/test_baseline.py` cần viết lại đáng kể (các test cũ assert đúng 530/896125/658125 sẽ sai) — đây là thay đổi có chủ đích, không phải regression.
