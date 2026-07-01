from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from api.alerts import send_email_alert, send_sms_alert

router = APIRouter(prefix="/api/alert", tags=["alert"])

class AlertRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    bill_before: float
    bill_after: float
    savings_percent: float

@router.post("/")
def trigger_alert(req: AlertRequest):
    results = {}
    
    if req.email:
        res_email = send_email_alert(req.email, req.bill_before, req.bill_after, req.savings_percent)
        results["email"] = res_email
    
    if req.phone:
        res_sms = send_sms_alert(req.phone, req.savings_percent)
        results["sms"] = res_sms

    if not req.email and not req.phone:
        raise HTTPException(status_code=400, detail="Must provide email or phone")

    return {"status": "success", "results": results}
