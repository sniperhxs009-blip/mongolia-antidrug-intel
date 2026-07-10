"""核心数据源、黑白名单配置【修复重点】
1. FORBIDDEN_HOSTS仅保留无法直连蒙古gov域名
2. 新增GOGO/IKON/NEWS.MN/UB POST民间媒体种子
3. ALLOW_ANY_MN_DOMAIN=True 放行全部蒙古媒体域名
4. 缩减黑名单，不再误过滤禁毒会议、专项行动
"""
from typing import List, Dict
# 永久封禁国内无法访问的蒙古官方gov站点
FORBIDDEN_HOSTS = {
    "police.gov.mn",
    "customs.gov.mn",
    "health.gov.mn",
    "zasag.mn",
    "mohs.mn",
    "mmra.gov.mn",
    "mofa.gov.mn",
    "ecustoms.mn"
}
# 封禁无效专栏路径
FORBIDDEN_PATH_FRAGMENTS = ("/anti-narcotics", "/drug-control", "unodc.org/mongolia")
# 允许全部.mn媒体域名
ALLOW_ANY_MN_DOMAIN = True
# 大幅缩小无关内容黑名单，移除画展、股市等宽泛屏蔽词
TOPIC_BLACKLIST = [
    "human trafficking",
    "anti-corruption",
    "奥运会",
    "兴奋剂wada",
    "乌兰乌德布里亚特纯本地新闻"
]
# 核心合法数据源（新增4家蒙古本土媒体）
CORE_OFFICIAL_SOURCES: List[Dict] = [
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "蒙通社 MONTSAME",
        "base_url": "https://montsame.mn",
        "seed_paths": ["/cn", "/en", "/mn"],
        "lang": "zh,en,mn",
        "search_mode_only": True,
        "keywords_extra": ["хар тамхи", "毒品", "narcotics"]
    },
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "GOGO.MN蒙古媒体",
        "base_url": "https://gogo.mn",
        "seed_paths": ["/mn"],
        "lang": "mn",
        "search_mode_only": True
    },
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "IKON.MN",
        "base_url": "https://ikon.mn",
        "seed_paths": ["/mn"],
        "lang": "mn"
    },
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "News.mn",
        "base_url": "https://news.mn",
        "seed_paths": ["/mn"],
        "lang": "mn"
    },
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "UB Post",
        "base_url": "https://ubpost.mongolnews.mn",
        "seed_paths": ["/en"],
        "lang": "en"
    },
    {
        "system_id": 7,
        "system_name": "国际禁毒协作机构",
        "org_name": "UNODC 联合国毒罪办",
        "base_url": "https://www.unodc.org",
        "seed_paths": ["/unodc/en/data-and-analysis/world-drug-report.html"],
        "lang": "en",
        "keywords_extra": ["Mongolia,narcotics"]
    },
    {
        "system_id": 4,
        "system_name": "边境口岸缉毒查验体系",
        "org_name": "中国禁毒网",
        "base_url": "http://www.nncc626.com",
        "seed_paths": ["/"],
        "lang": "zh",
        "keywords_extra": ["蒙古国,中蒙口岸,扎门乌德,甘其毛都"]
    }
]
# 中英蒙检索关键词
KW_ZH = ["毒品","禁毒","缉毒","贩毒","芬太尼","尼秦","安纳咖","合成毒品","口岸走私"]
KW_EN = ["narcotics","drug seizure","fentanyl","nitazene","trafficking","Mongolia"]
KW_MN = ["хар тамхи","мансууруулах бодис","синтетик мансууруулах бодис"]
def is_forbidden_url(url: str) -> bool:
    """判断链接是否黑名单封禁"""
    from urllib.parse import urlparse
    host = urlparse(url).netloc.lower().replace("www.","")
    path = url.lower()
    if host in FORBIDDEN_HOSTS or host.endswith(".gov.mn") or host == "gov.mn":
        return True
    for frag in FORBIDDEN_PATH_FRAGMENTS:
        if frag in path:
            return True
    return False
def build_core_site_search_queries(time_range: str = "1y") -> List[str]:
    """生成1年窗口检索语句"""
    queries = []
    for source in CORE_OFFICIAL_SOURCES:
        domain = source["base_url"].replace("https://","").replace("http://","")
        for kw in KW_ZH + KW_EN + KW_MN:
            queries.append(f"site:{domain} {kw} {time_range}")
    return queries
