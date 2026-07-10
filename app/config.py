"""
蒙古国禁毒全网情报自动采集、定时抓取、邮箱推送、交叉研判分析系统
应用配置
"""
from functools import lru_cache
from typing import List

from pydantic import Field
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

    # 新闻监测默认每小时；可选 every_30m | hourly | every_6h | every_12h | daily
    crawl_interval: str = "hourly"
    crawl_request_delay_sec: float = 0.5
    crawl_max_pages_per_source: int = 40
    crawl_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    crawl_timeout_sec: int = 25
    crawl_max_depth: int = 1
    enable_translation: bool = True
    enable_search_feeds: bool = True
    # 官网采集强制严格涉毒判定（勿开宽松）
    crawl_loose_filter: bool = False
    # SSL 异常站点仍尝试抓取
    crawl_ssl_verify: bool = False
    # 过期阈值（天）：文档要求近30日官方发布
    crawl_max_age_days: int = 30
    # 巡检时是否继续扫官网（文档要求直采官方种子；默认开启）
    enable_official_crawl: bool = True
    # 是否采集检察院/海关/PDF 等官方统计
    enable_official_stats: bool = True
    # 是否采集 Reddit/论坛/补充搜索引擎
    enable_forum_search: bool = False
    # 定时任务默认只抓新闻（长期监测）；每天固定时刻再跑全量研判
    crawl_mode: str = "news"  # news | full
    # Google News / 官网 site: 时间窗：文档要求近30日
    news_when: str = "30d"
    full_when: str = "30d"
    forum_when: str = "30d"
    # 新闻监测轮也跑核心官网增量（否则只能靠搜索聚合）
    enable_core_official_in_news: bool = True
    crawl_max_pages_official: int = 8
    crawl_max_pages_core: int = 6

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
    data_dir: str = ""  # 空则自动推断
    alert_keywords: str = (
        "专项行动,跨境缉毒,新法,口岸严查,合成毒品,易制毒,UNODC,缉毒大案,管制品,"
        "наркотик,мансууруулах,drug,narcotic,precursor,seizure"
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
