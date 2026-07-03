"""POST /forecast: classical-ML duration forecast for flexible appliances (Vòng Phụ Mức TB).

Nhận đặc trưng công việc (vd máy giặt: khối lượng đồ + chương trình; bình nóng: số người),
trả thời gian chạy dự báo + MAE mô hình. Frontend hiển thị con số này rồi gửi lại làm
duration_overrides cho /optimize, nên lớp ML (classical) thực sự cấp dữ liệu cho QAOA (quantum).
"""
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from db.models import User

from core import forecaster

router = APIRouter(tags=["forecast"])


def _require_household(current_user: User) -> None:
    """Dự báo thời lượng chỉ áp dụng cho 3 thiết bị hộ gia đình (máy giặt, bình nóng lạnh) nên
    chặn hẳn tài khoản doanh nghiệp — thiết bị nhà máy không nằm trong mô hình FLEX_FORECAST."""
    if current_user.role == "business":
        raise HTTPException(
            status_code=403,
            detail="Tính năng dự báo chỉ dành cho tài khoản hộ gia đình.",
        )


@router.get("/forecast/schema")
def forecast_schema(current_user: User = Depends(get_current_user)) -> Dict[str, list]:
    """Đặc trưng mỗi thiết bị linh hoạt cần để dự báo — UI dựa vào đây để render đúng input."""
    _require_household(current_user)
    return forecaster.FORECAST_SCHEMA


@router.post("/forecast")
def forecast(
    payload: Dict[str, Dict[str, object]],
    current_user: User = Depends(get_current_user),
) -> Dict[str, Dict[str, float]]:
    """payload: {"jobs": {ten_thiet_bi: {dac_trung: gia_tri}}}.
    Trả {ten_thiet_bi: {"predicted_hours": x, "test_mae": y}}. Bỏ qua thiết bị không có mô hình."""
    _require_household(current_user)
    jobs = payload.get("jobs", {})
    if not isinstance(jobs, dict):
        raise HTTPException(status_code=422, detail="'jobs' phải là object {ten_thiet_bi: dac_trung}")

    result: Dict[str, Dict[str, float]] = {}
    for name, features in jobs.items():
        if name not in forecaster.FORECAST_SCHEMA:
            continue
        try:
            result[name] = {
                "predicted_hours": forecaster.predict_duration(name, features or {}),
                "test_mae": round(forecaster.model_mae(name), 3),
            }
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=f"'{name}': {exc}")
    return result
