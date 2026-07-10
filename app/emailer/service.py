"""SMTP邮件发送服务"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.config import get_settings
from app.db import SessionLocal
from app.db.models import EmailLog
from datetime import datetime
def send_email(subject: str, html_content: str) -> bool:
    settings = get_settings()
    msg = MIMEMultipart()
    msg["From"] = settings.email_from
    msg["To"] = settings.email_to
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    success = False
    err = ""
    try:
        server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port)
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
        server.quit()
        success = True
    except Exception as e:
        err = str(e)
    db = SessionLocal()
    log = EmailLog(subject=subject, success=success, error_msg=err)
    db.add(log)
    db.commit()
    db.close()
    return success
