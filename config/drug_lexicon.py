"""
蒙古国禁毒情报系统 — 全量毒品关键词词库
覆盖：传统毒品、合成毒品、新精神活性物质(NPS)、医药滥用、易制毒化学品、蒙/英/俄/中别名
用于：过滤判定、搜索查询生成、告警触发
"""
from __future__ import annotations

from typing import List
from config.core_official import SEARCH_NEGATIVE_EXCLUDE

# ========== 中文：传统毒品 ==========
# 依据：蒙古国主流流通清单（大麻/安纳咖/冰毒/医用阿片外流/海洛因等）
ZH_TRADITIONAL = [
    "毒品", "禁毒", "缉毒", "贩毒", "吸毒", "涉毒", "制毒", "运毒", "藏毒", "毒资",
    "戒毒", "成瘾", "毒情", "毒枭", "毒窝", "零包贩毒", "以贩养吸",
    "鸦片", "罂粟", "海洛因", "白粉", "吗啡", "可卡因", "古柯",
    "大麻", "天然大麻", "黑烟草", "麻烟", "哈希什", "大麻树脂", "大麻膏", "大麻油",
    "冰毒", "冰块", "甲基苯丙胺", "摇头丸", "麻古", "K粉", "氯胺酮", "杜冷丁", "美沙酮",
    "安非他明", "苯丙胺", "安纳咖", "苯甲酸钠咖啡因",
    "曲马多", "羟考酮", "可待因", "芬太尼",
    "致幻剂", "LSD", "迷幻蘑菇", "裸盖菇素",
]

# ========== 中文：新型毒品 / NPS ==========
# 依据：2023-2026 蒙古国快速扩散 NPS（芬太尼/尼秦/奥芬/合成大麻素/卡西酮/派对毒/液态精神药）
ZH_NOVEL = [
    "新型毒品", "新精神活性物质", "合成毒品", "实验室毒品", "策划药",
    "芬太尼", "芬太尼类", "芬太尼衍生物", "合成阿片",
    "尼秦", "尼秦类", "硝基嗪", "异托尼他秦", "异硝唑啉", "甲托尼他秦",
    "奥芬", "奥芬类", "奥芬衍生物",
    "卡西酮", "合成卡西酮", "浴盐", "甲卡西酮", "喵喵",
    "合成大麻素", "香料毒", "人工合成大麻素",
    "HHC", "Delta-8", "Delta-8 THC", "Δ8-THC",
    "雾化电子烟油", "电子烟毒品", "烟弹毒品", "草本香料",
    "裸盖菇素", "迷幻蘑菇", "致幻蘑菇",
    "快乐水", "派对毒品", "混合粉末", "复合毒剂", "多成分复合毒剂",
    "液态新型精神药物", "液态精神药品", "情绪舒缓液",
    "氟胺酮", "依托咪酯", "开心水", "丧尸药",
    "彩虹烟", "笑气", "一氧化二氮", "N2O",
    "GHB", "迷奸水", "氟硝西泮", "三唑仑", "安眠酮",
    "哌替啶", "右美沙芬滥用", "依托咪酯滥用",
    "α-PVP", "MDPV", "4-MMC", "甲氧麻黄酮",
    "尼美西泮", "依托咪酯烟液",
    "安定", "阿普唑仑", "苯二氮卓", "苯二氮䓬",
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
    "трамадол", "оксикодон", "морфин", "кодеин",
    "нитазен", "изотонитазен", "метонитазен",
    "синтетик каннабиноид", "псилоцибин", "катинон", "МДПВ",
    "диазепам", "алпразолам", "бензодиазепин",
    "нөхөн сэргээх", "эмчилгээ", "хилээр нэвтрүүлэх", "контрабанд",
    "цагдаа", "гааль", "тусгай ажиллагаа", "гэмт хэрэг",
    # 文档补充（仅作搜索词；入库判定见 filters 强/弱词，勿把 тэмцэх 当强词）
    "мансууруулах бодисын эсрэг", "баривчлагдсан", "сэргээх төв",
]

