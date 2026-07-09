"""专业级情报交叉研判分析引擎"""
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.config import get_settings
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
]


class AnalysisEngine:
    """多源交叉比对、关联研判、趋势分析、风险研判。"""

    def __init__(self, db: Session):
        self.db = db

    def collect_items(self, days: int = 7) -> List[IntelItem]:
        since = datetime.utcnow() - timedelta(days=days)
        return (
            self.db.query(IntelItem)
            .filter(IntelItem.crawled_at >= since)
            .filter(IntelItem.is_duplicate.is_(False))
            .order_by(IntelItem.crawled_at.desc())
            .all()
        )

    def generate_report(self, report_type: str = "daily", days: Optional[int] = None) -> Report:
        days = days or {"daily": 1, "weekly": 7, "monthly": 30, "alert": 1}.get(report_type, 7)
        items = self.collect_items(days=days)
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=days)

        md = self._build_markdown(items, report_type, period_start, period_end)
        html = self._md_to_simple_html(md)
        title = f"蒙古国禁毒情报研判报告（{self._type_label(report_type)}）{period_end.strftime('%Y-%m-%d %H:%M')} UTC"

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
            by_org[it.org_name or "未知机构"] += 1
            if it.is_alert or it.intel_level in ("紧急", "重要"):
                alerts.append(it)

        lines: List[str] = []
        lines.append(f"# 蒙古国禁毒情报研判报告（{self._type_label(report_type)}）")
        lines.append("")
        lines.append(f"**密级提示**：内部研判材料，仅供授权人员使用。")
        lines.append(
            f"**统计周期**：{period_start.strftime('%Y-%m-%d %H:%M')} — {period_end.strftime('%Y-%m-%d %H:%M')} UTC"
        )
        lines.append(f"**有效情报条目**：{len(items)} 条")
        lines.append(f"**告警/重要条目**：{len(alerts)} 条")
        lines.append("")

        # 1 本期情报综述
        lines.append("## 一、本期情报综述")
        lines.append("")
        if not items:
            lines.append(
                "本周期内，七大官方禁毒体系公开渠道未检出新增可结构化禁毒相关情报。"
                "系统已完成全网巡检，建议维持既定监测频次，重点关注口岸与执法通报栏目。"
            )
        else:
            top_cats = "、".join([f"{k}({v})" for k, v in by_category.most_common(5)]) or "无"
            top_orgs = "、".join([f"{k}({v})" for k, v in by_org.most_common(5)]) or "无"
            lines.append(
                f"本周期共采集有效禁毒相关公开情报 **{len(items)}** 条。"
                f"情报等级分布：{dict(by_level)}。"
                f"主题分布靠前为：{top_cats}。"
                f"信息源活跃机构：{top_orgs}。"
            )
            lines.append(
                "综合研判：蒙方公开渠道仍以执法通报、预防宣传、监管政策与国际协作信息为主；"
                "跨境与口岸相关动态需与海关、边防、外交公开信息交叉核验后纳入重点关注清单。"
            )
        lines.append("")

        # 2 分机构专项动态
        lines.append("## 二、分机构专项动态汇总")
        lines.append("")
        for sid, sname in SYSTEM_ORDER:
            group = by_system.get(sid, [])
            lines.append(f"### （{sid}）{sname}")
            if not group:
                lines.append("- 本周期无新增公开禁毒相关动态。")
            else:
                # 机构工作重心研判
                cats = Counter([g.category for g in group])
                focus = "、".join([c for c, _ in cats.most_common(3)]) or "综合"
                lines.append(f"- **工作重心研判**：近期公开信息侧重「{focus}」。")
                for g in group[:8]:
                    title = g.title_zh or g.title
                    pub = (g.published_at or g.crawled_at).strftime("%Y-%m-%d") if (g.published_at or g.crawled_at) else "-"
                    lines.append(
                        f"- 【{g.intel_level}】[{title}]({g.url})｜机构：{g.org_name}｜时间：{pub}｜类别：{g.category}"
                    )
            lines.append("")

        # 3 跨境禁毒态势
        lines.append("## 三、跨境禁毒态势分析")
        lines.append("")
        cross = [i for i in items if i.category == "跨境毒情" or self._match(i, ["口岸", "边境", "хил", "гааль", "border", "customs"])]
        if cross:
            lines.append(
                f"本周期检出跨境/口岸相关公开信息 {len(cross)} 条。"
                "研判意见：关注中蒙口岸查验强度变化、季节性货运高峰与公开查获通报的时空分布；"
                "对“严查/专项/大规模查获”表述应提升监测优先级，并与海关、边防同源信息交叉比对。"
            )
            for g in cross[:6]:
                lines.append(f"- {g.title_zh or g.title}（{g.org_name}）— {g.url}")
        else:
            lines.append(
                "本周期公开渠道未见显著跨境走私通道变化通报。维持对海关、边防、外交涉毒合作栏目的常态监测，"
                "重点观察口岸严查、双边联络与查获类信息。"
            )
        lines.append("")

        # 4 政策法规
        lines.append("## 四、政策法规更新研判")
        lines.append("")
        policy = [i for i in items if i.category == "政策法规" or self._match(i, ["法", "法规", "хууль", "regulation", "legal"])]
        if policy:
            lines.append(f"检出政策法规类信息 {len(policy)} 条，建议核查是否涉及管制目录调整、刑罚适用或监管流程变更。")
            for g in policy[:6]:
                lines.append(f"- {g.title_zh or g.title} — {g.url}")
        else:
            lines.append("本周期未见明确新法出台或管制目录重大调整的公开信息。")
        lines.append("")

        # 5 新型毒品风险
        lines.append("## 五、新型毒品风险研判")
        lines.append("")
        novel = [i for i in items if i.category == "新型毒品" or self._match(i, ["合成", "芬太尼", "synthetic", "NPS", "meth", "синтетик"])]
        precursor = [i for i in items if i.category == "制毒原料" or self._match(i, ["易制毒", "precursor", "麻精", "controlled"])]
        lines.append(
            f"新型毒品相关公开信息 {len(novel)} 条；制毒原料/麻精监管相关 {len(precursor)} 条。"
        )
        if novel or precursor:
            lines.append(
                "风险研判：若出现新增管制品类、合成毒品流通或易制毒化学品监管新规，应立即纳入紧急推送与专题跟踪。"
            )
            for g in (novel + precursor)[:8]:
                lines.append(f"- 【{g.category}】{g.title_zh or g.title} — {g.url}")
        else:
            lines.append("本周期公开渠道未检出新型毒品或制毒原料监管重大异常信号。")
        lines.append("")

        # 6 戒毒治理
        lines.append("## 六、戒毒治理态势研判")
        lines.append("")
        rehab = [i for i in items if i.category == "戒毒康复" or self._match(i, ["戒毒", "康复", "成瘾", "rehab", "донтсон", "нөхөн"])]
        if rehab:
            lines.append(f"戒毒康复与社会防毒相关公开信息 {len(rehab)} 条，反映蒙方在成瘾干预与预防宣传方面的公开工作节奏。")
            for g in rehab[:5]:
                lines.append(f"- {g.title_zh or g.title} — {g.url}")
        else:
            lines.append("本周期戒毒康复类公开动态较少，维持对卫生部门与康复机构栏目监测。")
        lines.append("")

        # 7 国际协作
        lines.append("## 七、国际协作研判")
        lines.append("")
        intl = [i for i in items if i.system_id == 7 or i.category == "国际协作" or self._match(i, ["UNODC", "国际", "олон улсын"])]
        if intl:
            lines.append(f"国际禁毒协作相关公开信息 {len(intl)} 条，重点关注 UNODC 蒙古项目与外交部涉外禁毒合作表述。")
            for g in intl[:6]:
                lines.append(f"- {g.title_zh or g.title}（{g.org_name}）— {g.url}")
        else:
            lines.append("本周期国际协作公开信息有限，继续跟踪 UNODC 与外交部合作栏目。")
        lines.append("")

        # 8 突出线索清单
        lines.append("## 八、突出线索清单")
        lines.append("")
        focus_list = sorted(
            alerts or items,
            key=lambda x: {"紧急": 0, "重要": 1, "关注": 2, "一般": 3}.get(x.intel_level or "一般", 9),
        )[:15]
        if not focus_list:
            lines.append("暂无突出线索。")
        else:
            for idx, g in enumerate(focus_list, 1):
                pub = (g.published_at or g.crawled_at)
                pub_s = pub.strftime("%Y-%m-%d %H:%M") if pub else "-"
                lines.append(
                    f"{idx}. 【{g.intel_level}/{g.category}】{g.title_zh or g.title}｜"
                    f"{g.org_name}｜{pub_s}｜来源：{g.url}"
                )
        lines.append("")

        # 9 风险预警与趋势
        lines.append("## 九、风险预警与趋势预判")
        lines.append("")
        lines.append(self._risk_outlook(items, by_category, alerts))
        lines.append("")

        # 10 下期重点监测
        lines.append("## 十、下期重点监测方向")
        lines.append("")
        lines.append("1. 海关与边防公开查获、口岸严查及双边禁毒联络动态。")
        lines.append("2. 警察总局缉毒执法通报与地方（21省/乌兰巴托9区）联动信息。")
        lines.append("3. 卫生/药品监管部门麻精药品、易制毒化学品及管制目录调整。")
        lines.append("4. 合成毒品、新精神活性物质相关公开表述与实验室检测信息。")
        lines.append("5. 戒毒康复政策、成瘾数据与社会预防举措。")
        lines.append("6. UNODC 蒙古项目进展及外交部国际禁毒合作公开信息。")
        lines.append("")
        lines.append("---")
        lines.append("*本报告由蒙古国禁毒全网情报自动采集研判系统自动生成，数据仅来源于蒙古国官方禁毒体系及 UNODC 公开渠道。*")
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
        out = ["<div style='font-family:Segoe UI,Arial,sans-serif;line-height:1.6;color:#1a1a1a'>"]
        for line in lines:
            if line.startswith("# "):
                out.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                out.append(f"<h2 style='border-bottom:1px solid #ccc;padding-bottom:4px'>{line[3:]}</h2>")
            elif line.startswith("### "):
                out.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("- "):
                out.append(f"<div>• {line[2:]}</div>")
            elif re.match(r"\d+\. ", line):
                out.append(f"<div>{line}</div>")
            elif line.strip() == "---":
                out.append("<hr/>")
            elif line.strip() == "":
                out.append("<br/>")
            else:
                # 粗体 ** **
                line2 = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
                out.append(f"<p>{line2}</p>")
        out.append("</div>")
        return "\n".join(out)
