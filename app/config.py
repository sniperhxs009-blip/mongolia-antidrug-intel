"""
蒙古国禁毒全网情报自动采集、定时抓取、邮箱推送、交叉研判分析系统
应用配置 — 全量修复版（国内裸网检索式采集）
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "蒙古国禁毒全网情报自动采集研判系统"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "change-me-to-a-long-random-string"
    timezone: str = "Asia/Ulaanbaatar"

    database_url: str = "sqlite:///./data/intel.db"

    crawl_interval: str = "hourly"
    crawl_request_delay_sec: float = 0.3
    crawl_delay_jitter_sec: float = 0.5  # 修改原因：与 .env 同步，降低检索间隔
    crawl_max_pages_per_source: int = 20
    crawl_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    crawl_timeout_sec: int = 25
    crawl_max_depth: int = 2  # 修改原因：允许识别禁毒子栏目（深度2）
    enable_translation: bool = True
    enable_search_feeds: bool = True
    crawl_loose_filter: bool = False
    crawl_ssl_verify: bool = False
    crawl_max_age_days: int = 30

    # 硬性：禁止翻墙代理
    crawl_forbid_proxy: bool = True
    crawl_proxy_url: str = ""
    crawl_proxy_urls: str = ""

    # 修改原因：恢复蒙通社等本土媒体站内深度抓取
    enable_official_crawl: bool = True
    enable_core_official_in_news: bool = True
    enable_official_stats: bool = True
    enable_forum_search: bool = True

    crawl_mode: str = "news"
    news_when: str = "90d"
    full_when: str = "30d"
    forum_when: str = "30d"
    crawl_max_pages_official: int = 0
    crawl_max_pages_core: int = 8  # 修改原因：放宽核心站浅扫页数
    crawl_max_per_host_per_day: int = 10
    primary_search_rounds_per_day: int = 2
    secondary_search_rounds_per_day: int = 1

    # 鉴权 / 合规部署
    auth_enabled: bool = True
    auth_admin_user: str = "admin"
    auth_admin_password: str = "change-admin-password"
    auth_analyst_user: str = "analyst"
    auth_analyst_password: str = "change-analyst-password"
    require_manual_deploy: bool = True
    audit_log_retention_days: int = 90

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
    # 分级告警邮箱（空则回退 EMAIL_TO）
    email_alert_port: str = ""
    email_alert_nps: str = ""
    email_alert_joint: str = ""
    email_alert_law: str = ""

    report_language: str = "zh"
    data_dir: str = ""
    alert_keywords: str = (
        "专项行动,跨境缉毒,新法,口岸严查,合成毒品,易制毒,UNODC,缉毒大案,管制品,"
        "吨,公斤,芬太尼,尼秦,наркотик,мансууруулах,drug,narcotic,precursor,seizure"
    )

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
