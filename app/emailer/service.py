"""全自动邮箱推送：每日简报 + 重大突发即时告警"""
from __future__ import annotations

import logging
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import EmailLog, IntelItem, Report

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    def __init__(self, db: Session):
        self.db = db

    def is_configured(self) -> bool:
        return bool(settings.smtp_host and settings.smtp_user and settings.smtp_password and settings.email_to)

    def send_daily_brief(self, report: Report) -> bool:
        subject = f"【蒙古国禁毒情报日简报】{datetime.utcnow().strftime('%Y-%m-%d')}"
        body_html = self._wrap_html(
            title="蒙古国禁毒情报每日简报",
            subtitle=report.title,
            content_html=report.content_html or f"<pre>{report.content_md}</pre>",
        )
        ok = self._send(subject, body_html, kind="daily")
        if ok:
            report.emailed = True
            self.db.commit()
        return ok

    def send_alert(self, items: List[IntelItem], report: Optional[Report] = None) -> bool:
        if not settings.enable_alert_email or not items:
            return False
        subject = f"【紧急】蒙古国禁毒重大动态告警 {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"
        blocks = []
        for it in items[:20]:
            blocks.append(
                f"<div style='margin:12px 0;padding:12px;border-left:4px solid #b00020;background:#fff5f5'>"
                f"<div><strong>等级：</strong>{it.intel_level}｜<strong>类别：</strong>{it.category}</div>"
                f"<div><strong>机构：</strong>{it.org_name}（{it.system_name}）</div>"
                f"<div><strong>标题：</strong>{it.title_zh or it.title}</div>"
                f"<div><strong>摘要：</strong>{(it.summary_zh or it.summary or '')[:300]}</div>"
                f"<div><strong>来源：</strong><a href='{it.url}'>{it.url}</a></div>"
                f"</div>"
            )
        extra = ""
        if report:
            extra = f"<hr/><h3>研判摘录</h3>{report.content_html}"
        body = self._wrap_html(
            title="重大突发禁毒动态 — 即时告警",
            subtitle="系统检测到专项行动/跨境缉毒/新法/口岸严查等关键信号，已触发秒级推送。",
            content_html="".join(blocks) + extra,
        )
        return self._send(subject, body, kind="alert")

    def send_report(self, report: Report, kind: str = "report") -> bool:
        subject = f"【蒙古国禁毒研判报告】{report.title}"
        body = self._wrap_html(
            title="情报研判正式报告",
            subtitle=report.title,
            content_html=report.content_html or f"<pre>{report.content_md}</pre>",
        )
        ok = self._send(subject, body, kind=kind)
        if ok:
            report.emailed = True
            self.db.commit()
        return ok

    def _send(self, subject: str, html_body: str, kind: str) -> bool:
        if not self.is_configured():
            logger.warning("邮箱未配置，跳过发送: %s", subject)
            self._log(subject, kind, False, "SMTP not configured")
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.email_from or settings.smtp_user
            msg["To"] = settings.email_to
            msg.attach(MIMEText("请使用支持 HTML 的邮箱客户端查看本情报简报。", "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            if settings.smtp_use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context) as server:
                    server.login(settings.smtp_user, settings.smtp_password)
                    server.sendmail(msg["From"], [settings.email_to], msg.as_string())
            else:
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                    server.starttls()
                    server.login(settings.smtp_user, settings.smtp_password)
                    server.sendmail(msg["From"], [settings.email_to], msg.as_string())

            self._log(subject, kind, True, "")
            logger.info("邮件已发送: %s", subject)
            return True
        except Exception as exc:  # noqa: BLE001
            self._log(subject, kind, False, str(exc))
            logger.exception("邮件发送失败")
            return False

    def _log(self, subject: str, kind: str, success: bool, error: str) -> None:
        self.db.add(
            EmailLog(
                to_addr=settings.email_to,
                subject=subject,
                kind=kind,
                success=success,
                error=error,
                created_at=datetime.utcnow(),
            )
        )
        self.db.commit()

    @staticmethod
    def _wrap_html(title: str, subtitle: str, content_html: str) -> str:
        return f"""
<!DOCTYPE html>
<html><head><meta charset="utf-8"/></head>
<body style="margin:0;padding:0;background:#f3f4f6">
  <div style="max-width:860px;margin:0 auto;padding:24px">
    <div style="background:#0f2744;color:#fff;padding:20px 24px;border-radius:8px 8px 0 0">
      <div style="font-size:20px;font-weight:700">{title}</div>
      <div style="opacity:.85;margin-top:6px;font-size:13px">{subtitle}</div>
    </div>
    <div style="background:#fff;padding:24px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 8px 8px">
      {content_html}
      <hr style="margin:24px 0;border:none;border-top:1px solid #e5e7eb"/>
      <div style="font-size:12px;color:#6b7280">
        本邮件由「蒙古国禁毒全网情报自动采集研判系统」自动发送。<br/>
        数据范围严格限定蒙古国官方禁毒体系及 UNODC 公开渠道。标注来源网址、发布时间与情报等级，请注意核验。
      </div>
    </div>
  </div>
</body></html>
"""
