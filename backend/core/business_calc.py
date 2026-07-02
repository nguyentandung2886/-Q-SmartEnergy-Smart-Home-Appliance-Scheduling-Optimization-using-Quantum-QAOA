"""
Biểu giá điện EVN cho khách hàng DOANH NGHIỆP — KHUNG CẤU HÌNH, chưa có số liệu thật.

KHÔNG đụng tới biểu giá hộ gia đình (core/calc.py — EVN_TIERS đã kiểm chứng và khóa). Đây là
module riêng cho khách hàng doanh nghiệp. Hiện CHƯA có bảng giá EVN doanh nghiệp chính thức nên
mọi mức giá để None; calculate_business_bill() cố tình TỪ CHỐI tính (raise NotImplementedError)
thay vì trả ra một con số sai.
"""
from typing import Dict, Optional

# TODO(user): điền bảng giá EVN thật cho DN (theo cấp điện áp + khung giờ cao/thấp điểm/bình thường).
# Giá trị hiện tại là PLACEHOLDER, CHƯA phải số liệu chính thức.
EVN_BUSINESS_TIERS: Dict[str, Dict[str, Optional[float]]] = {
    "production": {"binh_thuong": None, "thap_diem": None, "cao_diem": None},
    "commercial": {"binh_thuong": None, "thap_diem": None, "cao_diem": None},
}


def calculate_business_bill(kwh_by_period: dict, business_type: str) -> float:
    """Tính tiền điện doanh nghiệp từ kWh theo từng khung giờ.

    Args:
        kwh_by_period: {khung giờ ("binh_thuong"/"thap_diem"/"cao_diem"): kWh tiêu thụ}.
        business_type: "production" hoặc "commercial".

    Raises:
        ValueError: business_type không thuộc EVN_BUSINESS_TIERS.
        NotImplementedError: bảng giá của business_type còn None (chưa cấu hình) — CỐ TÌNH
            không tính ra số để tránh trả về hóa đơn sai khi chưa có số liệu EVN thật.
    """
    if business_type not in EVN_BUSINESS_TIERS:
        raise ValueError(
            f"business_type {business_type!r} không hợp lệ (phải là một trong "
            f"{list(EVN_BUSINESS_TIERS)})"
        )
    tiers = EVN_BUSINESS_TIERS[business_type]
    if any(price is None for price in tiers.values()):
        raise NotImplementedError(
            f"Biểu giá EVN doanh nghiệp cho {business_type!r} CHƯA được cấu hình "
            f"(còn giá trị None trong EVN_BUSINESS_TIERS). Điền số liệu thật trước khi tính."
        )
    return sum(kwh * tiers[period] for period, kwh in kwh_by_period.items())
