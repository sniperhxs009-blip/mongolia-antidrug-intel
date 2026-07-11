"""全自动邮箱推送：每日简报 + 重大突发即时告警（分级多邮箱）。

修改原因：告警按口岸大宗/新型毒品/跨境联合/禁毒新法分发；正文 HTML 转义防 XSS。
"""
from __future__ import annotations

import html
import logging
import smtplib
import ssl
from collections import defaultdict
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from sqlalchemy.orm import Session

from app.audit import audit_log
from app.config import get_settings
from app.crawler.filters import alert_category, sanitize_sensitive_text
from app.db.models import EmailLog, IntelItem, Report

logger = logging.getLogger("mn-antidrug.email")
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
            subtitle=html.escape(report.title or ""),
            content_html=report.content_html or f"<pre>{html.escape(report.content_md or '')}</pre>",
        )
        ok = self._send(subject, body_html, kind="daily", to_addrs=[settings.email_to])
        if ok:
            report.emailed = True
            self.db.commit()
        return ok

    def send_alert(self, items: List[IntelItem], report: Optional[Report] = None) -> bool:
        if not settings.enable_alert_email or not items:
            return False
        # 修改原因：按告警类别拆分推送，支持多邮箱独立接收
        buckets: dict[str, List[IntelItem]] = defaultdict(list)
        for it in items:
            kind = getattr(it, "alert_kind", None) or alert_category(
                f"{it.title or ''} {it.summary or ''}"
            )
            buckets[kind].append(it)

        any_ok = False
        for kind, group in buckets.items():
            to_list = self._recipients_for_alert_kind(kind)
            subject = (
                f"【紧急·{kind}】蒙古国禁毒告警 "
                f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"
            )
            blocks = []
            for it in group[:20]:
                title = html.escape(sanitize_sensitive_text(it.title_zh or it.title or "", hide_details=False))
                summary = html.escape(
                    sanitize_sensitive_text((it.summary_zh or it.summary or "")[:300], hide_details=False)
                )
                url = html.escape(it.url or "")
                blocks.append(
                    f"<div style='margin:12px 0;padding:12px;border-left:4px solid #b00020;background:#fff5f5'>"
                    f"<div><strong>等级：</strong>{html.escape(it.intel_level or '')}｜"
                    f"<strong>类别：</strong>{html.escape(it.category or '')}｜"
                    f"<strong>可信度：</strong>{html.escape(getattr(it, 'credibility', '中') or '中')}</div>"
                    f"<div><strong>机构：</strong>{html.escape(it.org_name or '')}"
                    f"（{html.escape(it.system_name or '')}）</div>"
                    f"<div><strong>标题：</strong>{title}</div>"
                    f"<div><strong>摘要：</strong>{summary}</div>"
                    f"<div><strong>来源：</strong><a href='{url}'>{url}</a></div>"
                    f"</div>"
                )
            extra = ""
            if report:
                extra = f"<hr/><h3>研判摘录</h3>{report.content_html or ''}"
            body = self._wrap_html(
                title=f"重大突发禁毒动态 — {kind}",
                subtitle="系统检测到关键信号，已按告警类别分级推送。",
                content_html="".join(blocks) + extra,
            )
            if self._send(subject, body, kind=f"alert:{kind}", to_addrs=to_list):
                any_ok = True
        return any_ok

    def send_report(self, report: Report, kind: str = "report") -> bool:
        subject = f"【蒙古国禁毒研判报告】{report.title}"
        body = self._wrap_html(
            title="情报研判正式报告",
            subtitle=html.escape(report.title or ""),
            content_html=report.content_html or f"<pre>{html.escape(report.content_md or '')}</pre>",
        )
        ok = self._send(subject, body, kind=kind, to_addrs=[settings.email_to])
        if ok:
            report.emailed = True
            self.db.commit()
        return ok

    def _recipients_for_alert_kind(self, kind: str) -> List[str]:
        mapping = {
            "口岸大宗": getattr(settings, "email_alert_port", "") or "",
            "芬太尼/尼秦新型毒品": getattr(settings, "email_alert_nps", "") or "",
            "跨境联合行动": getattr(settings, "email_alert_joint", "") or "",
            "禁毒新法": getattr(settings, "email_alert_law", "") or "",
        }
        specific = mapping.get(kind, "")
        raw = specific or settings.email_to or ""
        return [x.strip() for x in raw.replace(";", ",").split(",") if x.strip()]

    def _send(self, subject: str, html_body: str, kind: str, to_addrs: Optional[List[str]] = None) -> bool:
        recipients = to_addrs or ([settings.email_to] if settings.email_to else [])
        recipients = [r for r in recipients if r]
        if not self.is_configured() or not recipients:
            logger.warning("邮箱未配置，跳过发送: %s", subject)
            self._log(subject, kind, False, "SMTP not configured", ",".join(recipients))
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.email_from or settings.smtp_user
            msg["To"] = ", ".join(recipients)
            msg.attach(MIMEText("请使用支持 HTML 的邮箱客户端查看本情报简报。", "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            if settings.smtp_use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context) as server:
                    server.login(settings.smtp_user, settings.smtp_password)
                    server.sendmail(msg["From"], recipients, msg.as_string())
            else:
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                    server.starttls()
                    server.login(settings.smtp_user, settings.smtp_password)
                    server.sendmail(msg["From"], recipients, msg.as_string())

            self._log(subject, kind, True, "", ",".join(recipients))
            try:
                audit_log("email_send", ip="", user="", detail=f"{kind}|{subject}")
            except Exception:
                pass
            logger.info("邮件已发送: %s -> %s", subject, recipients)
            return True
        except Exception as exc:  # noqa: BLE001
            self._log(subject, kind, False, str(exc), ",".join(recipients))
            logger.exception("邮件发送失败")
            return False

    def _log(self, subject: str, kind: str, success: bool, error: str, to_addr: str = "") -> None:
        self.db.add(
            EmailLog(
                to_addr=to_addr or settings.email_to,
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
<html><head><meta charset="utf-8"/>
<style>
  .mail-body, .mail-body * {{ color: #1a1a1a !important; }}
  .mail-body a {{ color: #0b5cab !important; }}
</style>
</head>
<body style="margin:0;padding:0;background:#f3f4f6">
  <div style="max-width:860px;margin:0 auto;padding:24px">
    <div style="background:#0f2744;color:#fff;padding:20px 24px;border-radius:8px 8px 0 0">
      <div style="font-size:20px;font-weight:700;color:#ffffff">{html.escape(title)}</div>
      <div style="opacity:.85;margin-top:6px;font-size:13px;color:#ffffff">{subtitle}</div>
    </div>
    <div class="mail-body" style="background:#fff;padding:24px;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 8px 8px;color:#1a1a1a">
      {content_html}
      <hr style="margin:24px 0;border:none;border-top:1px solid #e5e7eb"/>
      <div style="font-size:12px;color:#6b7280 !important">
        本邮件由「蒙古国禁毒全网情报自动采集研判系统」自动发送。<br/>
        数据范围严格限定蒙古国公开渠道及 UNODC 等国际机构。标注来源网址、发布时间与情报等级，请注意核验。
      </div>
    </div>
  </div>
</body></html>
"""
