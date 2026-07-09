"""
蒙古国禁毒情报系统 — 全量毒品关键词词库
覆盖：传统毒品、合成毒品、新精神活性物质(NPS)、医药滥用、易制毒化学品、蒙/英/俄/中别名
用于：过滤判定、搜索查询生成、告警触发
"""
from __future__ import annotations

from typing import List

# ========== 中文：传统毒品 ==========
ZH_TRADITIONAL = [
    "毒品", "禁毒", "缉毒", "贩毒", "吸毒", "涉毒", "制毒", "运毒", "藏毒", "毒资",
    "戒毒", "成瘾", "毒情", "毒枭", "毒窝", "零包贩毒", "以贩养吸",
    "鸦片", "罂粟", "海洛因", "白粉", "吗啡", "可卡因", "古柯", "大麻", "麻烟",
    "冰毒", "甲基苯丙胺", "摇头丸", "麻古", "K粉", "氯胺酮", "杜冷丁", "美沙酮",
    "安非他明", "苯丙胺", "致幻剂", "LSD", "迷幻蘑菇",

]

# ========== 中文：新型毒品 / NPS ==========
ZH_NOVEL = [
    "新型毒品", "新精神活性物质", "合成毒品", "实验室毒品", "策划药",
    "芬太尼", "芬太尼类", "卡西酮", "合成卡西酮", "合成大麻素", "Spice", "K2",
    "氟胺酮", "依托咪酯", "烟弹毒品", "电子烟毒品", "开心水", "丧尸药",
    "甲卡西酮", "喵喵", "浴盐", "彩虹烟", "笑气", "一氧化二氮", "N2O",
    "GHB", "迷奸水", "氟硝西泮", "三唑仑", "安眠酮",
    "哌替啶", "曲马多", "右美沙芬滥用", "依托咪酯滥用",
    "α-PVP", "MDPV", "4-MMC", "甲氧麻黄酮",
    "尼美西泮", "依托咪酯烟液", "合成阿片", "硝基嗪", "异托尼他秦",
]

# ========== 中文：易制毒 / 麻精药品 ==========
ZH_PRECURSOR = [
    "易制毒", "易制毒化学品", "麻精药品", "精神药品", "麻醉药品", "管制药品",
    "麻黄碱", "伪麻黄碱", "麻黄素", "羟亚胺", "胡椒基甲基酮", "黄樟素",
    "醋酸酐", "丙酮", "甲苯", "乙醚", "盐酸", "硫酸", "高锰酸钾",
    "邻酮", "羟亚胺", "溴素", "氯化亚砜", "苯乙酸", "苯乙腈",
    "管制目录", "列管", "前体化学品",
]

# ========== 蒙语（西里尔）==========
MN_KEYWORDS = [
    "мансууруулах", "мансууруулах бодис", "мансууруулах бодисын",
    "хар тамхи", "тамхины бодис", "донтсон", "донтлох", "донтлол",
    "урьдчилан сэргийлэх", "баривчилгаа", "хураан авсан",
    "наркотик", "наркотикын", "синтетик", "синтетик мансууруулах",
    "опиум", "героин", "кокаин", "каннабис", "марихуан", "гашиш",
    "метамфетамин", "амфетамин", "экстази", "кетамин", "ЛСД",
    "фентанyl", "фентанил", "прекурсор", "зохицуулалттай эм",
    "нөхөн сэргээх", "эмчилгээ", "хилээр нэвтрүүлэх", "контрабанд",
    "цагдаа", "гааль", "тусгай ажиллагаа", "гэмт хэрэг",
]

# ========== 英语：传统 + 执法 ==========
EN_TRADITIONAL = [
    "drug", "drugs", "narcotic", "narcotics", "controlled substance",
    "trafficking", "trafficker", "smuggling", "smuggler", "seizure", "seized",
    "interdiction", "anti-drug", "antidrug", "drug bust", "drug raid",
    "opium", "opioid", "heroin", "morphine", "cocaine", "crack cocaine",
    "cannabis", "marijuana", "marihuana", "hashish", "weed",
    "methamphetamine", "meth", "crystal meth", "amphetamine", "speed",
    "MDMA", "ecstasy", "molly", "ketamine", "LSD", "psilocybin",
    "addiction", "addict", "rehabilitation", "rehab", "overdose",
]

# ========== 英语：新型 / NPS / 合成 ==========
EN_NOVEL = [
    "new psychoactive substance", "NPS", "designer drug", "research chemical",
    "synthetic cannabinoid", "spice", "K2", "synthetic cathinone", "bath salts",
    "fentanyl", "fentanyl analogue", "carfentanil", "nitazene", "isotonitazene",
    "protonitazene", "metonitazene", "xylazine", "tranq", "tranq dope",
    "mephedrone", "4-MMC", "methylone", "MDPV", "alpha-PVP", "flakka",
    "GHB", "GBL", "1,4-butanediol", "Rohypnol", "flunitrazepam",
    "nitrous oxide", "laughing gas", "whippets",
    "etomidate", "etomidate vape", "synthetic opioid",
    "2C-B", "NBOMe", "25I-NBOMe", "DMT", "kratom", "kava",
    "tusi", "pink cocaine", "2C-B cocktail",
]