# ========== 英语：传统 + 执法 ==========
EN_TRADITIONAL = [
    "drug", "drugs", "narcotic", "narcotics", "controlled substance",
    "trafficking", "trafficker", "smuggling", "smuggler", "seizure", "seized",
    "interdiction", "anti-drug", "antidrug", "drug bust", "drug raid",
    "opium", "opioid", "heroin", "morphine", "cocaine", "crack cocaine",
    "cannabis", "marijuana", "marihuana", "hashish", "hash", "weed",
    "cannabis oil", "cannabis resin",
    "methamphetamine", "meth", "crystal meth", "ice", "amphetamine", "speed",
    "caffeine sodium benzoate", "sodium benzoate caffeine", "annaka",
    "tramadol", "oxycodone", "codeine",
    "MDMA", "ecstasy", "molly", "ketamine", "LSD", "psilocybin", "magic mushroom",
    "addiction", "addict", "rehabilitation", "rehab", "overdose",
]

# ========== 英语：新型 / NPS / 合成 ==========
EN_NOVEL = [
    "new psychoactive substance", "NPS", "designer drug", "research chemical",
    "synthetic cannabinoid", "spice", "K2", "synthetic cathinone", "bath salts",
    "HHC", "hexahydrocannabinol", "Delta-8", "Delta-8 THC", "delta-8-THC",
    "fentanyl", "fentanyl analogue", "fentanyl derivative", "carfentanil",
    "nitazene", "isotonitazene", "protonitazene", "metonitazene",
    "orfina", "orphine", "oripavine",
    "xylazine", "tranq", "tranq dope",
    "mephedrone", "4-MMC", "methylone", "MDPV", "alpha-PVP", "flakka",
    "party drug", "happy water", "mixed powder", "liquid NPS", "liquid psychoactive",
    "GHB", "GBL", "1,4-butanediol", "Rohypnol", "flunitrazepam",
    "diazepam", "alprazolam", "benzodiazepine",
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
    "марихуана", "гашиш", "метамфетамин", "амфетамин", "экстази", "фентанил",
    "нитазен", "изотонитазен", "трамадол", "оксикодон", "псилоцибин",
    "синтетический каннабиноид", "катинон", "МДПВ", "бензодиазепин",
    "синтетический", "психоактивн", "реабилитация",
    # 口岸/跨境长尾 + 俄蒙交界
    "Замын-Ууд", "Гашуунсухайт", "Эрлянь", "китайско-монгольск",
    "таможенн", "наркоконтрабанда", "наркоторговля",
    "Чита", "Кяхта", "Забайкальск", "Забайкалье", "Маньчжурия",
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
def build_search_queries(mode: str = "full", when: str = "") -> List[dict]:
    """生成多语种、多毒品类别的搜索任务。
    mode=news：精简高频监测任务（更快）；mode=full：全量覆盖。
    when：Google News 时间窗，如 7d / 1d（会追加 when:Xd）。
    """
    tasks: List[dict] = []
    news_mode = mode == "news"
    when_suffix = f" when:{when}" if when else ""

    # —— 蒙语核心 ——
    mn_cores_news = [
        "мансууруулах бодис",
        "хар тамхи",
        "метамфетамин",
        "фентанил",
        "нитазен",
        "каннабис",
        "героин",
        "баривчилгаа мансууруулах",
        "гааль мансууруулах",
        "Замын-Үүд мансууруулах",
        "хил мансууруулах",
    ]
    mn_cores_full = [
        "мансууруулах бодис",
        "хар тамхи",
        "метамфетамин",
        "героин",
        "каннабис",
        "гашиш",
        "кокаин",
        "кетамин",
        "фентанил",
        "нитазен",
        "изотонитазен",
        "синтетик каннабиноид",
        "псилоцибин",
        "катинон",
        "трамадол",
        "синтетик мансууруулах",
        "прекурсор",
        "баривчилгаа мансууруулах",
        "гааль мансууруулах",
        "цагдаа хар тамхи",
        "Замын-Үүд мансууруулах",
        "Гашуунсухайт мансууруулах",
        "хил нэвтрүүлэх мансууруулах",
    ]
    for q in (mn_cores_news if news_mode else mn_cores_full):
        tasks.append({
            "system_id": 8,
            "system_name": "全国媒体与公开资讯",
            "org_name": f"搜索·蒙语·{q[:18]}",
            "query": f"Монгол ({q}){when_suffix}",
            "hl": "mn",
            "gl": "mn",
            "ceid": "MN:mn",
            "engine": "google_news",
            "require_mongolia": False,
            "tier": "news" if news_mode else "full",
        })

    # —— 英语：蒙古 + 明确毒品品名 ——
    en_news = [
        "narcotic OR \"illegal drug\" OR \"drug trafficking\" OR \"drug smuggling\"",
        "methamphetamine OR \"crystal meth\"",
        "fentanyl OR nitazene OR isotonitazene",
        "cannabis OR marijuana OR \"synthetic cannabinoid\"",
        "heroin OR ketamine OR MDMA",
        "\"drug seizure\" OR \"drug bust\" OR \"drugs seized\"",
        "\"Zamyn-Uud\" OR \"Gashuun Sukhait\" OR Erenhot (drug OR narcotic OR seizure)",
        "\"China-Mongolia\" OR \"Sino-Mongolian\" (border OR customs) (drug OR narcotic)",
    ]
    en_full = [
        "narcotic OR \"illegal drug\" OR \"illicit drug\" OR \"drug trafficking\" OR \"drug smuggling\"",
        "methamphetamine OR \"crystal meth\" OR \"ice meth\"",
        "heroin OR opium",
        "cannabis OR marijuana OR hashish OR \"cannabis oil\"",
        "\"caffeine sodium benzoate\" OR annaka",
        "cocaine",
        "tramadol OR oxycodone OR morphine OR codeine",
        "fentanyl OR \"fentanyl analogue\" OR nitazene OR isotonitazene OR metonitazene",
        "HHC OR \"Delta-8\" OR \"synthetic cannabinoid\" OR spice OR K2",
        "psilocybin OR \"magic mushroom\"",
        "MDPV OR \"bath salts\" OR cathinone OR mephedrone",
        "ketamine OR MDMA OR ecstasy",
        "diazepam OR alprazolam OR benzodiazepine",
        "\"designer drug\" OR NPS OR \"liquid NPS\" OR \"party drug\"",
        "precursor OR ephedrine OR pseudoephedrine",
        "\"drug seizure\" OR \"drugs seized\" OR \"drug bust\"",
        "\"Zamyn-Uud\" OR Gashuun OR Erenhot (narcotic OR meth OR fentanyl OR seizure)",
        "\"China Mongolia border\" OR \"Sino-Mongolian\" (drug OR trafficking OR customs)",
    ]
    for g in (en_news if news_mode else en_full):
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
            "tier": "news" if news_mode else "full",
        })

    # —— 中文：蒙古国 + 毒品 ——
    zh_news = [
        "毒品 OR 缉毒 OR 禁毒 OR 贩毒",
        "冰毒 OR 芬太尼 OR 尼秦 OR 海洛因 OR 大麻",
        "合成大麻素 OR 安纳咖 OR 氯胺酮",
        "口岸查获 OR 跨境贩毒 OR 走私毒品",
        # 地域+毒品组合（扩大检索基数）
        "扎门乌德 OR 甘其毛都 OR 二连浩特 (毒品 OR 缉毒 OR 查获)",
        "中蒙口岸 OR 中蒙边境 (贩毒 OR 走私 OR 缉毒)",
        "蒙古国 (易制毒 OR 麻精 OR 新型毒品 OR 安纳咖)",
    ]
    zh_full = [
        "毒品 OR 缉毒 OR 禁毒 OR 贩毒",
        "冰毒 OR 冰块 OR 海洛因 OR 大麻 OR 黑烟草 OR 可卡因",
        "安纳咖 OR 苯甲酸钠咖啡因",
        "曲马多 OR 羟考酮 OR 吗啡 OR 可待因",
        "芬太尼 OR 尼秦 OR 异托尼他秦 OR 奥芬",
        "合成大麻素 OR 香料毒 OR HHC OR Delta-8",
        "裸盖菇素 OR 迷幻蘑菇 OR 卡西酮 OR 浴盐 OR MDPV",
        "快乐水 OR 派对毒品 OR 液态新型精神药物 OR 情绪舒缓液",
        "安定 OR 阿普唑仑 OR 苯二氮卓",
        "氯胺酮 OR 摇头丸 OR 新型毒品",
        "易制毒 OR 麻精 OR 制毒",
        "口岸查获 OR 跨境贩毒 OR 走私毒品",
        "扎门乌德 (毒品 OR 缉毒 OR 查获 OR 走私)",
        "甘其毛都 (毒品 OR 缉毒 OR 查获 OR 走私)",
        "二连浩特 (毒品 OR 缉毒 OR 查获)",
        "中蒙口岸 OR 中蒙边境 (缉毒 OR 贩毒 OR 安纳咖 OR 芬太尼)",
        "蒙古国 (尼秦 OR 异托尼他秦 OR 合成大麻素 OR 安纳咖)",
    ]
    for g in (zh_news if news_mode else zh_full):
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
            "tier": "news" if news_mode else "full",
        })

    # —— 媒体站内搜索（可打开原文）——
    site_queries_full = [
        "мансууруулах",
        "хар тамхи",
        "метамфетамин",
        "героин",
        "каннабис",
        "фентанил",
        "нитазен",
        "баривчилгаа",
    ]
    site_queries_news = [
        "мансууруулах",
        "хар тамхи",
        "метамфетамин",
        "фентанил",
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
        {
            "org_name": "News.mn站内搜索",
            "template": "https://news.mn/search?q={q}",
            "system_id": 8,
        },
    ]
    for site in site_engines:
        for q in (site_queries_news if news_mode else site_queries_full):
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
                "require_mongolia": False,
                "tier": "news" if news_mode else "full",
            })

    # 检索降噪：统一追加负面排除与蒙古锚点
    for _i, _task in enumerate(tasks):
        if _task.get("query"):
            _task["query"] = _finalize_query(_task["query"], bind_mongolia=bool(_task.get("require_mongolia", True)))
        tasks[_i] = _task

    # —— 全球主流媒体 + 国际禁毒机构 ——
    from config.global_media import build_global_search_queries

    tasks.extend(build_global_search_queries(mode=mode, when=when))

    # 修改原因：论坛任务不在此批量生成；仅 search_feeds 在 enable_forum_search=true 时追加

    for _i, _task in enumerate(tasks):
        if _task.get("query") and "site:" not in (_task.get("search_url") or ""):
            if _task.get("engine") != "site_search":
                _task["query"] = _finalize_query(_task["query"], bind_mongolia=bool(_task.get("require_mongolia", True)))
        tasks[_i] = _task
    return tasks


