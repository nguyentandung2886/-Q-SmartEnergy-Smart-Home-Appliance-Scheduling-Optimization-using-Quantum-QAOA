import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging

logger = logging.getLogger(__name__)

def send_email_alert(recipient: str, bill_before: float, bill_after: float, savings: float):
    sender_email = os.environ.get("EMAIL_SENDER")
    sender_password = os.environ.get("EMAIL_PASSWORD")

    if not sender_email or not sender_password:
        logger.warning(f"Mock Email Alert: To={recipient}, Savings={savings}% (Configure EMAIL_SENDER/PASSWORD to send real emails)")
        return {"status": "mock", "message": "Simulated email sent (Missing credentials)"}

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🚨 Q-SmartEnergy: Cảnh báo tối ưu hóa năng lượng"
        msg["From"] = sender_email
        msg["To"] = recipient

        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: auto; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
              <div style="background-color: #06B6D4; padding: 20px; text-align: center; color: white;">
                <h2 style="margin: 0;">Báo Cáo Tối Ưu Năng Lượng</h2>
              </div>
              <div style="padding: 30px;">
                <p>Xin chào,</p>
                <p>Hệ thống Q-SmartEnergy đã hoàn tất việc chạy thuật toán tối ưu hóa lịch chạy thiết bị của bạn.</p>
                <div style="background-color: #f9fafb; padding: 15px; border-radius: 6px; margin: 20px 0;">
                  <h3 style="margin-top: 0; color: #111827;">Kết quả hóa đơn dự kiến:</h3>
                  <ul style="list-style-type: none; padding: 0;">
                    <li style="margin-bottom: 10px;">📉 <b>Trước tối ưu:</b> <span style="color: #ef4444;">{bill_before:,.0f} ₫</span></li>
                    <li style="margin-bottom: 10px;">✨ <b>Sau tối ưu (QAOA):</b> <span style="color: #10b981;">{bill_after:,.0f} ₫</span></li>
                    <li>💰 <b>Mức tiết kiệm:</b> <span style="color: #06b6d4; font-size: 1.2em; font-weight: bold;">{savings}%</span></li>
                  </ul>
                </div>
                <p>Hãy truy cập vào Dashboard để xem chi tiết biểu đồ điện năng.</p>
                <p style="margin-top: 30px; font-size: 0.9em; color: #6b7280;">Trân trọng,<br>Hệ thống AI Q-SmartEnergy</p>
              </div>
            </div>
          </body>
        </html>
        """
        
        part = MIMEText(html, "html")
        msg.attach(part)

        # Connect to Gmail SMTP server
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient, msg.as_string())
        server.quit()
        
        return {"status": "success", "message": "Email sent successfully"}
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return {"status": "error", "message": str(e)}

def send_sms_alert(phone: str, savings: float):
    # Twilio logic can be placed here later
    # For now, we simulate SMS to avoid complicated setups during hackathons
    logger.info(f"Mock SMS Alert to {phone}: Hệ thống tối ưu năng lượng đã chạy xong. Tiết kiệm: {savings}%")
    return {"status": "mock", "message": f"Simulated SMS sent to {phone}"}