# ========== 英语：易制毒 ==========
EN_PRECURSOR = [
    "precursor", "precursors", "ephedrine", "pseudoephedrine",
    "phenylacetone", "P2P", "safrole", "isosafrole", "piperonal",
    "acetic anhydride", "APAAN", "ANPP", "NPP", "4-AP",
    "controlled chemical", "scheduled substance",
]

# ========== 俄语 ==========
RU_KEYWORDS = [
    "наркотик", "наркотиков", "наркотики", "наркомания", "наркоторговец",
    "контрабанда", "изъятие", "прекурсор", "героин", "кокаин", "каннабис",
    "марихуана", "метамфетамин", "амфетамин", "экстази", "фентанил",
    "синтетический", "психоактивн", "реабилитация",
]

# 合并：过滤用总词库（去重）
def all_drug_keywords() -> List[str]:
    bags = (
        ZH_TRADITIONAL + ZH_NOVEL + ZH_PRECURSOR
        + MN_KEYWORDS + EN_TRADITIONAL + EN_NOVEL + EN_PRECURSOR
        + RU_KEYWORDS
    )
    seen = set()
    out = []
    for k in bags:
        k = (k or "").strip()
        if not k:
            continue
        key = k.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(k)
    return out


# 搜索查询模板：每条都会带 Mongolia / монгол 约束
def build_search_queries() -> List[dict]:
    """生成多语种、多毒品类别的搜索任务。"""
    tasks: List[dict] = []

    # —— 蒙语核心 ——
    mn_cores = [
        "мансууруулах бодис",
        "хар тамхи",
        "метамфетамин",
        "героин",
        "каннабис",
        "кокаин",
        "кетамин",
        "фентанил",
        "синтетик мансууруулах",
        "прекурсор",
        "баривчилгаа мансууруулах",
        "гааль мансууруулах",
        "цагдаа хар тамхи",
    ]
    for q in mn_cores:
        tasks.append({
            "system_id": 8,
            "system_name": "全国媒体与公开资讯",
            "org_name": f"搜索·蒙语·{q[:18]}",
            "query": q,
            "hl": "mn",
            "gl": "mn",
            "ceid": "MN:mn",
            "engine": "google_news",
        })

    # —— 英语：蒙古 + 各类毒品 ——
    en_drug_groups = [
        "drug OR narcotic OR trafficking",
        "methamphetamine OR meth OR crystal meth",
        "heroin OR opium OR opioid",
        "cannabis OR marijuana OR hashish",
        "cocaine OR crack",
        "fentanyl OR nitazene OR xylazine",
        "ketamine OR MDMA OR ecstasy",
        "synthetic cannabinoid OR spice OR NPS",
        "precursor OR ephedrine OR pseudoephedrine",
        "seizure OR seized OR bust OR smuggling",
        "UNODC OR anti-drug",
    ]
    for g in en_drug_groups:
        tasks.append({
            "system_id": 8,
            "system_name": "全国媒体与公开资讯",
            "org_name": f"搜索·英语·{g.split(' OR ')[0][:16]}",
            "query": f"Mongolia ({g})",
            "hl": "en",
            "gl": "us",
            "ceid": "US:en",
            "engine": "google_news",
        })

    # —— 中文：蒙古国 + 毒品 ——
    zh_groups = [
        "毒品 OR 缉毒 OR 禁毒 OR 贩毒",
        "冰毒 OR 海洛因 OR 大麻 OR 可卡因",
        "芬太尼 OR 氯胺酮 OR 摇头丸 OR 新型毒品",
        "易制毒 OR 麻精 OR 制毒",
        "口岸查获 OR 跨境贩毒 OR 走私毒品",
    ]
    for g in zh_groups:
        tasks.append({
            "system_id": 8,
            "system_name": "全国媒体与公开资讯",
            "org_name": f"搜索·中文·{g.split(' OR ')[0]}",
            "query": f"蒙古国 ({g})",
            "hl": "zh-CN",
            "gl": "cn",
            "ceid": "CN:zh-Hans",
            "engine": "google_news",
        })

    # —— 媒体站内搜索（可打开原文）——
    site_queries = [
        "мансууруулах",
        "хар тамхи",
        "метамфетамин",
        "героин",
        "каннабис",
        "баривчилгаа",
    ]
    site_engines = [
        {
            "org_name": "GoGo站内搜索",
            "template": "https://gogo.mn/search?q={q}",
            "system_id": 8,
        },
        {
            "org_name": "蒙通社站内搜索",
            "template": "https://www.montsame.mn/mn/search?q={q}",
            "system_id": 8,
        },
        {
            "org_name": "IKON站内搜索",
            "template": "https://ikon.mn/search?q={q}",
            "system_id": 8,
        },
    ]
    for site in site_engines:
        for q in site_queries:
            tasks.append({
                "system_id": site["system_id"],
                "system_name": "全国媒体与公开资讯",
                "org_name": f"{site['org_name']}·{q}",
                "query": q,
                "hl": "mn",
                "gl": "mn",
                "ceid": "MN:mn",
                "engine": "site_search",
                "search_url": site["template"].format(q=q),
            })

    return tasks


# 告警级关键词（命中即提高等级）
ALERT_KEYWORDS = [
    "专项行动", "跨境缉毒", "口岸严查", "大规模查获", "缉毒大案",
    "fentanyl", "nitazene", "xylazine", "seizure", "seized",
    "баривчилгаа", "тусгай ажиллагаа", "фентанил", "метамфетамин",
    "芬太尼", "冰毒", "海洛因", "合成大麻", "易制毒",
]
