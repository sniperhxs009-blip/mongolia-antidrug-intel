"""完整采集流水线，采集+研判+邮件一体化"""
from sqlalchemy.orm import Session
from app.crawler.engine import CrawlEngine
from app.analysis.engine import AnalysisEngine
from app.emailer.service import send_email
from app.db.models import Report
def run_intel_cycle(
    db: Session,
    report_type: str = "daily",
    send_email: bool = True,
    on_event = None,
    mode: str = "full"
):
    engine = CrawlEngine(db, on_event=on_event)
    if mode == "full":
        engine.run_full_crawl()
    else:
        engine.run_core_official_crawl()
    ana = AnalysisEngine(db)
    report = ana.generate_report(report_type=report_type)
    if send_email:
        subj = f"蒙古国禁毒{ana._type_label(report_type)}情报 {report.period_start.strftime('%Y-%m-%d')}"
        send_email(subj, report.content_html)
    return report

def run_full_task():
    from app.db import SessionLocal
    db = SessionLocal()
    run_intel_cycle(db, report_type="monthly", send_email=True, mode="full")
    db.close()
