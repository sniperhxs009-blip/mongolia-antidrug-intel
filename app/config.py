"""应用配置 — 对齐完整代码.txt 修复版"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    app_name: str = "蒙古国禁毒全网情报自动采集研判系统"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "change-me-to-a-long-random-string"
    timezone: str = "Asia/Ulaanbaatar"
    database_url: str = "sqlite:///./data/intel.db"
    crawl_interval: str = "hourly"
    crawl_mode: str = "news"
    news_when: str = "1y"
    full_when: str = "1y"
    forum_when: str = "1y"
    crawl_max_age_days: int = 365
    crawl_max_per_host_per_day: int = 10
    crawl_max_pages_per_source: int = 60
    crawl_max_pages_core: int = 30
    crawl_max_pages_official: int = 30
    crawl_max_depth: int = 2
    crawl_request_delay_sec: float = 1.0
    crawl_delay_jitter_sec: float = 2.0
    crawl_timeout_sec: int = 30
    crawl_user_agent: str = "Mozilla/5.0 (compatible; MN-AntiDrug-IntelBot/1.0)"
    crawl_ssl_verify: bool = False
    crawl_loose_filter: bool = True
    crawl_forbid_proxy: bool = True
    crawl_proxy_url: str = ""
    crawl_proxy_urls: str = ""
    enable_translation: bool = True
    enable_search_feeds: bool = True
    enable_official_crawl: bool = True
    enable_core_official_in_news: bool = True
    enable_official_stats: bool = True
    enable_forum_search: bool = True
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 465
    smtp_use_ssl: bool = True
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: str = ""
    email_daily_brief_hour: int = 8
    email_daily_brief_minute: int = 0
    enable_alert_email: bool = True
    report_language: str = "zh"
    data_dir: str = ""
    alert_keywords: str = "专项行动,跨境缉毒,新法,口岸严查,合成毒品,易制毒,UNODC,缉毒大案,吨,公斤,芬太尼,尼秦,安纳咖,大规模走私,边境缴获"

    @property
    def alert_keyword_list(self) -> List[str]:
        return [k.strip() for k in self.alert_keywords.split(",") if k.strip()]

    @property
    def resolved_data_dir(self) -> str:
        if self.data_dir:
            return self.data_dir
        if "/var/data" in self.database_url:
            return "/var/data"
        return "data"

    @property
    def reports_dir(self) -> str:
        return f"{self.resolved_data_dir.rstrip('/')}/reports"


@lru_cache
def get_settings() -> Settings:
    return Settings()