# 告警级关键词（命中即提高等级）
ALERT_KEYWORDS = [
    "专项行动", "跨境缉毒", "口岸严查", "大规模查获", "缉毒大案",
    "fentanyl", "nitazene", "isotonitazene", "metonitazene", "xylazine",
    "seizure", "seized",
    "баривчилгаа", "тусгай ажиллагаа", "фентанил", "метамфетамин", "нитазен",
    "芬太尼", "尼秦", "异托尼他秦", "奥芬", "冰毒", "冰块", "海洛因",
    "安纳咖", "合成大麻素", "香料毒", "快乐水", "液态新型精神药物", "易制毒",
]


def _finalize_query(q: str, *, bind_mongolia: bool = True) -> str:
    """检索降噪：强制高精准地域锚点 + 负面排除（弱化宽泛 Mongolia 单关键词）。"""
    q = (q or '').strip()
    if bind_mongolia:
        low = q.lower()
        precise = (
            'ulaanbaatar', 'улаанбаатар', '乌兰巴托',
            '扎门', 'zamyn', 'zamiin', '甘其毛都', 'gashuun',
            '蒙古国', 'монгол улс',
        )
        if not any(x in low for x in precise):
            # 修改原因：强制绑定口岸/首都锚点，减少全球无关毒品新闻
            q = (
                f'(Ulaanbaatar OR "乌兰巴托" OR "扎门乌德" OR Zamyn-Uud OR '
                f'"甘其毛都" OR "Gashuun Sukhait" OR "蒙古国" OR "Монгол Улс") ({q})'
            )
    if SEARCH_NEGATIVE_EXCLUDE.strip() not in q:
        q = q + SEARCH_NEGATIVE_EXCLUDE
    return q.strip()
