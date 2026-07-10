"""完整三语毒品关键词库，扩充新型毒品词汇"""
from __future__ import annotations
from typing import List

# 中文强涉毒词
ZH_STRONG = [
    "毒品","禁毒","缉毒","贩毒","吸毒","制毒","运毒","戒毒","海洛因","可卡因",
    "冰毒","大麻","安纳咖","芬太尼","尼秦","异托尼他秦","氯胺酮","合成大麻素",
    "易制毒","麻精药品","大宗查获","公斤毒品","吨级走私"
]
# 英文强词
EN_STRONG = [
    "narcotic","fentanyl","nitazene","meth","cannabis","anaga","drug bust",
    "cross-border trafficking","synthetic cannabinoid"
]
# 蒙语强词
MN_STRONG = [
    "хар тамхи","мансууруулах бодис","фентанил","нитазен","газар хил худалдаа"
]
# 弱关联词（宽松模式可单独放行）
WEAK_WORDS = ["seizure","trafficking","查获","走私","抓捕"]
ALERT_KEYWORDS = [
    "专项行动", "跨境缉毒", "芬太尼", "尼秦", "吨", "公斤", "fentanyl", "nitazene",
]


def all_drug_keywords():
    return ZH_STRONG + EN_STRONG + MN_STRONG + WEAK_WORDS


def build_search_queries(mode: str = "full", when: str = "1y") -> List[dict]:
    """生成检索任务；优先使用核心站点 site: 查询，并补充中英蒙新闻检索。"""
    when_suffix = f" when:{when}" if when else ""
    tasks: List[dict] = []
    try:
        from config.core_official import build_core_site_search_queries

        for q in build_core_site_search_queries(when or "1y"):
            tasks.append({
                "system_id": 8,
                "system_name": "全国媒体与公开资讯",
                "org_name": "核心检索",
                "query": q if "when:" in q else f"{q}{when_suffix}",
                "hl": "en",
                "gl": "us",
                "ceid": "US:en",
                "engine": "google_news",
                "require_mongolia": True,
                "tier": mode,
                "source_kind": "keyword_search",
            })
    except Exception:
        pass

    for g in ["毒品 OR 缉毒 OR 禁毒 OR 贩毒", "芬太尼 OR 尼秦 OR 安纳咖 OR 合成毒品"]:
        tasks.append({
            "system_id": 8,
            "system_name": "全国媒体与公开资讯",
            "org_name": f"搜索·中文·{g.split(' OR ')[0]}",
            "query": f"\"蒙古国\" ({g}){when_suffix}",
            "hl": "zh-CN",
            "gl": "cn",
            "ceid": "CN:zh-Hans",
            "engine": "google_news",
            "require_mongolia": True,
            "tier": mode,
        })
    for g in ["narcotic OR \"drug trafficking\" OR \"drug seizure\"", "fentanyl OR nitazene"]:
        tasks.append({
            "system_id": 8,
            "system_name": "全国媒体与公开资讯",
            "org_name": f"搜索·英语·{g.split(' OR ')[0].replace(chr(34),'')[:16]}",
            "query": f"Mongolia ({g}){when_suffix}",
            "hl": "en",
            "gl": "us",
            "ceid": "US:en",
            "engine": "google_news",
            "require_mongolia": True,
            "tier": mode,
        })
    return tasks
