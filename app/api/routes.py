"""FastAPI 路由：情报指挥台、实时进度 SSE、API"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import CrawlJob, EmailLog, IntelItem, Report, Source, StatRecord, SystemSetting, get_db
from app.pipeline import run_intel_cycle
from app.progress import progress_hub
from app.scheduler.jobs import reschedule_crawl
from app.auth import issue_token, require_admin, require_login, verify_login, auth_enabled, current_user
from app.audit import audit_log
from app.crawler.crawl_lock import try_acquire, release, current_owner

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def _run_cycle_with_progress(run_id: str, report_type: str = "daily", mode: str = "full") -> None:
    from app.db.models import SessionLocal

    prog = progress_hub.get(run_id)
    if not prog:
        return

    def on_event(event_type: str, **payload):
        prog.emit(event_type, **payload)

    owner = f"crawl-{run_id}"
    if not try_acquire(owner):
        prog.emit("error", status="failed", phase="失败", message="已有采集任务占用互斥锁")
        return
    db = SessionLocal()
    try:
        run_intel_cycle(
            db,
            report_type=report_type,
            send_email=(mode == "full"),
            on_event=on_event,
            mode=mode,
        )
    except Exception as exc:  # noqa: BLE001
        prog.emit("error", status="failed", phase="失败", message=str(exc))
    finally:
        release(owner)
        db.close()


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), user=Depends(current_user)):
    if auth_enabled() and not user:
        return RedirectResponse("/login", status_code=302)
    audit_log("view_dashboard", ip=_client_ip(request), user=(user or {}).get("username", ""))
    intel_count = db.query(IntelItem).count()
    source_count = db.query(Source).filter(Source.is_active.is_(True)).count()
    report_count = db.query(Report).count()
    alert_count = db.query(IntelItem).filter(IntelItem.is_alert.is_(True)).count()
    stat_count = db.query(StatRecord).count()
    latest_items = (
        db.query(IntelItem).order_by(IntelItem.crawled_at.desc()).limit(30).all()
    )
    latest_stats = (
        db.query(StatRecord).order_by(StatRecord.crawled_at.desc()).limit(20).all()
    )
    latest_reports = db.query(Report).order_by(Report.created_at.desc()).limit(6).all()
    latest_jobs = db.query(CrawlJob).order_by(CrawlJob.started_at.desc()).limit(5).all()
    systems = (
        db.query(Source.system_id, Source.system_name)
        .distinct()
        .order_by(Source.system_id)
        .all()
    )
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "intel_count": intel_count,
            "source_count": source_count,
            "report_count": report_count,
            "alert_count": alert_count,
            "user": user,
            "watermark": f"MN-INTEL|{(user or {}).get('username','anon')}|trace",
            "stat_count": stat_count,
            "latest_items": latest_items,
            "latest_stats": latest_stats,
            "latest_reports": latest_reports,
            "latest_jobs": latest_jobs,
            "systems": systems,
            "crawl_interval": settings.crawl_interval,
            "email_configured": bool(settings.smtp_user and settings.smtp_password and settings.email_to),
            "now": datetime.utcnow(),
        },
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return HTMLResponse(
        "<html><body style='font-family:sans-serif;padding:40px'>"
        "<h2>登录 · 蒙古国禁毒情报系统</h2>"
        "<form method='post' action='/api/login'>"
        "用户名 <input name='username'/> 密码 <input name='password' type='password'/>"
        "<button type='submit'>登录</button></form>"
        "<p style='color:#666'>管理员可执行全量采集/删除；研判员只读与导出。</p>"
        "</body></html>"
    )


@router.post("/api/login")
def api_login(request: Request, username: str = Form(...), password: str = Form(...)):
    info = verify_login(username, password)
    if not info:
        audit_log("login_failed", ip=_client_ip(request), user=username)
        return HTMLResponse("登录失败 <a href='/login'>返回</a>", status_code=401)
    tok = issue_token(info)
    audit_log("login_ok", ip=_client_ip(request), user=username)
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie("mn_auth_token", tok, httponly=True, samesite="lax")
    return resp


@router.get("/api/system-health")
def system_health(db: Session = Depends(get_db), user=Depends(require_login)):
    import os
    import shutil

    db_ok = True
    try:
        db.query(IntelItem).count()
    except Exception:
        db_ok = False
    disk = shutil.disk_usage(".")
    return {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
        "crawl_lock": current_owner(),
        "busy": progress_hub.is_busy(),
        "mail_configured": bool(settings.smtp_user and settings.smtp_password and settings.email_to),
        "auth_enabled": auth_enabled(),
        "require_manual_deploy": getattr(settings, "require_manual_deploy", True),
        "disk_free_mb": int(disk.free / 1024 / 1024),
        "pid": os.getpid(),
    }


@router.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat(), "app": settings.app_name}


@router.get("/api/self-check")
def self_check(db: Session = Depends(get_db), user=Depends(require_login)):
    """全量修复版自检报告。"""
    # 修改原因：数据接口必须登录
    from config.core_official import (
        CORE_OFFICIAL_SOURCES,
        FORBIDDEN_HOSTS,
        FORBIDDEN_PATH_FRAGMENTS,
        KW_EN,
        KW_MN,
        KW_ZH,
        TOPIC_BLACKLIST,
        build_core_site_search_queries,
        is_forbidden_url,
    )
    from config.drug_lexicon import all_drug_keywords

    samples = [
        "https://zasag.mn/anti-narcotics",
        "https://www.unodc.org/mongolia/",
        "https://police.gov.mn/",
        "https://customs.gov.mn/",
        "https://health.gov.mn/drug-control",
        "https://shturl.cc/x",
        "https://montsame.mn/cn",
        "https://www.unodc.org/unodc/en/data-and-analysis/world-drug-report.html",
    ]
    blocked = [u for u in samples if is_forbidden_url(u)]
    allowed = [u for u in samples if not is_forbidden_url(u)]
    tasks = build_core_site_search_queries(settings.news_when)
    intel_n = db.query(IntelItem).count()
    return {
        "status": "ok",
        "report": {
            "effective_seed_sites": len(CORE_OFFICIAL_SOURCES),
            "blacklist_hosts": len(FORBIDDEN_HOSTS),
            "blacklist_path_rules": len(FORBIDDEN_PATH_FRAGMENTS),
            "keyword_lexicon_size": len(all_drug_keywords()),
            "whitelist_zh_en_mn": len(KW_ZH) + len(KW_EN) + len(KW_MN),
            "topic_blacklist_size": len(TOPIC_BLACKLIST),
            "search_tasks": len(tasks),
            "proxy_forbidden": bool(getattr(settings, "crawl_forbid_proxy", True)),
            "official_crawl_disabled": not bool(settings.enable_official_crawl),
            "latest_intel_count": intel_n,
            "sample_blocked": blocked,
            "sample_allowed": allowed,
            "checks": {
                "blacklist_blocks_gov_mn": is_forbidden_url("https://police.gov.mn/news"),
                "no_anti_narcotics_path": is_forbidden_url("https://example.com/anti-narcotics"),
                "montsame_allowed": not is_forbidden_url("https://montsame.mn/cn"),
                "unodc_wdr_allowed": not is_forbidden_url(
                    "https://www.unodc.org/unodc/en/data-and-analysis/world-drug-report.html"
                ),
            },
            "ready_for_scheduled_crawl": all(
                [
                    is_forbidden_url("https://police.gov.mn/news"),
                    is_forbidden_url("https://zasag.mn/anti-narcotics"),
                    not is_forbidden_url("https://montsame.mn/cn"),
                    not is_forbidden_url("https://news.google.com/search?q=site:police.gov.mn"),
                    bool(getattr(settings, "crawl_forbid_proxy", True)),
                    bool(settings.enable_official_crawl),
                    len(CORE_OFFICIAL_SOURCES) >= 8,
                ]
            ),
        },
    }


@router.get("/api/trend-30d")
def trend_30d(db: Session = Depends(get_db), user=Depends(require_login)):
    from app.analysis.engine import AnalysisEngine

    return AnalysisEngine(db).trend_compare_30d()


@router.get("/api/port-trend")
def port_trend(db: Session = Depends(get_db), user=Depends(require_login)):
    # 修改原因：分口岸趋势独立接口
    from app.analysis.engine import AnalysisEngine

    return {"markdown": AnalysisEngine(db).port_trend_report(days=30)}


@router.get("/api/stats")
def stats(db: Session = Depends(get_db), user=Depends(require_login)):
    return {
        "intel_items": db.query(IntelItem).count(),
        "sources": db.query(Source).count(),
        "reports": db.query(Report).count(),
        "alerts": db.query(IntelItem).filter(IntelItem.is_alert.is_(True)).count(),
        "stat_records": db.query(StatRecord).count(),
        "jobs": db.query(CrawlJob).count(),
        "emails": db.query(EmailLog).count(),
    }


@router.get("/api/stat-records")
def list_stat_records(db: Session = Depends(get_db), limit: int = 50, user=Depends(require_login)):
    rows = (
        db.query(StatRecord)
        .order_by(StatRecord.crawled_at.desc())
        .limit(min(limit, 200))
        .all()
    )
    return [
        {
            "id": r.id,
            "metric_name": r.metric_name,
            "metric_value": r.metric_value,
            "unit": r.unit,
            "period": r.period,
            "org": r.org_name,
            "title": r.title,
            "source_url": r.source_url,
            "source_type": r.source_type,
            "snippet": r.raw_snippet,
            "confidence": r.confidence,
            "crawled_at": r.crawled_at.isoformat() if r.crawled_at else None,
        }
        for r in rows
    ]


@router.get("/api/intel")
def list_intel(
    db: Session = Depends(get_db),
    limit: int = 80,
    system_id: Optional[int] = None,
    alert_only: bool = False,
    since_id: Optional[int] = None,
    user=Depends(require_login),
):
    q = db.query(IntelItem).order_by(IntelItem.crawled_at.desc())
    if system_id:
        q = q.filter(IntelItem.system_id == system_id)
    if alert_only:
        q = q.filter(IntelItem.is_alert.is_(True))
    if since_id:
        # 增量拉取：只返回比 since_id 更新的条目（按 id 升序便于前端追加）
        rows = (
            db.query(IntelItem)
            .filter(IntelItem.id > since_id)
            .order_by(IntelItem.id.asc())
            .limit(min(limit, 200))
            .all()
        )
    else:
        rows = q.limit(min(limit, 200)).all()
    return [
        {
            "id": r.id,
            "title": r.title_zh or r.title,
            "org": r.org_name,
            "system": r.system_name,
            "level": r.intel_level,
            "category": r.category,
            "credibility": getattr(r, "credibility", "中"),
            "alert_kind": getattr(r, "alert_kind", ""),
            "port_tag": getattr(r, "port_tag", ""),
            "drug_type": getattr(r, "drug_type", ""),
            "url": r.url,
            "published_at": r.published_at.isoformat() if r.published_at else None,
            "crawled_at": r.crawled_at.isoformat() if r.crawled_at else None,
            "is_alert": r.is_alert,
        }
        for r in rows
    ]


@router.get("/api/export/ledger")
def export_ledger(
    request: Request,
    db: Session = Depends(get_db),
    fmt: str = "csv",
    hide_details: bool = False,
    limit: int = 500,
    user=Depends(require_login),
):
    """分级导出台账：hide_details=true 隐藏缴获数量与新型毒品细节。"""
    from fastapi.responses import FileResponse
    from app.export_ledger import export_intel_csv, export_intel_xlsx, export_intel_docx

    rows = db.query(IntelItem).order_by(IntelItem.crawled_at.desc()).limit(min(limit, 2000)).all()
    out_dir = f"{settings.resolved_data_dir}/exports"
    audit_log(
        "export_ledger",
        ip=_client_ip(request),
        user=(user or {}).get("username", ""),
        detail={"fmt": fmt, "hide_details": hide_details, "n": len(rows)},
    )
    if fmt == "xlsx":
        path = export_intel_xlsx(rows, f"{out_dir}/ledger.xlsx", hide_details=hide_details)
    elif fmt == "docx":
        path = export_intel_docx(rows, f"{out_dir}/ledger.docx", hide_details=hide_details)
    else:
        path = export_intel_csv(rows, f"{out_dir}/ledger.csv", hide_details=hide_details)
    return FileResponse(path, filename=path.split("/")[-1].split("\\")[-1])


@router.get("/api/sources")
def list_sources(db: Session = Depends(get_db), user=Depends(require_login)):
    rows = db.query(Source).order_by(Source.system_id, Source.id).all()
    return [
        {
            "id": s.id,
            "system_id": s.system_id,
            "system_name": s.system_name,
            "org_name": s.org_name,
            "page_url": s.page_url,
            "is_seed": s.is_seed,
            "is_active": s.is_active,
            "last_status": s.last_status,
            "last_crawled_at": s.last_crawled_at.isoformat() if s.last_crawled_at else None,
            "discover_depth": s.discover_depth,
        }
        for s in rows
    ]


@router.get("/api/reports")
def list_reports(db: Session = Depends(get_db), limit: int = 20, user=Depends(require_login)):
    rows = db.query(Report).order_by(Report.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "type": r.report_type,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "emailed": r.emailed,
            "file_path": r.file_path,
        }
        for r in rows
    ]


@router.get("/api/reports/{report_id}")
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    hide_details: bool = False,
    user=Depends(require_login),
):
    from app.crawler.filters import sanitize_sensitive_text

    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        return JSONResponse({"error": "not found"}, status_code=404)
    md = r.content_md or ""
    if hide_details:
        md = sanitize_sensitive_text(md, hide_details=True)
    return {
        "id": r.id,
        "title": r.title,
        "type": r.report_type,
        "content_md": md,
        "content_html": r.content_html if not hide_details else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "hide_details": hide_details,
    }


@router.post("/api/intel/purge")
def purge_intel(request: Request, db: Session = Depends(get_db), user=Depends(require_admin)):
    """清理非蒙古国或非涉毒的脏数据（仅管理员）。"""
    from app.crawler.cleanup import purge_irrelevant_items, purge_noise_geo_items

    result = purge_irrelevant_items(db)
    noise = purge_noise_geo_items(db)
    audit_log("purge_intel", ip=_client_ip(request), user=user.get("username"), detail={**result, **noise})
    return {"status": "ok", **result, "noise_geo_deleted": noise.get("deleted", 0)}


@router.get("/api/crawl/status")
def crawl_status(run_id: Optional[str] = None, user=Depends(require_login)):
    prog = progress_hub.get(run_id) if run_id else progress_hub.current()
    if not prog:
        return {"status": "idle", "busy": False, "lock": current_owner()}
    snap = prog.snapshot()
    snap["busy"] = prog.status in ("queued", "running", "analyzing", "emailing")
    snap["lock"] = current_owner()
    return snap


@router.post("/api/crawl/run")
def trigger_crawl(
    request: Request,
    report_type: str = "daily",
    mode: str = "full",
    user=Depends(require_admin),
):
    """mode=news：仅抓最新新闻（快）；mode=full：新闻+研判报告。仅管理员。"""
    if mode not in ("news", "full"):
        mode = "full"
    if progress_hub.is_busy() or current_owner():
        cur = progress_hub.current()
        return JSONResponse(
            {
                "status": "busy",
                "message": "已有巡检任务正在执行",
                "run_id": cur.run_id if cur else None,
                "progress": cur.snapshot() if cur else None,
                "lock": current_owner(),
            },
            status_code=409,
        )
    prog = progress_hub.create(report_type=report_type)
    audit_log("crawl_start", ip=_client_ip(request), user=user.get("username"), detail={"mode": mode})
    t = threading.Thread(
        target=_run_cycle_with_progress,
        args=(prog.run_id, report_type, mode),
        daemon=True,
        name=f"crawl-{prog.run_id}",
    )
    t.start()
    return {"status": "started", "report_type": report_type, "mode": mode, "run_id": prog.run_id}


@router.get("/api/crawl/stream")
def crawl_stream(run_id: Optional[str] = None, user=Depends(require_login)):
    """SSE：实时推送巡检进度与逐条情报事件。"""

    def event_generator():
        last_len = 0
        idle_ticks = 0
        while True:
            prog = progress_hub.get(run_id) if run_id else progress_hub.current()
            if not prog:
                yield f"data: {json.dumps({'type': 'idle', 'message': '无活动任务'}, ensure_ascii=False)}\n\n"
                break

            snap = prog.snapshot()
            events = snap.get("events") or []
            if len(events) > last_len:
                for evt in events[last_len:]:
                    payload = {"type": "event", "event": evt, "progress": {
                        k: snap[k] for k in (
                            "run_id", "status", "phase", "message", "percent",
                            "total_sources", "current_index", "pages_fetched",
                            "items_new", "items_updated", "items_filtered",
                            "error_count", "current_org", "current_url", "report_id",
                        )
                    }}
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                last_len = len(events)
                idle_ticks = 0
            else:
                # 心跳，保持连接
                heartbeat = {
                    "type": "heartbeat",
                    "progress": {
                        "status": snap["status"],
                        "phase": snap["phase"],
                        "percent": snap["percent"],
                        "message": snap["message"],
                        "current_org": snap["current_org"],
                        "items_new": snap["items_new"],
                        "pages_fetched": snap["pages_fetched"],
                        "report_id": snap["report_id"],
                    },
                }
                yield f"data: {json.dumps(heartbeat, ensure_ascii=False)}\n\n"
                idle_ticks += 1

            if snap["status"] in ("success", "failed") and idle_ticks >= 2:
                yield f"data: {json.dumps({'type': 'closed', 'progress': snap}, ensure_ascii=False)}\n\n"
                break
            time.sleep(0.6)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/schedule")
def update_schedule(interval: str = Form(...), user=Depends(require_admin)):
    # 修改原因：定时修改仅管理员
    if interval not in ("every_30m", "hourly", "every_6h", "every_12h", "daily"):
        return JSONResponse({"error": "invalid interval"}, status_code=400)
    reschedule_crawl(interval)
    from app.db.models import SessionLocal

    db = SessionLocal()
    try:
        row = db.query(SystemSetting).filter(SystemSetting.key == "crawl_interval").first()
        if row:
            row.value = interval
        else:
            db.add(SystemSetting(key="crawl_interval", value=interval))
        db.commit()
    finally:
        db.close()
    return RedirectResponse(url="/", status_code=303)


@router.get("/reports/{report_id}", response_class=HTMLResponse)
def report_page(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db),
    hide_details: bool = False,
    user=Depends(current_user),
):
    if auth_enabled() and not user:
        return RedirectResponse("/login", status_code=302)
    from app.crawler.filters import sanitize_sensitive_text

    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        return HTMLResponse("报告不存在", status_code=404)
    audit_log("view_report", ip=_client_ip(request), user=(user or {}).get("username", ""), detail=report_id)
    content_html = r.content_html or ""
    if hide_details:
        content_html = sanitize_sensitive_text(content_html, hide_details=True)
    # 隐形溯源水印（CSS 几乎不可见）
    wm = f"<div style='position:fixed;bottom:4px;right:8px;opacity:0.04;font-size:10px;pointer-events:none'>" \
         f"MN-INTEL|{(user or {}).get('username','anon')}|{report_id}</div>"
    return templates.TemplateResponse(
        "report.html",
        {
            "request": request,
            "report": r,
            "app_name": settings.app_name,
            "content_html": content_html + wm,
            "hide_details": hide_details,
            "user": user,
        },
    )


@router.get("/sources", response_class=HTMLResponse)
def sources_page(request: Request, db: Session = Depends(get_db), user=Depends(current_user)):
    if auth_enabled() and not user:
        return RedirectResponse("/login", status_code=302)
    rows = db.query(Source).order_by(Source.system_id, Source.id).all()
    return templates.TemplateResponse(
        "sources.html",
        {"request": request, "sources": rows, "app_name": settings.app_name, "user": user},
    )
