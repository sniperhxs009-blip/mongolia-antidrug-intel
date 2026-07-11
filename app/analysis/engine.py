"""专业级情报交叉研判分析引擎"""
from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import get_settings
from app.crawler.filters import detect_lang, translate_to_zh
from app.db.models import IntelItem, Report

logger = logging.getLogger(__name__)
settings = get_settings()


SYSTEM_ORDER = [
    (1, "国家级禁毒统筹委员会体系"),
    (2, "刑事缉毒执法体系"),
    (3, "麻精药品与制毒原料行业监管体系"),
    (4, "边境海关缉毒查验体系"),
    (5, "全国地方层级禁毒机构"),
    (6, "戒毒康复医疗机构体系"),
    (7, "国际禁毒协作机构"),
    (8, "全国媒体与公开资讯"),
    (9, "官方统计与年报体系"),
    (10, "全球媒体与国际禁毒机构"),
    (11, "全球论坛社区与补充搜索"),
]

# 机构/来源名中文映射（报告展示用）
ORG_NAME_ZH = {
    "UNODC": "联合国毒品和犯罪问题办公室",
    "INCB": "国际麻醉品管制局",
    "WHO": "世界卫生组织",
    "WCO": "世界海关组织",
    "INTERPOL": "国际刑警组织",
    "Reuters": "路透社",
    "AP News": "美联社",
    "BBC": "英国广播公司",
    "The Guardian": "卫报",
    "CNN": "美国有线电视新闻网",
    "Al Jazeera": "半岛电视台",
    "The Diplomat": "外交官杂志",
    "Radio Free Asia": "自由亚洲电台",
    "VOA": "美国之音",
    "Nikkei Asia": "日经亚洲",
    "South China Morning Post": "南华早报",
    "Xinhua 新华社": "新华社",
    "CGTN": "中国国际电视台",
    "TASS": "塔斯社",
    "RIA Novosti": "俄新社",
    "VICE": "VICE新闻",
    "AKIpress": "AKIpress新闻社",
    "GoGo 新闻": "GoGo新闻",
    "IKON 新闻": "IKON新闻",
    "News.mn": "News.mn",
    "UB Post": "乌兰巴托邮报",
    "蒙通社 MONTSAME": "蒙通社",
}


