"""站点抓取频次限制，上限10次/天"""
from sqlalchemy.orm import Session
from app.db.models import CrawlRecord
from datetime import datetime, timedelta
def can_crawl_host(db: Session, host_url: str) -> bool:
    today_start = datetime.utcnow().replace(hour=0,minute=0,second=0)
    host = urlparse(host_url).netloc.lower()
    cnt = db.query(CrawlRecord).filter(Crawl.host == host, CrawlRecord.created_at >= today_start).count()
    settings = get_settings()
    return cnt < settings.crawl_max_per_host_per_day
def mark_host_crawled(db: Session, host_url: str):
    host = urlparse(host_url).netloc.lower()
    rec = CrawlRecord(host=host, created_at=datetime.utcnow())
    db.add(rec)
    db.commit()
