"""
Biểu giá điện EVN cho khách hàng DOANH NGHIỆP — số liệu THẬT theo cấp điện áp + khung giờ.

KHÔNG đụng tới biểu giá hộ gia đình (core/calc.py — EVN_TIERS đã kiểm chứng và khóa). Đây là
module riêng cho khách hàng doanh nghiệp.

Nguồn số liệu (tra cứu 07/2026):
- Giá SẢN XUẤT: Phụ lục QĐ 14/2025/QĐ-TTg + QĐ 1279/QĐ-BCT (vietnamsolar.vn/gia-dien-san-xuat/).
- Giá KINH DOANH: Nhóm 3.3 "Hộ kinh doanh khác" — nhà hàng, café, gym, showroom... — cùng nguồn
  quyết định (vietnamsolar.vn/gia-dien-kinh-doanh/). "commercial" trong app map với nhóm 3.3,
  KHÔNG phải nhóm 3.1 (khách sạn/lưu trú du lịch, rẻ hơn 35-58%, ngoài phạm vi app).
- Khung giờ cao/thấp điểm: QĐ 963/QĐ-BCT, hiệu lực 22/04/2026 (luatvietnam.vn).
- VAT 8% đến 31/12/2026 (Nghị định 174/2025/NĐ-CP, Nghị quyết 204/2025/QH15) — dùng chung
  VAT_RATE với biểu giá hộ gia đình (core/calc.py).
Giá đ/kWh, CHƯA gồm VAT — calculate_business_bill() cộng VAT_RATE ở bước cuối.
"""
from typing import Dict

from core.calc import VAT_RATE

# {business_type: {voltage_level: {khung giờ: đ/kWh (chưa VAT)}}}.
# Sản xuất có 4 cấp điện áp; kinh doanh (nhóm 3.3) chỉ có 3 — KHÔNG có cấp >=110kV.
EVN_BUSINESS_TIERS: Dict[str, Dict[str, Dict[str, float]]] = {
    "production": {
        "tren_110kv":    {"binh_thuong": 1811, "thap_diem": 1146, "cao_diem": 3266},  # >= 110 kV
        "22_den_110kv":  {"binh_thuong": 1833, "thap_diem": 1190, "cao_diem": 3398},  # 22 - <110 kV
        "6_den_22kv":    {"binh_thuong": 1899, "thap_diem": 1234, "cao_diem": 3508},  # 6 - <22 kV
        "duoi_6kv":      {"binh_thuong": 1987, "thap_diem": 1300, "cao_diem": 3640},  # < 6 kV
    },
    "commercial": {
        "22_den_110kv":  {"binh_thuong": 2887, "thap_diem": 1609, "cao_diem": 5025},  # >= 22 kV
        "6_den_22kv":    {"binh_thuong": 3108, "thap_diem": 1829, "cao_diem": 5202},  # 6 - <22 kV
        "duoi_6kv":      {"binh_thuong": 3152, "thap_diem": 1918, "cao_diem": 5422},  # < 6 kV
    },
}


def classify_hour_tou(hour: int) -> str:
    """Phân loại giờ nguyên 0-23 vào khung giờ TOU theo QĐ 963/QĐ-BCT.

    Khung giờ gốc: cao điểm 17h30-22h30 (T2-T7), thấp điểm 00h00-06h00 (mọi ngày),
    bình thường phần còn lại. App chỉ có độ phân giải THEO GIỜ và không gắn thứ trong
    tuần, nên đã chốt hai quy ước:
    - Mọi ngày coi là ngày thường T2-T7 (bỏ qua Chủ nhật không có cao điểm).
    - Làm tròn ranh giới lửng theo đa số phút của giờ đó: giờ 17 (17:00-18:00, đa số
      phút TRƯỚC 17h30) = bình thường; giờ 22 (22:00-23:00, đa số phút TRƯỚC 22h30)
      = cao điểm.

    Kết quả: 0-5 -> "thap_diem"; 18-22 -> "cao_diem"; còn lại -> "binh_thuong".
    """
    if 0 <= hour <= 5:
        return "thap_diem"
    if 18 <= hour <= 22:
        return "cao_diem"
    return "binh_thuong"


def calculate_business_bill(kwh_by_period: dict, business_type: str, voltage_level: str) -> float:
    """Tính tiền điện doanh nghiệp (đ, ĐÃ gồm VAT 8%) từ kWh theo từng khung giờ.

    Args:
        kwh_by_period: {khung giờ ("binh_thuong"/"thap_diem"/"cao_diem"): kWh tiêu thụ}.
        business_type: "production" hoặc "commercial".
        voltage_level: cấp điện áp đấu nối, key trong EVN_BUSINESS_TIERS[business_type]
            (kinh doanh không có "tren_110kv").

    Raises:
        ValueError: business_type hoặc voltage_level không có trong EVN_BUSINESS_TIERS.
    """
    if business_type not in EVN_BUSINESS_TIERS:
        raise ValueError(
            f"business_type {business_type!r} không hợp lệ (phải là một trong "
            f"{list(EVN_BUSINESS_TIERS)})"
        )
    levels = EVN_BUSINESS_TIERS[business_type]
    if voltage_level not in levels:
        raise ValueError(
            f"voltage_level {voltage_level!r} không hợp lệ cho {business_type!r} "
            f"(phải là một trong {list(levels)})"
        )
    prices = levels[voltage_level]
    total = sum(kwh * prices[period] for period, kwh in kwh_by_period.items())
    return total * (1 + VAT_RATE)
