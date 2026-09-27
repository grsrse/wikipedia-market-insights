"""
Executive 1-Page PDF Brief Generator for B2C Founders & Product Managers.
Uses ReportLab to generate a clean, publication-grade, single-page intelligence memo.
Includes multi-lingual TrueType font support for Cyrillic and Central European characters.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Register TrueType fonts for complete UTF-8 & Cyrillic / Central-European support
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

FONT_CANDIDATES = [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/System/Library/Fonts/Helvetica.ttc", "/System/Library/Fonts/Helvetica.ttc"),
]

for reg_path, bold_path in FONT_CANDIDATES:
    if os.path.exists(reg_path):
        try:
            pdfmetrics.registerFont(TTFont("AppSans", reg_path))
            if os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont("AppSans-Bold", bold_path))
            else:
                pdfmetrics.registerFont(TTFont("AppSans-Bold", reg_path))
            FONT_REGULAR = "AppSans"
            FONT_BOLD = "AppSans-Bold"
            break
        except Exception:
            pass


def make_proportional_image(
    image_path: str | Path,
    max_width: float = 530.0,
    max_height: Optional[float] = None,
) -> Optional[Image]:
    """
    Dynamically loads image, reads intrinsic pixel dimensions,
    and scales it proportionally to fit within max_width and max_height
    WITHOUT stretching or squishing the aspect ratio.
    """
    p = Path(image_path)
    if not p.exists():
        return None
    try:
        from reportlab.lib.utils import ImageReader
        img_reader = ImageReader(str(p))
        orig_w, orig_h = img_reader.getSize()
        if orig_w <= 0 or orig_h <= 0:
            return Image(str(p), width=max_width, height=max_height or 200)

        aspect_ratio = orig_w / orig_h

        # Fit within max_width
        target_w = max_width
        target_h = target_w / aspect_ratio

        # If target_h exceeds max_height, scale down proportionally
        if max_height and target_h > max_height:
            target_h = max_height
            target_w = target_h * aspect_ratio

        return Image(str(p), width=round(target_w, 2), height=round(target_h, 2))
    except Exception:
        return Image(str(p), width=max_width, height=max_height or 200)


class PDFReportGenerator:
    """Generates a 1-page PDF Executive Summary for a topic validation hypothesis."""

    def __init__(self, output_path: str | Path) -> None:
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def generate_single_topic_report(
        self,
        analysis: Dict[str, Any],
        chart_image_path: str | Path,
    ) -> Path:
        """Generates 1-page PDF for a single topic analysis (e.g. Astronomy in uk.wikipedia)."""
        doc = SimpleDocTemplate(
            str(self.output_path),
            pagesize=A4,
            leftMargin=32,
            rightMargin=32,
            topMargin=26,
            bottomMargin=26,
        )

        styles = getSampleStyleSheet()
        normal_style = styles["Normal"]

        title_style = ParagraphStyle(
            "DocTitle",
            parent=normal_style,
            fontName=FONT_BOLD,
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#0f172a"),
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=normal_style,
            fontName=FONT_REGULAR,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#64748b"),
        )
        section_style = ParagraphStyle(
            "SectionTitle",
            parent=normal_style,
            fontName=FONT_BOLD,
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#1e293b"),
        )
        body_style = ParagraphStyle(
            "BodySmall",
            parent=normal_style,
            fontName=FONT_REGULAR,
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#334155"),
        )
        kpi_title_style = ParagraphStyle(
            "KPITitle",
            parent=normal_style,
            fontName=FONT_BOLD,
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor("#475569"),
            alignment=1,
        )
        kpi_val_style = ParagraphStyle(
            "KPIVal",
            parent=normal_style,
            fontName=FONT_BOLD,
            fontSize=13,
            leading=15,
            textColor=colors.HexColor("#0f172a"),
            alignment=1,
        )

        story = []

        # 1. Header with Badge
        topic = analysis["topic"]
        lang = analysis["language"].upper()
        start = analysis.get("start_date", "")
        end = analysis.get("end_date", "")
        today_str = datetime.now().strftime("%B %d, %Y")

        header_data = [
            [
                Paragraph(f"Wikipedia Market Intelligence: <b>{topic}</b>", title_style),
                Paragraph(f"<b>B2C Product Validation Memo</b><br/>Date: {today_str}", subtitle_style),
            ],
            [
                Paragraph(f"Language: <b>{lang}.wikipedia</b> | Scope: {start} → {end} | Agent Filter: Organic Readers (User-only)", subtitle_style),
                "",
            ],
        ]
        t_header = Table(header_data, colWidths=[380, 150])
        t_header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(t_header)
        story.append(Spacer(1, 4))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=2, spaceAfter=6))

        # 2. KPI Cards (4 metrics)
        summary = analysis["summary"]
        growth = analysis["growth"]
        trust = analysis["trust_metrics"]
        spikes = analysis["spikes"]
        ci = analysis.get("bootstrap_ci")
        fc = analysis.get("forecast")

        total_v = f"{summary['total_views']:,}"
        yoy_v = f"{'+' if growth['yoy_growth_percent'] > 0 else ''}{growth['yoy_growth_percent']}%"

        if ci:
            trust_v = f"{trust['trust_score']:.0f}/100<br/><font size=6 color='#64748b'>CI: [{ci['low_95']:.0f}-{ci['high_95']:.0f}]</font>"
        else:
            trust_v = f"{trust['trust_score']}/100"

        if fc and "point_forecast" in fc and fc["point_forecast"]:
            card4_title = f"{fc.get('horizon_days', 90)}-DAY PROJECTION"
            card4_val = f"{fc['point_forecast'][-1]:,.0f}/d<br/><font size=6 color='#64748b'>({fc.get('trend_direction', 'stable')})</font>"
        else:
            card4_title = "SPIKE CONCENTRATION"
            card4_val = f"{round(spikes['ratio'] * 100, 1)}%"

        kpi_data = [
            [
                Paragraph("TOTAL PAGEVIEWS", kpi_title_style),
                Paragraph("YoY GROWTH", kpi_title_style),
                Paragraph("TRUST SCORE", kpi_title_style),
                Paragraph(card4_title, kpi_title_style),
            ],
            [
                Paragraph(total_v, kpi_val_style),
                Paragraph(yoy_v, kpi_val_style),
                Paragraph(trust_v, kpi_val_style),
                Paragraph(card4_val, kpi_val_style),
            ],
        ]
        t_kpi = Table(kpi_data, colWidths=[132, 132, 132, 134])
        t_kpi.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_kpi)
        story.append(Spacer(1, 8))

        # 3. Chart Visual
        if Path(chart_image_path).exists():
            story.append(Paragraph("AUDIENCE TRAFFIC & BASELINE TREND", section_style))
            story.append(Spacer(1, 3))
            img = make_proportional_image(chart_image_path, max_width=530, max_height=215)
            if img:
                story.append(img)
            story.append(Spacer(1, 6))

        # 4. Statistical Trust & Reliability Diagnostics
        story.append(Paragraph("STATISTICAL RELIABILITY EVALUATION", section_style))
        story.append(Spacer(1, 3))

        diag_data = [
            ["Metric", "Value", "Benchmark / Interpretation"],
            ["Trust Verdict", trust["verdict"], "Composite score of organic stability & spike resilience"],
            ["Baseline 60d Growth", f"{'+' if growth['baseline_growth_percent'] > 0 else ''}{growth['baseline_growth_percent']}%", "Underlying audience trajectory excluding transient bursts"],
            ["Spike Days Count", f"{spikes['count']} days", "Days exceeding 2.5x IQR deviation above moving median"],
            ["Spike Impact Ratio", f"{round(spikes['ratio'] * 100, 1)}%", "Portion of traffic driven by short-lived events/news"],
            ["Daily Median Views", f"{summary['median_daily_views']:,} views", "Typical daily organic demand baseline"],
        ]
        t_diag = Table(diag_data, colWidths=[120, 130, 280])
        t_diag.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ]))
        story.append(t_diag)
        story.append(Spacer(1, 6))

        # 5. Founder Strategic Recommendations & Limitations
        story.append(Paragraph("STRATEGIC RECOMMENDATIONS & LIMITATIONS", section_style))
        story.append(Spacer(1, 3))

        explanation_text = trust.get("explanation", "")
        recs = [
            f"<b>Data-driven Diagnosis:</b> {explanation_text}",
            f"<b>Actionable Verdict:</b> {'Proceed with course/feature testing; demand is organic.' if trust['trust_score'] >= 50 else 'Exercise caution; traffic growth was driven by external news/events rather than sustained evergreen interest.'}",
            "<b>Market Caveat:</b> Wikipedia pageviews demonstrate informational curiosity and topical awareness, not immediate willingness-to-pay. Always conduct secondary pricing and conversion smoke-tests (e.g. landing page pre-orders) before committing substantial engineering budget.",
        ]
        for rec in recs:
            story.append(Paragraph(f"• {rec}", body_style))
            story.append(Spacer(1, 2))

        doc.build(story)
        return self.output_path

    def generate_comparison_report(
        self,
        topic: str,
        markets: List[Dict[str, Any]],
        chart_image_path: str | Path,
    ) -> Path:
        """Generates 1-page PDF comparing multiple language markets for a B2C product expansion."""
        doc = SimpleDocTemplate(
            str(self.output_path),
            pagesize=A4,
            leftMargin=32,
            rightMargin=32,
            topMargin=26,
            bottomMargin=26,
        )

        styles = getSampleStyleSheet()
        normal_style = styles["Normal"]

        title_style = ParagraphStyle(
            "DocTitle",
            parent=normal_style,
            fontName=FONT_BOLD,
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#0f172a"),
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=normal_style,
            fontName=FONT_REGULAR,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#64748b"),
        )
        section_style = ParagraphStyle(
            "SectionTitle",
            parent=normal_style,
            fontName=FONT_BOLD,
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#1e293b"),
        )
        body_style = ParagraphStyle(
            "BodySmall",
            parent=normal_style,
            fontName=FONT_REGULAR,
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#334155"),
        )
        kpi_title_style = ParagraphStyle(
            "KPITitle",
            parent=normal_style,
            fontName=FONT_BOLD,
            fontSize=7.5,
            leading=9,
            textColor=colors.HexColor("#475569"),
            alignment=1,
        )
        kpi_val_style = ParagraphStyle(
            "KPIVal",
            parent=normal_style,
            fontName=FONT_BOLD,
            fontSize=12,
            leading=14,
            textColor=colors.HexColor("#0f172a"),
            alignment=1,
        )

        story = []

        # 1. Header
        today_str = datetime.now().strftime("%B %d, %Y")
        lang_list = ", ".join(m["language"].upper() for m in markets)

        header_data = [
            [
                Paragraph(f"Cross-Market Opportunity Brief: <b>{topic}</b>", title_style),
                Paragraph(f"<b>B2C Market Expansion Memo</b><br/>Date: {today_str}", subtitle_style),
            ],
            [
                Paragraph(f"Markets Analyzed: <b>{lang_list}</b> | Methodology: Wikipedia Organic Reader Pageviews & Normalization", subtitle_style),
                "",
            ],
        ]
        t_header = Table(header_data, colWidths=[380, 150])
        t_header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(t_header)
        story.append(Spacer(1, 4))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=2, spaceAfter=6))

        # Multi-criteria normalized market ranking (Trust: 50%, Growth: 30%, Norm Density: 20%)
        # All factors normalized to [0, 1] relative to cohort max to prevent scale dominance
        max_trust = max((m["trust_metrics"]["trust_score"] for m in markets), default=100.0) or 100.0
        max_yoy = max((max(0.0, m["growth"]["yoy_growth_percent"]) for m in markets), default=100.0) or 100.0
        max_norm = max(((m.get("normalized_views_per_million") or 0.0) for m in markets), default=1.0) or 1.0

        def market_rank_score(m):
            t_norm = m["trust_metrics"]["trust_score"] / max(max_trust, 100.0)
            y_norm = max(0.0, m["growth"]["yoy_growth_percent"]) / max(max_yoy, 1.0)
            n_norm = (m.get("normalized_views_per_million") or 0.0) / max(max_norm, 1.0)
            return t_norm * 0.5 + y_norm * 0.3 + n_norm * 0.2

        sorted_markets = sorted(markets, key=market_rank_score, reverse=True)
        top_market = sorted_markets[0]
        top_lang = top_market["language"].upper()

        total_all_views = sum(m["summary"]["total_views"] for m in markets)
        best_growth_m = max(markets, key=lambda m: m["growth"]["yoy_growth_percent"])

        # 2. KPI Cards
        kpi_data = [
            [
                Paragraph("TOTAL AGGREGATE VIEWS", kpi_title_style),
                Paragraph("TOP RECOMMENDED MARKET", kpi_title_style),
                Paragraph("HIGHEST YoY GROWTH", kpi_title_style),
                Paragraph("TOP TRUST SCORE", kpi_title_style),
            ],
            [
                Paragraph(f"{total_all_views:,}", kpi_val_style),
                Paragraph(f"{top_lang} (Score: {top_market['trust_metrics']['trust_score']:.0f})", kpi_val_style),
                Paragraph(f"{best_growth_m['language'].upper()} ({'+' if best_growth_m['growth']['yoy_growth_percent'] > 0 else ''}{best_growth_m['growth']['yoy_growth_percent']}%)", kpi_val_style),
                Paragraph(f"{sorted_markets[0]['trust_metrics']['trust_score']:.0f}/100", kpi_val_style),
            ],
        ]
        t_kpi = Table(kpi_data, colWidths=[132, 132, 132, 134])
        t_kpi.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_kpi)
        story.append(Spacer(1, 8))

        # 3. Comparative Chart
        if Path(chart_image_path).exists():
            story.append(Paragraph("COMPARATIVE MARKET METRICS", section_style))
            story.append(Spacer(1, 3))
            img = make_proportional_image(chart_image_path, max_width=530, max_height=210)
            if img:
                story.append(img)
            story.append(Spacer(1, 6))

        # 4. Multi-market Comparison Table
        story.append(Paragraph("MARKET COMPARISON MATRIX", section_style))
        story.append(Spacer(1, 3))

        cell_style = ParagraphStyle(
            "MatrixCellComp",
            parent=normal_style,
            fontName=FONT_REGULAR,
            fontSize=7,
            leading=8.5,
            textColor=colors.HexColor("#1e293b"),
        )
        cell_bold = ParagraphStyle(
            "MatrixHeaderComp",
            parent=cell_style,
            fontName=FONT_BOLD,
            alignment=1,
        )

        matrix_data = [
            [
                Paragraph("<b>Lang</b>", cell_bold),
                Paragraph("<b>Article Title</b>", cell_bold),
                Paragraph("<b>Total Views</b>", cell_bold),
                Paragraph("<b>YoY %</b>", cell_bold),
                Paragraph("<b>Spike %</b>", cell_bold),
                Paragraph("<b>Norm Views / 1M</b>", cell_bold),
                Paragraph("<b>Trust Score</b>", cell_bold),
            ]
        ]
        for m in sorted_markets:
            lang_code = m["language"].upper()
            art = m["article_title"]
            v_tot = f"{m['summary']['total_views']:,}"
            yoy = f"{'+' if m['growth']['yoy_growth_percent'] > 0 else ''}{m['growth']['yoy_growth_percent']}%"
            spk = f"{round(m['spikes']['ratio'] * 100, 1)}%"
            n_v = f"{m.get('normalized_views_per_million') or 0:.1f}"
            t_s = f"{m['trust_metrics']['trust_score']:.0f}"
            if m.get("cohort_name"):
                t_s += f" ({m['cohort_name']})"
            else:
                raw_verdict = m.get("trust_metrics", {}).get("verdict", "")
                if "High" in raw_verdict:
                    v_short = "High"
                elif "Moderate" in raw_verdict:
                    v_short = "Moderate"
                elif "Fragile" in raw_verdict:
                    v_short = "Fragile"
                else:
                    v_short = raw_verdict.split()[0] if raw_verdict else ""
                if v_short:
                    t_s += f" ({v_short})"
            matrix_data.append([
                Paragraph(lang_code, cell_style),
                Paragraph(art, cell_style),
                Paragraph(v_tot, cell_style),
                Paragraph(yoy, cell_style),
                Paragraph(spk, cell_style),
                Paragraph(n_v, cell_style),
                Paragraph(t_s, cell_style),
            ])

        t_matrix = Table(matrix_data, colWidths=[35, 135, 75, 55, 55, 85, 90])
        t_matrix.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ]))
        story.append(t_matrix)
        story.append(Spacer(1, 6))

        # 5. Founder Takeaways & Next Steps
        story.append(Paragraph("STRATEGIC EXPANSION RECOMMENDATIONS", section_style))
        story.append(Spacer(1, 3))

        top_reason = (
            f"Market <b>{top_lang}</b> demonstrates the healthiest balance of sustainable demand: "
            f"Trust Score of {top_market['trust_metrics']['trust_score']:.0f}/100 with only {round(top_market['spikes']['ratio']*100, 1)}% spike contamination."
        )
        recs = [
            f"<b>Primary Rollout Target:</b> {top_reason}",
            f"<b>Localization Prioritization:</b> Prioritize localized marketing and feature development for {', '.join(m['language'].upper() for m in sorted_markets[:2])} before lower-ranked segments.",
            "<b>Risk & Pricing Assessment:</b> Wikipedia metrics provide high-resolution demand discovery at low acquisition cost. Before heavy localization, test click-through on localized ads or landing pages to validate willingness to pay in the target market.",
        ]
        for rec in recs:
            story.append(Paragraph(f"• {rec}", body_style))
            story.append(Spacer(1, 2))

        doc.build(story)
        return self.output_path

    def generate_multi_topic_benchmark_report(
        self,
        benchmark_data: Dict[str, Dict[str, Any]],
        topics: List[str],
        langs: List[str],
        comparison_chart_path: str | Path,
        individual_topic_charts: Optional[Dict[str, str | Path]] = None,
    ) -> Path:
        """
        Generates a Multi-Page Multi-Topic Benchmark PDF Report:
        - Page 1: Executive Overview, Cross-Topic Benchmark Matrix & Strategic Recommendations
        - Pages 2..1+N: Individual Deep-Dive Topic Pages (1 page per topic with charts & Council of Rivals)
        Strictly guarantees exactly 1 + len(topics) pages.
        """
        individual_topic_charts = individual_topic_charts or {}
        doc = SimpleDocTemplate(
            str(self.output_path),
            pagesize=A4,
            leftMargin=32,
            rightMargin=32,
            topMargin=26,
            bottomMargin=26,
        )

        styles = getSampleStyleSheet()
        normal_style = styles["Normal"]

        title_style = ParagraphStyle(
            "BenchTitle",
            parent=normal_style,
            fontName=FONT_BOLD,
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#0f172a"),
        )
        subtitle_style = ParagraphStyle(
            "BenchSubTitle",
            parent=normal_style,
            fontName=FONT_REGULAR,
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#64748b"),
        )
        section_style = ParagraphStyle(
            "BenchSectionTitle",
            parent=normal_style,
            fontName=FONT_BOLD,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#1e293b"),
        )
        body_style = ParagraphStyle(
            "BenchBody",
            parent=normal_style,
            fontName=FONT_REGULAR,
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#334155"),
        )
        kpi_title_style = ParagraphStyle(
            "BenchKPITitle",
            parent=normal_style,
            fontName=FONT_BOLD,
            fontSize=6.5,
            leading=8,
            textColor=colors.HexColor("#475569"),
            alignment=1,
        )
        kpi_val_style = ParagraphStyle(
            "BenchKPIVal",
            parent=normal_style,
            fontName=FONT_BOLD,
            fontSize=10,
            leading=12,
            textColor=colors.HexColor("#0f172a"),
            alignment=1,
        )

        story = []
        today_str = datetime.now().strftime("%B %d, %Y")

        # --- Calculate Leaders across topics ---
        topic_totals = {}
        topic_avg_trust = {}
        topic_growths = {}
        for t in topics:
            tot_v = sum(benchmark_data.get(t, {}).get(l, {}).get("summary", {}).get("total_views", 0) for l in langs)
            topic_totals[t] = tot_v
            t_scores = [benchmark_data.get(t, {}).get(l, {}).get("trust_metrics", {}).get("trust_score", 50.0) for l in langs]
            topic_avg_trust[t] = sum(t_scores) / max(1, len(t_scores))
            g_rates = [benchmark_data.get(t, {}).get(l, {}).get("growth", {}).get("yoy_growth_percent", 0.0) for l in langs]
            topic_growths[t] = max(g_rates) if g_rates else 0.0

        vol_leader = max(topic_totals, key=topic_totals.get) if topic_totals else topics[0]
        growth_leader = max(topic_growths, key=topic_growths.get) if topic_growths else topics[0]
        trust_leader = max(topic_avg_trust, key=topic_avg_trust.get) if topic_avg_trust else topics[0]

        # =========================================================
        # PAGE 1: EXECUTIVE BENCHMARK OVERVIEW & MATRIX
        # =========================================================
        t_names_short = ", ".join(topics[:3]) + (f" (+{len(topics)-3})" if len(topics) > 3 else "")
        header_data = [
            [
                Paragraph(f"Cross-Topic Executive Benchmark: <b>{t_names_short}</b>", title_style),
                Paragraph(f"<b>B2C Product Hypothesis Memo</b><br/>Date: {today_str} | Markets: {', '.join(l.upper() for l in langs)}", subtitle_style),
            ]
        ]
        t_head = Table(header_data, colWidths=[370, 160])
        t_head.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_head)
        story.append(Spacer(1, 3))

        # 4 KPI Summary Cards
        kpi_cards = [
            [
                Paragraph("TOTAL VOLUME LEADER", kpi_title_style),
                Paragraph("GROWTH DYNAMICS LEADER", kpi_title_style),
                Paragraph("ORGANIC STABILITY LEADER", kpi_title_style),
                Paragraph("RECOMMENDED PRIMARY BET", kpi_title_style),
            ],
            [
                Paragraph(f"{vol_leader}<br/><font size=6 color='#64748b'>{topic_totals[vol_leader]:,} views</font>", kpi_val_style),
                Paragraph(f"{growth_leader}<br/><font size=6 color='#059669'>{'+' if topic_growths[growth_leader]>0 else ''}{topic_growths[growth_leader]:.1f}% Max YoY</font>", kpi_val_style),
                Paragraph(f"{trust_leader}<br/><font size=6 color='#2563eb'>Score: {topic_avg_trust[trust_leader]:.1f}/100</font>", kpi_val_style),
                Paragraph(f"{vol_leader} (Core)<br/><font size=6 color='#059669'>+ {growth_leader} (Growth)</font>", kpi_val_style),
            ],
        ]
        t_kpi = Table(kpi_cards, colWidths=[132, 132, 132, 134])
        t_kpi.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_kpi)
        story.append(Spacer(1, 4))

        # 2x2 Comparative Chart
        if Path(comparison_chart_path).exists():
            story.append(Paragraph("CROSS-TOPIC QUANTITATIVE BENCHMARK (VOLUME, GROWTH, TRUST, SHARE)", section_style))
            story.append(Spacer(1, 2))
            img = make_proportional_image(comparison_chart_path, max_width=530, max_height=240)
            if img:
                story.append(img)
            story.append(Spacer(1, 4))

        # Multi-topic Performance Matrix Table
        story.append(Paragraph("TOPICS PERFORMANCE MATRIX ACROSS MARKETS", section_style))
        story.append(Spacer(1, 2))

        bench_cell_style = ParagraphStyle(
            "MatrixCellBench",
            parent=normal_style,
            fontName=FONT_REGULAR,
            fontSize=6.5,
            leading=8,
            textColor=colors.HexColor("#1e293b"),
        )
        bench_header_style = ParagraphStyle(
            "MatrixHeaderBench",
            parent=bench_cell_style,
            fontName=FONT_BOLD,
        )

        matrix_data = [
            [
                Paragraph("<b>Topic</b>", bench_header_style),
                Paragraph("<b>Market</b>", bench_header_style),
                Paragraph("<b>Article Title</b>", bench_header_style),
                Paragraph("<b>Total Views</b>", bench_header_style),
                Paragraph("<b>YoY %</b>", bench_header_style),
                Paragraph("<b>Trust Score (95% CI)</b>", bench_header_style),
                Paragraph("<b>Verdict / Status</b>", bench_header_style),
            ]
        ]
        for t in topics:
            for l in langs:
                m = benchmark_data.get(t, {}).get(l, {})
                if not m:
                    continue
                v_tot = f"{m.get('summary', {}).get('total_views', 0):,}"
                yoy = f"{'+' if m.get('growth', {}).get('yoy_growth_percent', 0) > 0 else ''}{m.get('growth', {}).get('yoy_growth_percent', 0):.1f}%"
                ts = m.get("trust_metrics", {}).get("trust_score", 50.0)
                ci = m.get("bootstrap_ci") or {}
                ci_str = f"{ts:.1f} [{ci.get('low_95', ts):.0f}-{ci.get('high_95', ts):.0f}]"
                art = m.get("article_title", t)
                verdict = m.get("trust_metrics", {}).get("verdict", "Moderate")

                matrix_data.append([
                    Paragraph(t, bench_cell_style),
                    Paragraph(l.upper(), bench_cell_style),
                    Paragraph(art, bench_cell_style),
                    Paragraph(v_tot, bench_cell_style),
                    Paragraph(yoy, bench_cell_style),
                    Paragraph(ci_str, bench_cell_style),
                    Paragraph(verdict, bench_cell_style),
                ])

        t_matrix = Table(matrix_data, colWidths=[65, 30, 130, 65, 50, 95, 95])
        t_matrix.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 6.5),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ]))
        story.append(t_matrix)
        story.append(Spacer(1, 4))

        # Strategic Verdict on Page 1
        story.append(Paragraph("STRATEGIC VERDICT & NEXT STEPS", section_style))
        story.append(Spacer(1, 2))
        verdict_summary = (
            f"<b>1. Base Retention Leader:</b> <b>{vol_leader}</b> commands the largest audience ({topic_totals[vol_leader]:,} views) with Trust Score of {topic_avg_trust[vol_leader]:.1f}/100. Ideal for flagship retention.<br/>"
            f"<b>2. Growth Momentum Play:</b> <b>{growth_leader}</b> exhibits the strongest demand momentum ({'+' if topic_growths[growth_leader]>0 else ''}{topic_growths[growth_leader]:.1f}% YoY). Greenlight for paid testing.<br/>"
            f"<b>3. Portfolio Recommendation:</b> Launch a hybrid roll-out: establish {vol_leader} as core content while using {growth_leader} for top-of-funnel acquisition."
        )
        story.append(Paragraph(verdict_summary, body_style))

        # =========================================================
        # PAGES 2..1+N: INDIVIDUAL TOPIC DEEP-DIVE PAGES
        # =========================================================
        for t_idx, t in enumerate(topics):
            story.append(PageBreak())

            t_header_data = [
                [
                    Paragraph(f"Topic Deep Dive ({t_idx+1}/{len(topics)}): <b>{t}</b>", title_style),
                    Paragraph(f"<b>Detailed Hypothesis Dossier</b><br/>Date: {today_str}", subtitle_style),
                ]
            ]
            t_t_head = Table(t_header_data, colWidths=[370, 160])
            t_t_head.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t_t_head)
            story.append(Spacer(1, 4))

            # Topic KPI bar
            t_tot = topic_totals.get(t, 0)
            t_growth = topic_growths.get(t, 0.0)
            t_trust = topic_avg_trust.get(t, 50.0)

            t_kpi_data = [
                [
                    Paragraph("TOTAL AUDIENCE", kpi_title_style),
                    Paragraph("MOMENTUM (YoY)", kpi_title_style),
                    Paragraph("ORGANIC TRUST", kpi_title_style),
                    Paragraph("COUNCIL STATUS", kpi_title_style),
                ],
                [
                    Paragraph(f"{t_tot:,}", kpi_val_style),
                    Paragraph(f"{'+' if t_growth > 0 else ''}{t_growth:.1f}%", kpi_val_style),
                    Paragraph(f"{t_trust:.1f}/100", kpi_val_style),
                    Paragraph(f"{'PROCEED' if t_trust >= 65 else 'CAUTION'}", kpi_val_style),
                ],
            ]
            t_t_kpi = Table(t_kpi_data, colWidths=[132, 132, 132, 134])
            t_t_kpi.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(t_t_kpi)
            story.append(Spacer(1, 6))

            # Individual Topic Chart if available
            t_chart_path = individual_topic_charts.get(t)
            if t_chart_path and Path(t_chart_path).exists():
                story.append(Paragraph(f"HISTORICAL TREND & TRAFFIC PROFILE: {t.upper()}", section_style))
                story.append(Spacer(1, 2))
                img = make_proportional_image(t_chart_path, max_width=530, max_height=215)
                if img:
                    story.append(img)
                story.append(Spacer(1, 5))

            # Market Breakdown for this Topic
            story.append(Paragraph("LANGUAGE MARKET PERFORMANCE BREAKDOWN", section_style))
            story.append(Spacer(1, 2))
            t_matrix_data = [
                ["Language", "Exact Wikipedia Article", "Total Views", "YoY %", "Spike Ratio", "Trust Score"]
            ]
            for l in langs:
                m = benchmark_data.get(t, {}).get(l, {})
                if not m:
                    continue
                t_matrix_data.append([
                    l.upper(),
                    m.get("article_title", ""),
                    f"{m.get('summary', {}).get('total_views', 0):,}",
                    f"{'+' if m.get('growth', {}).get('yoy_growth_percent', 0) > 0 else ''}{m.get('growth', {}).get('yoy_growth_percent', 0):.1f}%",
                    f"{round(m.get('spikes', {}).get('ratio', 0) * 100, 1)}%",
                    f"{m.get('trust_metrics', {}).get('trust_score', 0):.1f}/100",
                ])
            t_m_table = Table(t_matrix_data, colWidths=[65, 145, 85, 75, 75, 85])
            t_m_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ]))
            story.append(t_m_table)
            story.append(Spacer(1, 6))

            # Council of Rivals Perspectives for primary market
            primary_m = benchmark_data.get(t, {}).get(langs[0], {})
            council = primary_m.get("council_of_rivals", {})
            story.append(Paragraph("COUNCIL OF RIVALS PERSPECTIVES (EXPERT EVALUATION)", section_style))
            story.append(Spacer(1, 2))

            ua = council.get("ua_growth_marketer", {})
            risk = council.get("risk_epistemology_auditor", {})
            monet = council.get("monetization_strategist", {})

            council_content = [
                [
                    Paragraph(f"<b>UA & Growth Marketer:</b> {ua.get('viral_potential', 'N/A')}<br/>{ua.get('test_channel_recommendation', 'Test via search or short-form video.')}", body_style),
                ],
                [
                    Paragraph(f"<b>Risk & Epistemology Auditor:</b> {risk.get('epistemic_reliability', 'N/A')}<br/>{risk.get('risk_assessment', 'Evaluate spike resilience and retention.')}", body_style),
                ],
                [
                    Paragraph(f"<b>Monetization Strategist:</b> {monet.get('market_tier', 'N/A')}<br/>Pricing: {monet.get('pricing_recommendation', 'Subscription model.')}", body_style),
                ],
            ]
            t_council = Table(council_content, colWidths=[530])
            t_council.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(t_council)

        doc.build(story)
        return self.output_path

