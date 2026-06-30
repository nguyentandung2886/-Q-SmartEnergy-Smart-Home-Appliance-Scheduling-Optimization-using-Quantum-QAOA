"""
Household Appliance Catalog for Q-SmartEnergy — 10 loại thiết bị điện gia dụng phổ biến
ở Việt Nam, công suất có nguồn tham chiếu (datasheet/trang nhà sản xuất/đại lý uy tín).
KHÔNG ép tổng khớp con số nào có trước — tổng kWh/tháng tính ra bao nhiêu thì dùng đúng
con số đó (xem total_monthly_kwh()), kể cả khi khác với số liệu minh họa trong proposal cũ.

Input: không có (module-level catalog cố định).
Output:
  - HOUSEHOLD_APPLIANCES: List[Appliance] — danh sách đầy đủ.
  - total_monthly_kwh(): tổng kWh/tháng — calc.py dùng giá trị này làm MONTHLY_KWH.
  - split_by_flexibility(): tách (flexible, fixed) để caller chỉ truyền phần flexible vào
    qubo_builder.build_qubo() (phần fixed không phải biến quyết định QUBO).

Quy ước tính kWh/tháng cho MỖI appliance (áp dụng đều cho is_flexible=True/False):
  monthly_kwh = power_w / 1000 * duration_hours * 30
  - is_flexible=False: duration_hours = giờ DÙNG MỖI NGÀY (vd tủ lạnh=24, quạt=5).
  - is_flexible=True: duration_hours = giờ CHẠY MỖI LẦN, giả định 1 lần/ngày (khớp đúng
    cách qubo_builder's one-hot chọn đúng 1 giờ/ngày cho thiết bị này).

Rubric Mapping:
  # Rubric III.5 - data generator dựa trên số liệu thiết bị thật, có nguồn
  # Rubric III.2 - ánh xạ đúng ràng buộc đời thực (tải cố định vs linh hoạt)
"""

import math
from typing import Dict, List, Tuple

from qubo_builder import Appliance

HOUSEHOLD_APPLIANCES: List[Appliance] = [
    # 1. Tủ lạnh — Panasonic Inverter NR-BL267PSVN (234L), công bố hiệu suất chính thức
    #    Panasonic VN: 296 kWh/năm ≈ 0.81 kWh/ngày ≈ 33.75W liên tục (24/7).
    #    Nguồn: panasonic.com/vn (công bố hiệu suất tiêu thụ điện năng tủ lạnh).
    Appliance(name="Tủ lạnh", power_w=33.75, duration_hours=24, candidate_hours=(), is_flexible=False),

    # 2. Điều hòa phòng ngủ, 12000 BTU — Daikin FTKC35TVMV (1.5HP, Inverter), 960W rated.
    #    Giờ dùng/ngày: 6h (theo khoảng 6-8h/ngày mùa nóng, thông lệ ngành) [CẦN XÁC MINH giờ].
    #    Nguồn công suất: datasheet Daikin FTKC35TVMV (đại lý dienlanhdaicoviet.com).
    Appliance(name="Điều hòa phòng ngủ (12000 BTU)", power_w=960, duration_hours=6, candidate_hours=(), is_flexible=False),

    # 3. Điều hòa phòng khách, 18000 BTU — Daikin FTKC50 (2HP, Inverter), 1670W rated (full load).
    #    Giờ dùng/ngày: 6h [CẦN XÁC MINH giờ]. Nguồn công suất: datasheet Daikin FTKC50UV16V
    #    (đại lý betterhomeapp.com).
    Appliance(name="Điều hòa phòng khách (18000 BTU)", power_w=1670, duration_hours=6, candidate_hours=(), is_flexible=False),

    # 4. Bình nước nóng gián tiếp (storage, vd Ariston/Ferroli) — 2500W.
    #    FLEXIBLE: có thể hẹn giờ làm nóng nước trước khi dùng. candidate_hours minh họa:
    #    6h (sáng sớm) hoặc 21h (tối). Giờ dùng/lần: 0.5h [CẦN XÁC MINH thời gian].
    #    Nguồn công suất: FPT Shop (so sánh máy nước nóng gián tiếp Ariston/Ferroli).
    Appliance(name="Bình nước nóng gián tiếp", power_w=2500, duration_hours=0.5, candidate_hours=(6, 21), is_flexible=True),

    # 5. Bình nước nóng trực tiếp (instant, vd Ariston/Ferroli) — 3500W (khoảng 2500-4500W).
    #    FLEXIBLE: candidate_hours minh họa 7h hoặc 20h. Giờ dùng/lần: 0.5h [CẦN XÁC MINH thời gian].
    #    Nguồn công suất: FPT Shop (so sánh máy nước nóng trực tiếp Ariston/Ferroli).
    Appliance(name="Bình nước nóng trực tiếp", power_w=3500, duration_hours=0.5, candidate_hours=(7, 20), is_flexible=True),

    # 6. Máy giặt — 500W (loại cửa trên, phổ biến). FLEXIBLE: candidate_hours minh họa 9h/14h.
    #    Giờ dùng/lần: 1h. Nguồn: Meta.vn, Điện máy HTech (công suất máy giặt).
    Appliance(name="Máy giặt", power_w=500, duration_hours=1, candidate_hours=(9, 14), is_flexible=True),

    # 7. Quạt điện (quạt cây/để bàn) — 60W. Giờ dùng/ngày: 5h [CẦN XÁC MINH giờ].
    #    Nguồn công suất: FPT Shop, Livotec (công suất quạt điện).
    Appliance(name="Quạt điện", power_w=60, duration_hours=5, candidate_hours=(), is_flexible=False),

    # 8. Bếp điện (bếp từ 1 bếp) — 2000W. Giờ dùng/ngày: 1h [CẦN XÁC MINH giờ].
    #    Nguồn công suất: Sunhouse VN (bếp điện bao nhiêu W).
    Appliance(name="Bếp điện", power_w=2000, duration_hours=1, candidate_hours=(), is_flexible=False),

    # 9. Bóng điện (gộp ~6 bóng LED trong nhà, ~10W/bóng) — 60W tổng. Giờ dùng/ngày: 5h
    #    (theo ví dụ minh họa cách tính tiền điện của Home Credit) [CẦN XÁC MINH số bóng+giờ].
    #    Nguồn công suất/bóng: Haledco (công suất bóng đèn LED).
    Appliance(name="Bóng điện", power_w=60, duration_hours=5, candidate_hours=(), is_flexible=False),

    # 10. Nồi cơm điện — Toshiba RC-18NTFV(W), 800W. Giờ dùng/ngày: 1h (nấu + giữ ấm)
    #     [CẦN XÁC MINH tần suất]. Nguồn công suất: Pico.vn (nồi cơm điện Toshiba RC-18NTFV).
    Appliance(name="Nồi cơm điện", power_w=800, duration_hours=1, candidate_hours=(), is_flexible=False),

    # 11. Tivi (LED 43 inch) — 100W (khoảng 65-140W tùy độ sáng/HDR). Giờ dùng/ngày: 4h
    #     [CẦN XÁC MINH giờ]. Nguồn công suất: manhnguyen.com.vn (công suất tivi Samsung).
    Appliance(name="Tivi", power_w=100, duration_hours=4, candidate_hours=(), is_flexible=False),

    # 12. Lò vi sóng — 850W (khoảng 800-900W). Giờ dùng/ngày: 0.25h (15 phút).
    #     Nguồn công suất: FPT Shop (so sánh lò vi sóng Sharp/Panasonic).
    Appliance(name="Lò vi sóng", power_w=850, duration_hours=0.25, candidate_hours=(), is_flexible=False),
]