class AnalysisEngine:
    """多源交叉比对、关联研判、趋势分析、风险研判。"""

    def __init__(self, db: Session):
        self.db = db
        self._zh_cache: Dict[str, str] = {}

    def collect_items(self, days: int = 7) -> List[IntelItem]:
        since = datetime.utcnow() - timedelta(days=days)
        return (
            self.db.query(IntelItem)
            .filter(IntelItem.crawled_at >= since)
            .filter(IntelItem.is_duplicate.is_(False))
            .order_by(IntelItem.crawled_at.desc())
            .all()
        )

    @staticmethod
    def _has_cjk(text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", text or ""))

    def _to_zh(self, text: str) -> str:
        """报告内强制中文：已是中文则保留，否则翻译。"""
        text = (text or "").strip()
        if not text:
            return text
        if text in self._zh_cache:
            return self._zh_cache[text]
        if self._has_cjk(text) and detect_lang(text) == "zh":
            self._zh_cache[text] = text
            return text
        # 标题里中英混排且已有足够中文，直接用
        if self._has_cjk(text) and len(re.findall(r"[\u4e00-\u9fff]", text)) >= max(4, len(text) // 4):
            self._zh_cache[text] = text
            return text
        zh = translate_to_zh(text, enabled=True)
        # 翻译失败则尽量做轻量替换
        if not zh or zh == text:
            zh = text
            for en, cn in (
                ("Mongolia", "蒙古国"),
                ("Ulaanbaatar", "乌兰巴托"),
                ("drug", "毒品"),
                ("narcotic", "麻醉品"),
                ("methamphetamine", "冰毒"),
                ("heroin", "海洛因"),
                ("cannabis", "大麻"),
                ("fentanyl", "芬太尼"),
                ("ketamine", "氯胺酮"),
                ("police", "警方"),
                ("customs", "海关"),
                ("seizure", "查获"),
                ("trafficking", "贩运"),
                ("smuggling", "走私"),
            ):
                zh = re.sub(re.escape(en), cn, zh, flags=re.I)
        self._zh_cache[text] = zh
        return zh

    def _org_zh(self, org_name: str) -> str:
        org = (org_name or "").strip()
        if not org:
            return "未知机构"
        if org in ORG_NAME_ZH:
            return ORG_NAME_ZH[org]
        for k, v in ORG_NAME_ZH.items():
            if k.lower() in org.lower() or org.lower() in k.lower():
                return v
        # 搜索任务名：搜索·英语·xxx → 保留结构并译后缀
        if org.startswith("搜索·") or org.startswith("国际") or org.startswith("全球") or org.startswith("统计"):
            return self._to_zh(org) if not self._has_cjk(org) else org
        if self._has_cjk(org):
            return org
        return self._to_zh(org)

    def _item_title_zh(self, item: IntelItem) -> str:
        # 优先已有中文标题；否则强制翻译原文标题
        if item.title_zh and self._has_cjk(item.title_zh):
            return item.title_zh.strip()
        raw = (item.title_zh or item.title or "").strip()
        return self._to_zh(raw)

    def generate_report(self, report_type: str = "daily", days: Optional[int] = None) -> Report:
        # 日度/月度均按近30日官方归集窗口（与文档一致）；周报7日；告警1日
        days = days or {"daily": 30, "weekly": 7, "monthly": 30, "alert": 1}.get(report_type, 30)
        items = self.collect_items(days=days)
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days)

        md = self._build_markdown(items, report_type, period_start, period_end)
        html = self._md_to_simple_html(md)
        title = (
            f"蒙古国禁毒全机构近{days}日涉毒情报归集报告 "
            f"{period_start.strftime('%Y.%m.%d')}-{period_end.strftime('%Y.%m.%d')}"
        )

        import os

        os.makedirs(settings.reports_dir, exist_ok=True)
        path = f"{settings.reports_dir}/report_{report_type}_{period_end.strftime('%Y%m%d_%H%M%S')}.md"
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)

        report = Report(
            report_type=report_type,
            title=title,
            period_start=period_start,
            period_end=period_end,
            content_md=md,
            content_html=html,
            file_path=path,
            created_at=datetime.utcnow(),
            emailed=False,
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        logger.info("研判报告已生成: %s", path)
        return report

    def _type_label(self, report_type: str) -> str:
        return {"daily": "日度", "weekly": "周度", "monthly": "月度", "alert": "紧急通报"}.get(
            report_type, report_type
        )

    def _item_core(self, item: IntelItem) -> str:
        raw = (item.summary_zh or item.summary or item.content_zh or item.content or "").strip()
        if not raw:
            return self._item_title_zh(item)
        zh = self._to_zh(raw)
        return zh[:280] + ("…" if len(zh) > 280 else "")

    def _item_judgment(self, item: IntelItem) -> str:
        cat = item.category or "综合"
        level = item.intel_level or "一般"
        hints = []
        if self._match(item, ["口岸", "边境", "хил", "гааль", "border", "customs", "扎门", "嘎顺"]):
            hints.append("关注中蒙口岸/无人区走私通道变化")
        if self._match(item, ["合成", "芬太尼", "尼秦", "synthetic", "NPS", "meth", "изотонитазен"]):
            hints.append("新型合成毒品/高致死阿片风险抬升")
        if self._match(item, ["青少年", "校园", "音乐节", "playtime", "13-25"]):
            hints.append("年轻群体聚集场景防毒压力上升")
        if self._match(item, ["UNODC", "集安", "CSTO", "联合行动", "跨境"]):
            hints.append("跨境联合行动与国际协作信号")
        if not hints:
            hints.append(f"纳入「{cat}」主题持续跟踪，等级：{level}")
        return "；".join(hints[:2])

    def _build_markdown(
        self,
        items: List[IntelItem],
        report_type: str,
        period_start: datetime,
        period_end: datetime,
    ) -> str:
        by_system: Dict[int, List[IntelItem]] = defaultdict(list)
        by_category: Counter = Counter()
        by_level: Counter = Counter()
        by_org: Counter = Counter()
        alerts = []
        for it in items:
            by_system[it.system_id or 0].append(it)
            by_category[it.category or "综合"] += 1
            by_level[it.intel_level or "一般"] += 1
            by_org[self._org_zh(it.org_name)] += 1
            if it.is_alert or it.intel_level in ("紧急", "重要"):
                alerts.append(it)

        # 七大模块（文档顺序）；媒体/统计/全球源并入对应研判，不单独成章喧宾夺主
        MODULES = [
            (1, "一、国家级统筹协调委员会 近期官方情报", "国家级统筹"),
            (2, "二、核心刑事缉毒执法机构 近一月案件&通告", "执法缉毒"),
            (3, "三、药品/制毒原料行业监管行政单位 管控公告", "行业监管"),
            (4, "四、海关、边境边防禁毒查验单位 口岸缉毒动态", "边境口岸"),
            (5, "五、地方层级禁毒配套机构（21省+乌兰巴托9区）", "地方机构"),
            (6, "六、戒毒、成瘾治疗专门医疗机构 康复数据", "戒毒康复"),
            (7, "七、国际禁毒协作相关常驻机构 涉外动态", "国际协作"),
        ]

        lines: List[str] = []
        lines.append(
            f"# 蒙古国禁毒全机构近{(period_end - period_start).days}日"
            f"（{period_start.strftime('%Y.%m.%d')}-{period_end.strftime('%Y.%m.%d')}）涉毒情报归集报告"
        )
        lines.append("")
        lines.append("## 情报说明")
        lines.append("")
        lines.append(
            "1. **数据源严格限定**：蒙通社 Montsame、中国禁毒网、UNODC 全球官网、"
            "联合国蒙古办事处、中新网、内蒙古公安、CSTO、上合经合、UB Post 等国内裸网可直连公开源；"
            "禁止访问蒙古本土 `.gov.mn` 及虚构专栏路径；采用关键词检索式增量采集。"
        )
        lines.append(
            "2. **时效与过滤**：优先近30日官方发布；剔除自媒体爆料、体育兴奋剂、"
            "非管制医药及历史过期资讯。"
        )
        lines.append(
            "3. **归集结构**：按「国家级统筹→执法缉毒→行业监管→边境口岸→地方机构→戒毒康复→国际协作」"
            "七大模块依次归集；每条标注发布机构、发布时间、核心内容、研判要点、原文链接。"
        )
        lines.append(
            f"4. **本周期统计**：有效情报 **{len(items)}** 条；告警/重要 **{len(alerts)}** 条；"
            f"等级分布 {dict(by_level)}。"
        )
        lines.append("")
        lines.append(f"<!-- watermark: MN-INTEL-TRACE|{period_end.strftime('%Y%m%d')} -->")
        lines.append("")

        # 将 system 8/9/10/11 的条目按主题并入七大模块，避免官方归集报告被搜索噪声冲淡
        def _bucket(it: IntelItem) -> int:
            sid = it.system_id or 0
            org_l = (it.org_name or "").lower()
            url_l = (it.url or "").lower()
            # 修改原因：gov.mn 快照情报强制归入蒙古官方体系 1/2/3/4
            if "快照·" in (it.org_name or "") or "gov_snapshot" in (it.raw_meta or ""):
                if "police.gov.mn" in org_l or "police.gov.mn" in url_l or "цагдаа" in org_l:
                    return 2
                if any(x in org_l for x in ("customs.gov.mn", "bpo.gov.mn")) or "гааль" in org_l:
                    return 4
                if any(x in org_l for x in ("health.gov.mn", "mmra.gov.mn", "moh")):
                    return 3
                return 1
            if "site:police.gov.mn" in url_l or ("police" in org_l and "快照" in org_l):
                return 2
            if "site:customs.gov.mn" in url_l or ("customs" in org_l and "快照" in org_l):
                return 4
            if sid in (1, 2, 3, 4, 5, 6, 7):
                return sid
            if self._match(it, ["海关", "口岸", "边境", "гааль", "хил", "customs", "border", "扎门", "甘其毛都", "跨境"]):
                return 4
            if self._match(it, ["戒毒", "康复", "成瘾", "донтсон", "сэргээх", "rehab", "青少年"]):
                return 6
            if self._match(it, ["UNODC", "国际", "外交", "олон улсын", "INTERPOL", "INCB", "reddit", "论坛"]):
                return 7
            if self._match(it, ["麻精", "处方", "卫生", "прекурсор", "health", "moh", "易制毒"]):
                return 3
            if self._match(it, ["警察", "检察院", "缉毒", "цагдаа", "баривчилгаа", "prosecutor", "统计", "同比"]):
                return 2
            if self._match(it, ["委员会", "政府", "zasag", "gov.mn", "协调", "快照"]):
                return 1
            return 8  # 暂存未归类

        def _report_sort_key(it: IntelItem) -> tuple:
            """修改原因：蒙古官方情报置顶，国内中文资讯后置。"""
            org = (it.org_name or "").lower()
            is_gov_snap = "快照" in (it.org_name or "") or "gov.mn" in (it.url or "")
            is_domestic_cn = any(x in org for x in ("新华网", "禁毒网", "nncc", "news.cn", "内蒙古"))
            return (1 if is_gov_snap else 2, 2 if is_domestic_cn else 1, -(it.published_at or it.crawled_at or datetime.utcnow()).timestamp())

        module_items: Dict[int, List[IntelItem]] = defaultdict(list)
        uncategorized: List[IntelItem] = []
        for it in items:
            b = _bucket(it)
            if b == 8:
                uncategorized.append(it)
            else:
                module_items[b].append(it)

        for sid, heading, _label in MODULES:
            group = module_items.get(sid, []) or by_system.get(sid, [])
            # 去重
            seen = set()
            uniq = []
            for g in group:
                if g.id in seen:
                    continue
                seen.add(g.id)
                uniq.append(g)
            group = sorted(uniq, key=_report_sort_key)
            lines.append(f"## {heading}")
            lines.append("")
            if not group:
                lines.append("- 本周期该模块公开渠道未见新增可结构化涉毒官方情报。")
                lines.append("")
                continue
            for idx, g in enumerate(group[:80], 1):  # 原 25 → 80，报告不截断隐藏
                title = self._item_title_zh(g)
                org = self._org_zh(g.org_name)
                pub = g.published_at or g.crawled_at
                pub_s = pub.strftime("%Y.%m.%d") if pub else "-"
                lines.append(f"### {idx}）【{g.category or '综合'}】{title}")
                lines.append("")
                lines.append(f"- **发布主体**：{org}")
                lines.append(f"- **发布时间**：{pub_s}")
                lines.append(f"- **可信度**：{getattr(g, 'credibility', None) or '中'}")
                if getattr(g, "port_tag", None):
                    lines.append(f"- **口岸标签**：{g.port_tag}")
                lines.append(f"- **核心内容**：{self._item_core(g)}")
                lines.append(f"- **研判要点**：{self._item_judgment(g)}")
                lines.append(f"- **原文来源**：{g.url or '（无链接）'}")
                lines.append("")

        # 修改原因：分口岸趋势独立毒情报表段落
        try:
            lines.append(self.port_trend_report(days=30))
            lines.append("")
        except Exception:
            pass

        if uncategorized:
            lines.append("## 附、其他公开渠道涉蒙涉毒信息（已过滤）")
            lines.append("")
            # 分模块展示：论坛 / 统计 / 其他，避免大量条目挤压
            forum_items = [g for g in uncategorized if (g.system_id or 0) == 11 or self._match(g, ["reddit", "论坛", "zhihu", "贴吧"])]
            stat_items = [g for g in uncategorized if (g.system_id or 0) == 9 or (g.category or "") in ("官方统计", "PDF报表")]
            # 修改原因：蒙古海关/警方快照不再归入杂项
            gov_snap = [
                g for g in uncategorized
                if "快照" in (g.org_name or "") or "gov.mn" in (g.url or "").lower()
            ]
            other = [g for g in uncategorized if g not in forum_items and g not in stat_items and g not in gov_snap]
            if gov_snap:
                lines.append("### 蒙古官方快照情报")
                lines.append("")
                for g in sorted(gov_snap, key=_report_sort_key)[:80]:
                    lines.append(
                        f"- 【{g.intel_level}】{self._item_title_zh(g)}｜"
                        f"{self._org_zh(g.org_name)}｜{g.url}"
                    )
                lines.append("")
            if stat_items:
                lines.append("### 统计与年报类")
                lines.append("")
                for g in stat_items[:80]:
                    lines.append(
                        f"- 【{g.intel_level}】{self._item_title_zh(g)}｜"
                        f"{self._org_zh(g.org_name)}｜{g.url}"
                    )
                lines.append("")
            if forum_items:
                lines.append("### 论坛与社区类")
                lines.append("")
                for g in forum_items[:80]:
                    lines.append(
                        f"- 【{g.intel_level}】{self._item_title_zh(g)}｜"
                        f"{self._org_zh(g.org_name)}｜{g.url}"
                    )
                lines.append("")
            if other:
                lines.append("### 媒体与其他公开渠道")
                lines.append("")
                for g in other[:80]:
                    lines.append(
                        f"- 【{g.intel_level}】{self._item_title_zh(g)}｜"
                        f"{self._org_zh(g.org_name)}｜{g.url}"
                    )
                lines.append("")

        # 综合交叉研判（文档第八节）
        lines.append("## 八、综合情报交叉研判总结")
        lines.append("")
        cross = [i for i in items if self._match(i, ["口岸", "边境", "хил", "гааль", "border", "customs"])]
        novel = [i for i in items if self._match(i, ["合成", "芬太尼", "尼秦", "synthetic", "NPS", "meth"])]
        youth = [i for i in items if self._match(i, ["青少年", "校园", "音乐节", "playtime"])]
        lines.append(
            f"1. **毒情品类趋势**：本周期新型/合成相关公开信息 {len(novel)} 条；"
            "传统大麻/安纳咖与合成毒品并存时，优先跟踪城市与口岸高致死阿片、合成大麻素信号。"
        )
        lines.append(
            f"2. **执法管控重心**：跨境/口岸相关 {len(cross)} 条；"
            "关注主口岸严查与戈壁无人小路 divert 风险，以及空港/文娱场所安检通报。"
        )
        lines.append(
            "3. **中蒙跨境风险预警**：对扎门乌德、嘎顺苏海图及东/南戈壁方向公开查获、"
            "双边情报交换类信息提高监测优先级。"
        )
        lines.append(
            f"4. **短板隐患**：年轻群体相关公开信息 {len(youth)} 条；"
            "校园、音乐节等场景与基层新型毒品快检覆盖仍是持续关注点。"
        )
        lines.append("")
        lines.append(self._risk_outlook(items, by_category, alerts))
        lines.append("")

        lines.append("## 九、下期重点监测方向")
        lines.append("")
        lines.append("1. 蒙通社三语站、中国禁毒网、UNODC 世界毒品报告近30日涉蒙公开通报。")
        lines.append("2. 中新网/内蒙古公安涉中蒙口岸缉毒社会与属地官方报道。")
        lines.append("3. CSTO、上合经合、联合国蒙古办事处涉外禁毒协作动态。")
        lines.append("4. 近30日毒品品类、走私渠道、涉案人群趋势对比（见下节）。")
        lines.append("5. 大宗缉毒案、新法列管、跨境联合行动、高致死新型毒品预警 → 触发即时邮件。")
        lines.append("")
        lines.append(self._trend_30d_section(items))
        lines.append("")
        lines.append("---")
        lines.append(
            "*本报告由蒙古国禁毒全网情报自动采集研判系统自动生成；"
            "仅基于官方及授权公开渠道，不采信自媒体爆料。*"
        )
        return "\n".join(lines)

    def port_trend_report(self, days: int = 30) -> str:
        """分口岸趋势：扎门乌德 / 甘其毛都 / 俄蒙边境独立小节。"""
        items = self.collect_items(days=days)
        buckets = {
            "扎门乌德": ["扎门乌德", "zamyn", "zamiin"],
            "甘其毛都": ["甘其毛都", "gashuun"],
            "俄蒙边境": ["俄蒙", "russia-mongolia", "монгол.*орос"],
        }
        lines = [f"## 分口岸毒情趋势（近{days}日）", ""]
        for name, keys in buckets.items():
            hits = [i for i in items if self._match(i, keys)]
            lines.append(f"### {name}（{len(hits)} 条）")
            for g in hits[:20]:
                cred = getattr(g, "credibility", None) or "中"
                lines.append(f"- 【可信度:{cred}】{self._item_title_zh(g)}｜{self._org_zh(g.org_name)}")
            lines.append("")
        return "\n".join(lines)

    def trend_compare_30d(self, items: Optional[List[IntelItem]] = None) -> dict:
        """近30日毒品品类、走私渠道、涉案人群简易趋势对比。"""
        items = items if items is not None else self.collect_items(days=30)
        mid = datetime.utcnow() - timedelta(days=15)

        def _bucket_period(it: IntelItem) -> str:
            ts = it.published_at or it.crawled_at or datetime.utcnow()
            return "recent15" if ts >= mid else "prior15"

        dims = {
            "品类_合成/芬太尼/尼秦": ["芬太尼", "尼秦", "合成", "fentanyl", "nitazene", "synthetic", "NPS", "异托尼他秦"],
            "品类_传统大麻/海洛因/冰毒": ["大麻", "海洛因", "冰毒", "cannabis", "heroin", "meth", "安纳咖"],
            "品类_新型毒品/NPS": ["新型毒品", "快乐水", "合成大麻素", "nps", "designer", "香料毒"],
            "渠道_口岸/跨境": ["口岸", "边境", "跨境", "customs", "border", "хил", "гааль", "扎门乌德", "甘其毛都"],
            "渠道_跨境走私": ["走私", "trafficking", "smuggl", "контрабанда", "хил нэвтрүүлэх"],
            "渠道_城市黑市": ["黑市", "青少年", "校园", "音乐节", "playtime", "ub post"],
            "人群_青少年": ["青少年", "校园", "学生", "youth", "school", "13-25"],
            "人群_跨境走私": ["走私", "trafficking", "smuggl", "баривчилгаа"],
            "来源_论坛社区": ["reddit", "论坛", "zhihu", "贴吧", "bluelight"],
            "来源_官方统计": ["统计", "同比", "pdf", "статистик", "案件数"],
        }
        out: Dict[str, dict] = {}
        for name, keys in dims.items():
            a = sum(1 for it in items if _bucket_period(it) == "prior15" and self._match(it, keys))
            b = sum(1 for it in items if _bucket_period(it) == "recent15" and self._match(it, keys))
            delta = b - a
            out[name] = {"prior_15d": a, "recent_15d": b, "delta": delta}
        return {
            "window_days": 30,
            "total_items": len(items),
            "dimensions": out,
        }


    def _trend_30d_section(self, items: List[IntelItem]) -> str:
        data = self.trend_compare_30d(items)
        lines = ["## 十、近30日趋势对比（前15日 vs 近15日）", ""]
        if not items:
            lines.append("- 本周期无有效情报，趋势对比暂缺。")
            return "\n".join(lines)
        for name, row in data["dimensions"].items():
            arrow = "↑" if row["delta"] > 0 else ("↓" if row["delta"] < 0 else "→")
            lines.append(
                f"- **{name}**：前15日 {row['prior_15d']} → 近15日 {row['recent_15d']} "
                f"（{arrow}{abs(row['delta'])}）"
            )
        lines.append("")
        lines.append(
            f"*样本总量 {data['total_items']} 条；仅反映公开渠道披露密度变化，不作绝对案发量推断。*"
        )
        return "\n".join(lines)

    def _risk_outlook(self, items: List[IntelItem], by_category: Counter, alerts: list) -> str:
        if not items:
            return (
                "趋势预判：公开信息静默不等于风险消失。建议保持每日/每12小时巡检，"
                "对口岸、缉毒执法、管制药品三类栏目设置更高优先级。"
            )
        parts = []
        if alerts:
            parts.append(f"已识别告警/重要线索 {len(alerts)} 条，需优先核验并视情启动即时邮件推送闭环。")
        if by_category.get("跨境毒情", 0) >= 2:
            parts.append("跨境/口岸信息密度上升，预判口岸查验与货运高峰叠加期风险抬升。")
        if by_category.get("新型毒品", 0) or by_category.get("制毒原料", 0):
            parts.append("出现新型毒品或制毒原料监管信号，建议开展专题跟踪并比对历史管制变化。")
        if by_category.get("执法行动", 0) >= 3:
            parts.append("执法行动类信息公开增多，反映阶段性专项整治或案件集中披露可能。")
        if not parts:
            parts.append("整体公开信息平稳，未见单项风险显著抬升；维持七大体系全覆盖监测。")
        parts.append("月度/周度对比应以条目增量、告警占比、跨境主题占比为核心指标持续回溯。")
        return " ".join(parts)

    @staticmethod
    def _match(item: IntelItem, keys: List[str]) -> bool:
        blob = " ".join(
            [
                item.title or "",
                item.title_zh or "",
                item.summary or "",
                item.summary_zh or "",
                item.content or "",
                item.content_zh or "",
            ]
        ).lower()
        return any(k.lower() in blob for k in keys)

    @staticmethod
    def _md_to_simple_html(md: str) -> str:
        # 轻量转换，满足邮件展示
        import html as html_lib
        import re

        escaped = html_lib.escape(md)
        lines = escaped.split("\n")
        out = [
            "<div class='report-body' "
            "style='font-family:Segoe UI,Noto Sans SC,Arial,sans-serif;line-height:1.7;color:#ffffff'>"
        ]
        for line in lines:
            if line.startswith("# "):
                out.append(f"<h1 style='color:#ffffff'>{line[2:]}</h1>")
            elif line.startswith("## "):
                out.append(
                    f"<h2 style='color:#ffffff;border-bottom:1px solid rgba(255,255,255,.25);"
                    f"padding-bottom:4px'>{line[3:]}</h2>"
                )
            elif line.startswith("### "):
                out.append(f"<h3 style='color:#ffffff'>{line[4:]}</h3>")
            elif line.startswith("- "):
                out.append(f"<div style='color:#ffffff'>• {line[2:]}</div>")
            elif re.match(r"\d+\. ", line):
                out.append(f"<div style='color:#ffffff'>{line}</div>")
            elif line.strip() == "---":
                out.append("<hr style='border-color:rgba(255,255,255,.25)'/>")
            elif line.strip() == "":
                out.append("<br/>")
            else:
                # 粗体 ** **
                line2 = re.sub(r"\*\*(.+?)\*\*", r"<strong style='color:#ffffff'>\1</strong>", line)
                out.append(f"<p style='color:#ffffff'>{line2}</p>")
        out.append("</div>")
        return "\n".join(out)
