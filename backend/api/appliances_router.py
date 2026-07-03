"""Appliance CRUD endpoints. All routes require valid JWT (see auth.get_current_user)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from auth import get_current_user
from db.database import get_db
from db.models import ApplianceModel, User

router = APIRouter(prefix="/appliances", tags=["appliances"])


class ApplianceIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    power_w: float = Field(gt=0)
    duration_hours: float = Field(gt=0, le=24)
    quantity: int = Field(1, ge=1)
    candidate_hours: List[int] = []
    is_flexible: bool = True
    group_name: Optional[str] = None

    @field_validator("candidate_hours")
    @classmethod
    def _candidate_hours_in_day_range(cls, v: List[int]) -> List[int]:
        """Mỗi giờ ứng viên phải trong 0-23 — giờ ngoài khoảng làm /optimize trả 500 (build_qubo
        không tra được giá tại giờ đó) thay vì lỗi validate rõ ràng (bug #7)."""
        for h in v:
            if not (0 <= h <= 23):
                raise ValueError(f"candidate_hours chứa giờ ngoài 0-23: {h}")
        return v


class ApplianceOut(BaseModel):
    id: int
    name: str
    power_w: float
    duration_hours: float
    quantity: int
    candidate_hours: List[int]
    is_flexible: bool
    group_name: Optional[str] = None

    model_config = {"from_attributes": True}


def _to_out(row: ApplianceModel) -> ApplianceOut:
    hours = list(row.candidate_hours or [])
    return ApplianceOut(
        id=row.id, name=row.name, power_w=row.power_w, duration_hours=row.duration_hours,
        quantity=row.quantity if row.quantity else 1,
        candidate_hours=hours, is_flexible=row.is_flexible,
        group_name=row.group_name,
    )


def _get_owned(appliance_id: int, user_id: int, db: Session) -> ApplianceModel:
    row = db.query(ApplianceModel).filter(
        ApplianceModel.id == appliance_id, ApplianceModel.user_id == user_id
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appliance not found")
    return row


@router.get("", response_model=List[ApplianceOut])
def list_appliances(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(ApplianceModel).filter(ApplianceModel.user_id == current_user.id).all()
    return [_to_out(r) for r in rows]


@router.post("", response_model=ApplianceOut, status_code=status.HTTP_201_CREATED)
def create_appliance(
    payload: ApplianceIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = ApplianceModel(
        user_id=current_user.id,
        name=payload.name, power_w=payload.power_w, duration_hours=payload.duration_hours,
        quantity=payload.quantity,
        candidate_hours=list(payload.candidate_hours),
        is_flexible=payload.is_flexible,
        group_name=payload.group_name,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.put("/{appliance_id}", response_model=ApplianceOut)
def update_appliance(
    appliance_id: int,
    payload: ApplianceIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = _get_owned(appliance_id, current_user.id, db)
    row.name = payload.name
    row.power_w = payload.power_w
    row.duration_hours = payload.duration_hours
    row.quantity = payload.quantity
    row.candidate_hours = list(payload.candidate_hours)
    row.is_flexible = payload.is_flexible
    row.group_name = payload.group_name
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.delete("/{appliance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appliance(
    appliance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = _get_owned(appliance_id, current_user.id, db)
    db.delete(row)
    db.commit()
