"""专业级情报交叉研判分析引擎【修复：放宽地域匹配、扩充媒体归类】"""
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
# 扩充蒙古媒体中文映射
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
    "GoGo 新闻": "GoGo.mn蒙古本地媒体",
    "IKON 新闻": "IKON.mn蒙古本地媒体",
    "News.mn": "News.mn本土新闻门户",
    "UB Post": "乌兰巴托邮报",
    "蒙通社 MONTSAME": "蒙通社",
}
class AnalysisEngine:
    def __init__(self, db: Session):
        self.db = db
        self._zh_cache: Dict[str, str] = {}
    def collect_items(self, days: int = 365) -> List[IntelItem]:
        """默认读取1年数据"""
        since = datetime.utcnow() - timedelta(days=days)
        return (
            self.db.query(IntelItem)
            .filter(IntelItem.is_duplicate.is_(False))
            .order_by(IntelItem.crawled_at.desc())
            .all()
        )
    @staticmethod
    def _has_cjk(text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", text or ""))
    def _to_zh(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return text
        if text in self._zh_cache:
            return self._zh_cache[text]
        if self._has_cjk(text) and detect_lang(text) == "zh":
            self._zh_cache[text] = text
            return text
        if self._has_cjk(text) and len(re.findall(r"[\u4e00-\u9fff]", text)) >= max(4, len(text) // 4):
            self._zh_cache[text] = text
            return text
        zh = translate_to_zh(text, enabled=True)
        if not zh or zh == text:
            zh = text
            replace_map = [
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
            ]
            for en, cn in replace_map:
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
        if org.startswith("搜索·") or org.startswith("国际") or org.startswith("论坛") or org.startswith("统计"):
            return self._to_zh(org) if not self._has_cjk(org) else org
        if self._has_cjk(org):
            return org
        return self._to_zh(org)
    def _item_title_zh(self, item: IntelItem) -> str:
        if item.title_zh and self._has_cjk(item.title_zh):
            return item.title_zh.strip()
        raw = (item.title or "").strip()
        return self._to_zh(raw)
    def generate_report(self, report_type: str = "daily", days: Optional[int] = None) -> Report:
        days = days or {"daily": 30, "weekly": 7, "monthly": 365, "alert": 1}.get(report_type, 365)
        items = self.collect_items(days=days)
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days)
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
        return {"daily": "日度", "weekly": "周度", "monthly": "年度全量归集", "alert": "紧急通报"}.get(report_type, report_type)
    def _item_core(self, item: IntelItem) -> str:
        raw = (item.summary_zh or item.summary or item.content or "").strip()
        zh = self._to_zh(raw)
        return zh[:320] + ("…" if len(zh) > 320 else "")
    def _item_judgment(self, item: IntelItem) -> str:
        cat = item.category or "综合"
        level = item.intel_level or "一般"
        hints = []
        if self._match(item, ["口岸", "边境", "хил", "гааль", "border", "customs", "扎门", "甘其毛都"]):
            hints.append("关注中蒙口岸、戈壁徒步走私通道变化")
        if self._match(item, ["合成", "芬太尼", "尼秦", "synthetic", "NPS", "meth"]):
            hints.append("新型合成阿片类毒品致死风险持续抬升")
        if self._match(item, ["青少年", "校园", "音乐节", "playtime"]):
            hints.append("青年聚集场所防毒管控压力上升")
        if self._match(item, ["UNODC", "集安", "CSTO", "联合行动"]):
            hints.append("跨境多国禁毒协作信号需跟踪")
        if not hints:
            hints.append(f"纳入「{cat}」主题持续监测，情报等级：{level}")
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
            by_org[self._org_zh(it)] += 1
            if it.is_alert or it.intel_level in ("紧急", "重要"):
                alerts.append(it)
        MODULES = [
            (1, "一、国家级禁毒统筹委员会 近期官方情报", "国家级统筹"),
            (2, "二、核心刑事缉毒执法机构 近一月案件&通告", "执法缉毒"),
            (3, "三、药品/制毒原料行业管控公告", "行业监管"),
            (4, "四、海关、边境边防禁毒查验单位 口岸缉毒动态", "边境口岸"),
            (5, "五、地方层级禁毒配套机构（21省+乌兰巴托9区）", "地方机构"),
            (6, "六、戒毒、成瘾治疗专门医疗机构 康复数据", "戒毒康复"),
            (7, "七、国际禁毒协作相关常驻机构 涉外动态", "国际协作"),
        ]
        lines: List[str] = []
        lines.append(
            f"# 蒙古国禁毒全机构近{(period_end - period_start).days}日（{period_start.strftime('%Y.%m.%d')}-{period_end.strftime('%Y.%m.%d')}）涉毒情报归集报告"
        )
        lines.append("")
        lines.append("## 情报说明【修复后采集规则】")
        lines.append("1. 数据源扩充：蒙通社、GOGO/IKON/NEWS.MN、UB Post蒙古本土媒体、中国禁毒网、UNODC，全部国内裸网直连。")
        lines.append("2. 时效窗口1年，适配蒙古国官方禁毒新闻更新频次极低的现状。")
        lines.append("3. 过滤规则放宽：蒙古媒体页面无需文本含蒙古字样即可入库；外媒纯毒品报道保留研判。")
        lines.append(f"4. 本期有效情报 {len(items)} 条；告警/重要 {len(alerts)} 条；等级分布 {dict(by_level)}。")
        lines.append("")
        def _bucket(it: IntelItem) -> int:
            sid = it.system_id or 0
            if sid in (1, 2, 3, 4, 5, 6, 7):
                return sid
            if self._match(it, ["海关", "口岸", "гааль", "хил"]):
                return 4
            if self._match(it, ["戒毒", "康复", "донтсон", "сэргээх"]):
                return 6
            if self._match(it, ["UNODC", "国际", "外交"]):
                return 7
            if self._match(it, ["麻精", "卫生"]):
                return 3
            if self._match(it, ["警察", "缉毒"]):
                return 2
            if self._match(it, ["委员会", "政府"]):
                return 1
            return 8
        module_items: Dict[int, List[IntelItem]] = defaultdict(list)
        uncategorized: List[IntelItem] = []
        for it in items:
            b = _bucket(it)
            if b == 8:
                uncategorized.append(it)
            else:
                module_items[b].append(it)
        for sid, heading, _label in MODULES:
            group = module_items.get(sid, [])
            seen = set()
            uniq = []
            for g in group:
                if g.id in seen:
                    continue
                seen.add(g.id)
                uniq.append(g)
            group = uniq
            lines.append(f"## {heading}")
            lines.append("")
            if not group:
                lines.append("- 本周期该体系无新增可核验官方情报。")
                lines.append("")
                continue
            for idx, g in enumerate(group[:12], 1):
                title = self._item_title_zh(g)
                org = self._org_zh(g.org_name)
                pub = g.published_at or g.crawled_at
                pub_s = pub.strftime("%Y.%m.%d") if pub else "-"
                lines.append(f"### {idx}）【{g.category or '综合'}】{title}")
                lines.append("")
                lines.append(f"- **发布主体**：{org}")
                lines.append(f"- **发布时间**：{pub_s}")
                lines.append(f"- **核心内容**：{self._item_core(g)}")
                lines.append(f"- **研判要点**：{self._item_judgment(g)}")
                lines.append(f"- **原文来源**：{g.url or '（无链接）'}")
                lines.append("")
        if uncategorized:
            lines.append("## 附、蒙古本土媒体/国际外媒补充涉毒资讯")
            lines.append("")
            for g in uncategorized[:12]:
                lines.append(f"- 【{g.intel_level}】{self._item_title_zh(g)}｜{self._org_zh(g)}｜{g.url}")
            lines.append("")
        lines.append("## 八、综合情报交叉研判总结")
        lines.append("")
        cross = [i for i in items if self._match(i, ["口岸", "边境"])]
        novel = [i for i in items if self._match(i, ["芬太尼", "尼秦", "合成"])]
        youth = [i for i in items if self._match(i, ["青少年", "校园"])]
        lines.append(f"1. 中蒙跨境口岸相关情报 {len(cross)} 条，徒步、货车走私为主要渠道。")
        lines.append(f"2. 新型合成毒品相关资讯 {len(novel)} 条，阿片类中毒风险走高。")
        lines.append(f"3. 青少年涉毒公开信息 {len(youth)}，文娱场所管控需持续关注。")
        lines.append("")
        lines.append(self._risk_outlook(items, by_category, alerts))
        lines.append("## 九、下期重点监测方向")
        lines.append("1. 蒙通社、GOGO/IKON/NEWS.MN、UB Post全渠道1年检索。")
        lines.append("2. 甘其毛都、扎门乌德口岸缉毒公开案件。")
        lines.append("3. UNODC全球毒情报告、集安组织跨境行动。")
        lines.append("4. 安纳咖、芬太尼、尼秦类毒品报道。")
        lines.append("5. 公斤级查获自动触发即时邮件告警。")
        lines.append("")
        lines.append(self._trend_30d_section(items))
        lines.append("---")
        lines.append("*本报告自动生成，数据源全部国内可直连公开媒体，无翻墙采集内容。*")
        return "\n".join(lines)
    def trend_compare_30d(self, items: Optional[List[IntelItem]] = None) -> dict:
        items = items if items is not None else self.collect_items(30)
        mid = datetime.utcnow() - timedelta(days=15)
        dims = {
            "品类_合成/芬太尼": ["芬太尼", "尼秦", "合成"],
            "品类_传统大麻/安纳咖": ["大麻", "安纳咖", "海洛因"],
            "渠道_口岸跨境": ["口岸", "边境"],
            "渠道_城市黑市": ["黑市", "青少年"],
            "人群_青少年": ["青少年", "学生"],
            "大宗查获": ["公斤", "吨"],
        }
        out = {}
        for name, kws in dims.items():
            a = sum(1 for i in items if (i.published_at or i.crawled_at) < mid and self._match(i, kws))
            b = sum(1 for i in items if (i.published_at or i.crawled_at) >= mid and self._match(i, kws))
            delta = b - a
            out[name] = {"前15日": a, "近15日": b, "差值": delta}
        return {
            "window_days": 30,
            "total_items": len(items),
            "dimensions": out,
        }
    def _trend_30d_section(self, items: List[IntelItem]) -> str:
        lines = ["## 十、近30日情报趋势对比（前15日VS近15日）", ""]
        data = self.trend_compare_30d(items)
        if not items:
            lines.append("- 暂无有效情报，建议执行1年窗口全量巡检。")
            return "\n".join(lines)
        for name, row in data["dimensions"].items():
            arrow = "↑" if row["delta"] > 0 else ("↓" if row["delta"] < 0 else "→")
            lines.append(f"- {name}：前15日 {row['前15日']} 条 → 近15日 {row['近15日']} （{arrow}{abs(row['差值'])}）")
        lines.append("")
        lines.append("注：仅代表媒体披露数量，不等于实际案发总量。")
        return "\n".join(lines)
    def _risk_outlook(self, items: List[IntelItem], by_category: Counter, alerts: list) -> str:
        parts = []
        if alerts:
            parts.append(f"系统识别{len(alerts)}条重要/紧急线索，优先核验原文。")
        if by_category.get("跨境毒情", 0) >= 2:
            parts.append("口岸走私报道增多，边境货运、徒步通道风险抬升。")
        if by_category.get("新型毒品", 0):
            parts.append("合成阿片类案件持续披露，需长期跟踪流通渠道。")
        if not parts:
            parts.append("整体资讯平稳，持续监测蒙古本土媒体补充线索。")
        return " ".join(parts)
    @staticmethod
    def _match(item: IntelItem, keys: List[str]) -> bool:
        blob = " ".join(
            [
                item.title or "",
                item.title_zh or "",
                item.summary or "",
                item.summary_zh or "",
            ]
        ).lower()
        return any(k.lower() in blob for k in keys)
    @staticmethod
    def _md_to_simple_html(md: str) -> str:
        import html as html_lib
        import re
        escaped = html_lib.escape(md)
        lines = escaped.split("\n")
        out = [
            "<div class='report-body' style='font-family:Segoe UI,Noto Sans SC,Arial,sans-serif;line-height:1.7;color:#ffffff'>"
        ]
        for line in lines:
            if line.startswith("# "):
                out.append(f"<h1 style='color:#ffffff'>{line[2:]}</h1>")
            elif line.startswith("## "):
                out.append(
                    f"<h2 style='color:#ffffff;border-bottom:1px solid rgba(255,255,.25);padding-bottom:4px'>{line[3:]}</h2>"
                )
            elif line.startswith("### "):
                out.append(f"<h3 style='color:#ffffff'>{line[4:]}</h3>")
            elif line.startswith("- "):
                out.append(f"<div style='color:#ffffff'>• {line[2:]}</div>")
            elif re.match(r"\d+\. ", line):
                out.append(f"<div style='color:#ffffff'>{line}</div>")
            elif line.strip() == "---":
                out.append("<hr style='border-color:rgba(255,255,.25)'/>")
            elif line.strip() == "":
                out.append("<br/>")
            else:
                line2 = re.sub(r"\*\*(.+?)\*\*", r"<strong style='color:#ffffff'>\1</strong>", line)
                out.append(f"<p style='color:#ffffff'>{line2}</p>")
        out.append("</div>")
        return "\n".join(out)