def total_monthly_kwh(appliances: List[Appliance] = None) -> float:
    """Tổng kWh/tháng = Σ (power_w/1000 * duration_hours * 30) cho mọi appliance trong list.
    Default dùng HOUSEHOLD_APPLIANCES nếu không truyền list khác.
    KHÔNG ép khớp số nào có trước — gọi hàm này với HOUSEHOLD_APPLIANCES cho ra số thật."""
    if appliances is None:
        appliances = HOUSEHOLD_APPLIANCES
    return sum(a.power_w / 1000.0 * a.duration_hours * 30.0 for a in appliances)


def split_by_flexibility(appliances: List[Appliance]) -> Tuple[List[Appliance], List[Appliance]]:
    """Trả về (flexible_list, fixed_list). flexible_list (is_flexible=True) dùng để truyền
    vào qubo_builder.build_qubo() — fixed_list KHÔNG vào QUBO, chỉ đóng góp kWh cố định."""
    flexible = [a for a in appliances if a.is_flexible]
    fixed = [a for a in appliances if not a.is_flexible]
    return flexible, fixed


# Khung giờ sử dụng ĐIỂN HÌNH cho thiết bị cố định — chỉ để VẼ một ngày sinh hoạt thực tế
# trên Gantt. Mỗi thiết bị có thể chạy NHIỀU khung giờ rời nhau trong ngày (vd quạt: trưa +
# tối), không nhất thiết là một khối liên tục. Mỗi khung là (giờ_bắt_đầu, số_giờ); tổng số giờ
# xấp xỉ duration_hours/ngày. Thiết bị cố định KHÔNG phải biến quyết định QUBO (không thể dời
# giờ nấu ăn, xem tivi...) — đây là nếp dùng điện điển hình, không phải kết quả tối ưu hóa.
DEFAULT_USAGE_WINDOWS: Dict[str, List[Tuple[int, int]]] = {
    "Tủ lạnh": [(0, 24)],                                  # chạy 24/7
    "Điều hòa phòng ngủ (12000 BTU)": [(0, 4), (22, 2)],   # rạng sáng + trước khi ngủ
    "Điều hòa phòng khách (18000 BTU)": [(12, 3), (19, 3)],# trưa + tối
    "Quạt điện": [(12, 2), (20, 3)],                       # trưa nóng + buổi tối
    "Bếp điện": [(18, 1)],                                 # nấu bữa tối
    "Bóng điện": [(5, 1), (18, 4)],                        # sáng sớm + tối
    "Nồi cơm điện": [(17, 1)],                             # nấu cơm chiều
    "Tivi": [(12, 1), (19, 3)],                            # bản tin trưa + khung giờ vàng
    "Lò vi sóng": [(12, 1)],                               # hâm đồ ăn trưa
}

_DEFAULT_START_FALLBACK = 18  # thiết bị cố định lạ → mặc định buổi tối


def usage_windows(appliance: Appliance) -> List[Tuple[int, int]]:
    """Danh sách khung giờ (giờ_bắt_đầu, số_giờ) để hiển thị 1 thiết bị cố định trên lịch ngày.
    Mỗi khung được clamp để không vượt quá 24h (Gantt 24 cột). Thiết bị lạ → 1 khung buổi tối."""
    windows = DEFAULT_USAGE_WINDOWS.get(appliance.name)
    if windows is None:
        span = min(24, max(1, math.ceil(appliance.duration_hours)))
        start = min(_DEFAULT_START_FALLBACK, 24 - span)
        windows = [(max(0, start), span)]
    clamped: List[Tuple[int, int]] = []
    for start, length in windows:
        start = max(0, min(23, start))
        length = max(1, min(24 - start, length))
        clamped.append((start, length))
    return clamped
