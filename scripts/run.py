"""
CLI Entrypoint for the wikipedia-market-insights Agent Skill.

Designed for AI Agent execution (e.g. Claude Haiku 4.5 / OpenRouter):
- Deterministic argument parsing
- Structured JSON output to stdout
- Actionable error feedback
- High-DPI Chart & 1-Page PDF generation
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
# Ensure UTF-8 output on all platforms (especially Windows console)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import re
import hashlib

def make_safe_slug(text: str) -> str:
    """Generates an ASCII-safe filename slug."""
    s = re.sub(r"[^a-zA-Z0-9_\-]", "_", text).strip("_").lower()
    return s if s else hashlib.md5(text.encode("utf-8")).hexdigest()[:8]

from typing import Any, Dict, List, Optional

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from client import WikimediaClient
from analyzer import (
    TopicAnalyzer,
    kalman_filter_smoother,
    detect_spectral_cycles,
    forecast_time_series,
    bootstrap_trust_score,
    cluster_markets_kmeans,
)
from visualizer import (
    plot_single_topic_trend,
    plot_cross_language_comparison,
    plot_market_clusters,
    plot_multi_topic_benchmark,
)
from report_pdf import PDFReportGenerator



def get_date_range(period: str, start: Optional[str] = None, end: Optional[str] = None) -> tuple[str, str]:
    """Resolves period string (e.g. '2y', '1y', '6m') or explicit YYYYMMDD into (start, end)."""
    if start and end:
        return start.replace("-", ""), end.replace("-", "")

    end_dt = datetime.now() - timedelta(days=1)  # Yesterday is latest complete day in AQS
    if period == "2y":
        start_dt = end_dt - timedelta(days=730)
    elif period == "1y":
        start_dt = end_dt - timedelta(days=365)
    elif period == "6m":
        start_dt = end_dt - timedelta(days=180)
    elif period == "3y":
        start_dt = end_dt - timedelta(days=1095)
    else:
        start_dt = end_dt - timedelta(days=730)

    return start_dt.strftime("%Y%m%d"), end_dt.strftime("%Y%m%d")


def cmd_analyze(args: argparse.Namespace) -> int:
    """Analyze a single topic in a specific Wikipedia language edition."""
    client = WikimediaClient()
    start, end = get_date_range(args.period, args.start, args.end)

    # 1. Resolve exact title
    resolved = client.resolve_topic_across_languages(args.topic, primary_lang=args.lang, target_langs=[args.lang])
    article_title = resolved.get(args.lang) or args.topic

    # 2. Fetch pageviews
    pv_items = client.get_article_pageviews(
        project=args.lang,
        article=article_title,
        start=start,
        end=end,
        granularity="daily",
        agent=args.agent,
    )

    if not pv_items:
        # Actionable error message for AI agent
        err_out = {
            "status": "error",
            "error_type": "ArticleNotFoundOrNoViews",
            "message": f"No pageviews found for '{args.topic}' (resolved as '{article_title}') in {args.lang}.wikipedia.",
            "suggestion": "Verify article spelling or use Wikipedia search to find the closest exact article title.",
        }
        print(json.dumps(err_out, indent=2, ensure_ascii=False))
        return 1

    # 3. Analyze
    forecast_days = getattr(args, "forecast_days", 90) if getattr(args, "forecast", False) else None
    analyzer = TopicAnalyzer(pv_items)
    analysis = analyzer.to_analysis_dict(
        topic=args.topic,
        lang=args.lang,
        article_title=article_title,
        forecast_days=forecast_days,
    )

    # 4. Generate Visuals & PDF
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = make_safe_slug(args.topic)

    chart_file = out_dir / f"trend_{args.lang}_{slug}.png"
    pdf_file = out_dir / f"report_{args.lang}_{slug}.pdf"

    spikes_data = analyzer.detect_spikes()
    kalman_smoothed, _, _ = kalman_filter_smoother(analyzer.views)
    plot_single_topic_trend(
        dates=analyzer.dates,
        views=analyzer.views,
        baseline=spikes_data["rolling_baseline"],
        spikes=spikes_data["spikes"],
        topic=args.topic,
        lang=args.lang,
        trust_score=analysis["trust_metrics"]["trust_score"],
        verdict=analysis["trust_metrics"]["verdict"],
        output_path=chart_file,
        kalman_trend=kalman_smoothed,
        forecast=analysis.get("forecast"),
    )


    pdf_gen = PDFReportGenerator(pdf_file)
    pdf_gen.generate_single_topic_report(analysis, chart_file)

    output: Dict[str, Any] = {
        "status": "success",
        "action": "analyze",
        "data": analysis,
        "artifacts": {
            "chart_png": str(chart_file.resolve()),
            "report_pdf": str(pdf_file.resolve()),
        },
    }

    if getattr(args, "verify", False):
        from verify_memo import verify_pdf, verify_chart
        v_errors = verify_pdf(pdf_file) + verify_chart(chart_file)
        output["verification"] = {
            "status": "passed" if not v_errors else "failed",
            "errors": v_errors,
        }

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    """Compare a topic or benchmark multiple topics across language Wikipedia editions."""
    raw_topics = getattr(args, "topics", None) or getattr(args, "topic", "")
    topic_list = [t.strip() for t in raw_topics.split(",") if t.strip()]
    if not topic_list:
        topic_list = ["Intermittent fasting"]

    target_langs = [l.strip().lower() for l in args.langs.split(",") if l.strip()]
    if not target_langs:
        target_langs = ["pl", "cs"]

    if len(topic_list) > 1:
        return cmd_benchmark_topics(topic_list, target_langs, args)

    topic = topic_list[0]
    args.topic = topic

    client = WikimediaClient()
    start, end = get_date_range(args.period, args.start, args.end)

    # 1. Resolve topic titles across target languages
    primary_lang = getattr(args, "primary_lang", None) or target_langs[0]
    resolved_titles = client.resolve_topic_across_languages(
        args.topic, primary_lang=primary_lang, target_langs=target_langs
    )

    markets: List[Dict[str, Any]] = []
    missing_langs: List[str] = []

    for lang in target_langs:
        title = resolved_titles.get(lang) or args.topic
        pv_items = client.get_article_pageviews(
            project=lang,
            article=title,
            start=start,
            end=end,
            granularity="daily",
            agent=args.agent,
        )

        if not pv_items:
            missing_langs.append(lang)
            continue

        # Get aggregate views for normalization
        agg_start = start[:6] + "01"
        agg_end = end[:6] + "01"
        proj_items = client.get_project_pageviews_aggregate(
            project=lang,
            start=agg_start,
            end=agg_end,
            granularity="monthly",
            agent="user",
        )
        total_proj_views = sum(it.get("views", 0) for it in proj_items) if proj_items else None

        forecast_days = getattr(args, "forecast_days", 90) if getattr(args, "forecast", False) else None
        analyzer = TopicAnalyzer(pv_items)
        market_info = analyzer.to_analysis_dict(
            topic=args.topic,
            lang=lang,
            article_title=title,
            total_project_views=total_proj_views,
            forecast_days=forecast_days,
        )
        markets.append(market_info)

    if not markets:
        err_out = {
            "status": "error",
            "message": f"Failed to retrieve data for '{args.topic}' across requested languages: {target_langs}",
            "missing_languages": missing_langs,
        }
        print(json.dumps(err_out, indent=2, ensure_ascii=False))
        return 1

    # 2. Enrich with Tibshirani K-Means Clusters if >= 3 markets
    cluster_file: Optional[Path] = None
    if len(markets) >= 3:
        markets = cluster_markets_kmeans(markets)

    # 3. Generate Comparative Artifacts
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = make_safe_slug(args.topic)

    chart_file = out_dir / f"compare_{slug}.png"
    pdf_file = out_dir / f"market_memo_{slug}.pdf"

    plot_cross_language_comparison(markets, args.topic, chart_file)
    if len(markets) >= 3:
        cluster_file = out_dir / f"cluster_{slug}.png"
        plot_market_clusters(markets, args.topic, cluster_file)

    pdf_gen = PDFReportGenerator(pdf_file)
    pdf_gen.generate_comparison_report(args.topic, markets, chart_file)

    # 4. Sort & Formulate Recommendations
    sorted_markets = sorted(
        markets,
        key=lambda m: (
            m["trust_metrics"]["trust_score"] * 0.5 +
            min(m["growth"]["yoy_growth_percent"], 100.0) * 0.3 +
            (m.get("normalized_views_per_million") or 0.0) * 0.2
        ),
        reverse=True,
    )
    top_market = sorted_markets[0]

    artifacts_dict: Dict[str, str] = {
        "comparison_chart_png": str(chart_file.resolve()),
        "executive_memo_pdf": str(pdf_file.resolve()),
    }
    if cluster_file:
        artifacts_dict["cluster_chart_png"] = str(cluster_file.resolve())

    output = {
        "status": "success",
        "action": "compare",
        "topic": args.topic,
        "date_range": {"start": start, "end": end},
        "markets": markets,
        "top_recommendation": {
            "language": top_market["language"],
            "article_title": top_market["article_title"],
            "trust_score": top_market["trust_metrics"]["trust_score"],
            "yoy_growth_percent": top_market["growth"]["yoy_growth_percent"],
            "total_views": top_market["summary"]["total_views"],
            "verdict": top_market["trust_metrics"]["verdict"],
        },
        "ranking": [
            {
                "rank": i + 1,
                "language": m["language"],
                "article": m["article_title"],
                "total_views": m["summary"]["total_views"],
                "yoy_growth": m["growth"]["yoy_growth_percent"],
                "trust_score": m["trust_metrics"]["trust_score"],
                "cohort": m.get("cohort_name"),
            }
            for i, m in enumerate(sorted_markets)
        ],
        "artifacts": artifacts_dict,
    }

    if getattr(args, "verify", False):
        from verify_memo import verify_pdf, verify_chart
        v_errors = verify_pdf(pdf_file) + verify_chart(chart_file)
        if cluster_file:
            v_errors += verify_chart(cluster_file)
        output["verification"] = {
            "status": "passed" if not v_errors else "failed",
            "errors": v_errors,
        }

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


def cmd_benchmark_topics(
    topic_list: List[str], target_langs: List[str], args: argparse.Namespace
) -> int:
    """Benchmark multiple competing topics across language Wikipedia editions."""
    client = WikimediaClient()
    start, end = get_date_range(args.period, args.start, args.end)
    forecast_days = getattr(args, "forecast_days", 90) if getattr(args, "forecast", False) else None

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    benchmark_data: Dict[str, Dict[str, Any]] = {}
    individual_charts: Dict[str, Path] = {}
    warnings: List[Dict[str, Any]] = []

    for topic in topic_list:
        benchmark_data[topic] = {}
        primary_lang = getattr(args, "primary_lang", None) or target_langs[0]
        resolved = client.resolve_topic_across_languages(
            topic, primary_lang=primary_lang, target_langs=target_langs
        )
        t_markets: List[Dict[str, Any]] = []

        last_analyzer = None
        for lang in target_langs:
            title = resolved.get(lang) or topic
            pv_items = client.get_article_pageviews(
                project=lang,
                article=title,
                start=start,
                end=end,
                granularity="daily",
                agent=args.agent,
            )
            if not pv_items:
                warnings.append({
                    "warning_type": "ArticleNotFoundOrNoViews",
                    "topic": topic,
                    "language": lang,
                    "article_title": title,
                    "message": f"No pageviews found for '{topic}' (resolved as '{title}') in {lang}.wikipedia.",
                })
                continue

            agg_start = start[:6] + "01"
            agg_end = end[:6] + "01"
            proj_items = client.get_project_pageviews_aggregate(
                project=lang,
                start=agg_start,
                end=agg_end,
                granularity="monthly",
                agent="user",
            )
            total_proj_views = sum(it.get("views", 0) for it in proj_items) if proj_items else None

            analyzer = TopicAnalyzer(pv_items)
            last_analyzer = analyzer
            market_info = analyzer.to_analysis_dict(
                topic=topic,
                lang=lang,
                article_title=title,
                total_project_views=total_proj_views,
                forecast_days=forecast_days,
            )
            benchmark_data[topic][lang] = market_info
            t_markets.append(market_info)

        # Generate individual topic chart
        if len(t_markets) >= 2:
            t_slug = make_safe_slug(topic)
            t_chart = out_dir / f"compare_{t_slug}.png"
            plot_cross_language_comparison(t_markets, topic, t_chart)
            individual_charts[topic] = t_chart
        elif len(t_markets) == 1 and last_analyzer is not None:
            m_info = t_markets[0]
            t_slug = make_safe_slug(topic)
            t_chart = out_dir / f"trend_{m_info['language']}_{t_slug}.png"
            spikes_data = last_analyzer.detect_spikes()
            kalman_smoothed, _, _ = kalman_filter_smoother(last_analyzer.views)
            plot_single_topic_trend(
                dates=last_analyzer.dates,
                views=last_analyzer.views,
                baseline=spikes_data["rolling_baseline"],
                spikes=spikes_data["spikes"],
                topic=topic,
                lang=m_info["language"],
                trust_score=m_info["trust_metrics"]["trust_score"],
                verdict=m_info["trust_metrics"]["verdict"],
                output_path=t_chart,
                kalman_trend=kalman_smoothed,
                forecast=m_info.get("forecast"),
            )
            individual_charts[topic] = t_chart

    has_any_data = any(len(markets) > 0 for markets in benchmark_data.values())
    if not has_any_data:
        err_out = {
            "status": "error",
            "error_type": "AllArticlesNotFound",
            "message": f"Failed to retrieve data for any of the requested topics across languages: {target_langs}",
            "warnings": warnings,
            "suggestion": "Check topic spellings or verify if these topics exist in the requested language editions.",
        }
        print(json.dumps(err_out, indent=2, ensure_ascii=False))
        return 1

    # Generate unified 2x2 multi-topic benchmark chart
    bench_slug = make_safe_slug("_vs_".join(topic_list[:3]))
    chart_file = out_dir / f"benchmark_{bench_slug}.png"
    plot_multi_topic_benchmark(benchmark_data, topic_list, target_langs, chart_file)

    # Generate multi-page PDF report (1 overview + N topic pages)
    pdf_file = out_dir / f"benchmark_memo_{bench_slug}.pdf"
    pdf_gen = PDFReportGenerator(pdf_file)
    pdf_gen.generate_multi_topic_benchmark_report(
        benchmark_data=benchmark_data,
        topics=topic_list,
        langs=target_langs,
        comparison_chart_path=chart_file,
        individual_topic_charts=individual_charts,
    )

    # Compute ranking of topics across volume, growth, trust
    topic_scores = []
    for topic in topic_list:
        tot_views = sum(
            benchmark_data.get(topic, {}).get(l, {}).get("summary", {}).get("total_views", 0)
            for l in target_langs
        )
        avg_trust = sum(
            benchmark_data.get(topic, {}).get(l, {}).get("trust_metrics", {}).get("trust_score", 50.0)
            for l in target_langs
        ) / max(1, len(target_langs))
        max_growth = max(
            (benchmark_data.get(topic, {}).get(l, {}).get("growth", {}).get("yoy_growth_percent", 0.0)
            for l in target_langs),
            default=0.0,
        )
        topic_scores.append({
            "topic": topic,
            "total_views": tot_views,
            "average_trust_score": round(avg_trust, 1),
            "max_yoy_growth_percent": round(max_growth, 2),
        })

    sorted_topics = sorted(
        topic_scores,
        key=lambda x: x["total_views"] * 0.4 + x["average_trust_score"] * 1000 + x["max_yoy_growth_percent"] * 500,
        reverse=True,
    )

    output_status = "partial_success" if warnings else "success"
    output = {
        "status": output_status,
        "action": "benchmark",
        "topics": topic_list,
        "languages": target_langs,
        "date_range": {"start": start, "end": end},
        "topic_rankings": sorted_topics,
        "benchmark_data": benchmark_data,
        "warnings": warnings,
        "artifacts": {
            "benchmark_chart_png": str(chart_file.resolve()),
            "benchmark_memo_pdf": str(pdf_file.resolve()),
            "individual_charts": {t: str(p.resolve()) for t, p in individual_charts.items()},
        },
    }

    if getattr(args, "verify", False):
        from verify_memo import verify_pdf, verify_chart
        expected_pages = 1 + len(topic_list)
        v_errors = verify_pdf(pdf_file, expected_pages=expected_pages) + verify_chart(chart_file)
        for p in individual_charts.values():
            v_errors += verify_chart(p)
        output["verification"] = {
            "status": "passed" if not v_errors else "failed",
            "errors": v_errors,
        }

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


def cmd_cluster(args: argparse.Namespace) -> int:
    """Cluster multilingual markets into business cohorts using K-Means (Tibshirani ML)."""
    client = WikimediaClient()
    start, end = get_date_range(args.period, args.start, args.end)

    target_langs = [l.strip().lower() for l in args.langs.split(",") if l.strip()]
    if not target_langs:
        target_langs = ["en", "de", "pl", "uk", "cs"]

    primary_lang = getattr(args, "primary_lang", None) or target_langs[0]
    resolved_titles = client.resolve_topic_across_languages(
        args.topic, primary_lang=primary_lang, target_langs=target_langs
    )

    markets: List[Dict[str, Any]] = []
    missing_langs: List[str] = []

    for lang in target_langs:
        title = resolved_titles.get(lang) or args.topic
        pv_items = client.get_article_pageviews(
            project=lang,
            article=title,
            start=start,
            end=end,
            granularity="daily",
            agent=args.agent,
        )

        if not pv_items:
            missing_langs.append(lang)
            continue

        agg_start = start[:6] + "01"
        agg_end = end[:6] + "01"
        proj_items = client.get_project_pageviews_aggregate(
            project=lang,
            start=agg_start,
            end=agg_end,
            granularity="monthly",
            agent="user",
        )
        total_proj_views = sum(it.get("views", 0) for it in proj_items) if proj_items else None

        analyzer = TopicAnalyzer(pv_items)
        market_info = analyzer.to_analysis_dict(
            topic=args.topic,
            lang=lang,
            article_title=title,
            total_project_views=total_proj_views,
        )
        markets.append(market_info)

    if not markets:
        err_out = {
            "status": "error",
            "message": f"Failed to retrieve data for '{args.topic}' across requested languages: {target_langs}",
            "missing_languages": missing_langs,
        }
        print(json.dumps(err_out, indent=2, ensure_ascii=False))
        return 1

    n_clusters = getattr(args, "k", 3) or 3
    clustered_markets = cluster_markets_kmeans(markets, n_clusters=n_clusters)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = make_safe_slug(args.topic)
    chart_file = out_dir / f"cluster_{slug}.png"

    plot_market_clusters(clustered_markets, args.topic, chart_file)

    cohort_summary: Dict[str, Dict[str, Any]] = {}
    for m in clustered_markets:
        c_id = m.get("cluster_id", 0)
        c_name = m.get("cohort_name", f"Cluster {c_id}")
        if c_name not in cohort_summary:
            cohort_summary[c_name] = {
                "cohort_name": c_name,
                "description": m.get("cohort_description", ""),
                "languages": [],
                "member_count": 0,
            }
        cohort_summary[c_name]["languages"].append(m["language"])
        cohort_summary[c_name]["member_count"] += 1

    output = {
        "status": "success",
        "action": "cluster",
        "topic": args.topic,
        "n_clusters": len(cohort_summary),
        "cohorts": list(cohort_summary.values()),
        "markets": clustered_markets,
        "artifacts": {
            "cluster_chart_png": str(chart_file.resolve()),
        },
    }

    if getattr(args, "verify", False):
        from verify_memo import verify_chart
        v_errors = verify_chart(chart_file)
        output["verification"] = {
            "status": "passed" if not v_errors else "failed",
            "errors": v_errors,
        }

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="wikipedia-market-insights: B2C Market Intelligence Agent Skill CLI"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Analysis mode")

    # analyze
    p_analyze = subparsers.add_parser("analyze", help="Deep dive analysis of a topic in one language")
    p_analyze.add_argument("--topic", required=True, help="Topic name or concept")
    p_analyze.add_argument("--lang", default="uk", help="Language code (e.g. uk, en, pl)")
    p_analyze.add_argument("--period", default="2y", choices=["6m", "1y", "2y", "3y"], help="Historical lookback")
    p_analyze.add_argument("--start", help="Start date YYYYMMDD")
    p_analyze.add_argument("--end", help="End date YYYYMMDD")
    p_analyze.add_argument("--agent", default="user", choices=["user", "all-agents", "spider"], help="Traffic filter")
    p_analyze.add_argument("--forecast", action="store_true", help="Generate Shumway autoregressive forward forecast")
    p_analyze.add_argument("--forecast-days", type=int, default=90, help="Forecast horizon in days (default: 90)")
    p_analyze.add_argument("--output-dir", default="./artifacts", help="Directory for charts and PDF report")
    p_analyze.add_argument("--verify", action="store_true", help="Run deterministic verification gate on generated artifacts")

    # compare
    p_compare = subparsers.add_parser("compare", help="Compare a topic or benchmark multiple topics across language Wikipedia editions")
    p_compare.add_argument("--topic", help="Topic name or concept (or comma-separated list of topics)")
    p_compare.add_argument("--topics", help="Comma-separated topic names for multi-topic benchmarking (e.g. 'Pilates,Calisthenics,Stretching')")
    p_compare.add_argument("--langs", required=True, help="Comma-separated language codes, e.g. 'pl,cs' or 'uk,pl,cs,de'")
    p_compare.add_argument("--primary-lang", help="Primary language for topic translation search")
    p_compare.add_argument("--period", default="2y", choices=["6m", "1y", "2y", "3y"], help="Historical lookback")
    p_compare.add_argument("--start", help="Start date YYYYMMDD")
    p_compare.add_argument("--end", help="End date YYYYMMDD")
    p_compare.add_argument("--agent", default="user", choices=["user", "all-agents", "spider"], help="Traffic filter")
    p_compare.add_argument("--forecast", action="store_true", help="Generate Shumway autoregressive forward forecast")
    p_compare.add_argument("--forecast-days", type=int, default=90, help="Forecast horizon in days (default: 90)")
    p_compare.add_argument("--output-dir", default="./artifacts", help="Directory for charts and PDF report")
    p_compare.add_argument("--verify", action="store_true", help="Run deterministic verification gate on generated artifacts")

    # benchmark (dedicated subparser alias)
    p_bench = subparsers.add_parser("benchmark", help="Benchmark multiple competing topics across language Wikipedia editions")
    p_bench.add_argument("--topics", required=True, help="Comma-separated topic names to benchmark (e.g. 'Pilates,Calisthenics,Stretching')")
    p_bench.add_argument("--langs", required=True, help="Comma-separated language codes, e.g. 'de,fr'")
    p_bench.add_argument("--primary-lang", help="Primary language for topic translation search")
    p_bench.add_argument("--period", default="2y", choices=["6m", "1y", "2y", "3y"], help="Historical lookback")
    p_bench.add_argument("--start", help="Start date YYYYMMDD")
    p_bench.add_argument("--end", help="End date YYYYMMDD")
    p_bench.add_argument("--agent", default="user", choices=["user", "all-agents", "spider"], help="Traffic filter")
    p_bench.add_argument("--forecast", action="store_true", help="Generate Shumway autoregressive forward forecast")
    p_bench.add_argument("--forecast-days", type=int, default=90, help="Forecast horizon in days (default: 90)")
    p_bench.add_argument("--output-dir", default="./artifacts", help="Directory for charts and PDF report")
    p_bench.add_argument("--verify", action="store_true", help="Run deterministic verification gate on generated artifacts")

    # report (alias to compare or analyze with default export)
    p_report = subparsers.add_parser("report", help="Generate full executive brief with PDF and charts")
    p_report.add_argument("--topic", help="Topic name or concept")
    p_report.add_argument("--topics", help="Comma-separated topic names for multi-topic benchmarking")
    p_report.add_argument("--langs", default="pl,cs,uk", help="Comma-separated language codes")
    p_report.add_argument("--primary-lang", help="Primary language for topic translation search")
    p_report.add_argument("--period", default="2y", help="Historical lookback")
    p_report.add_argument("--start", help="Start date YYYYMMDD")
    p_report.add_argument("--end", help="End date YYYYMMDD")
    p_report.add_argument("--agent", default="user", help="Traffic filter")
    p_report.add_argument("--forecast", action="store_true", help="Generate Shumway autoregressive forward forecast")
    p_report.add_argument("--forecast-days", type=int, default=90, help="Forecast horizon in days (default: 90)")
    p_report.add_argument("--output-dir", default="./artifacts", help="Directory for charts and PDF report")
    p_report.add_argument("--verify", action="store_true", help="Run deterministic verification gate on generated artifacts")

    # cluster (Tibshirani K-Means)
    p_cluster = subparsers.add_parser("cluster", help="K-Means clustering of multilingual markets into business cohorts (Tibshirani ML)")
    p_cluster.add_argument("--topic", required=True, help="Topic name or concept")
    p_cluster.add_argument("--langs", default="en,de,pl,uk,cs,es", help="Comma-separated language codes")
    p_cluster.add_argument("--primary-lang", help="Primary language for topic translation search")
    p_cluster.add_argument("--period", default="2y", choices=["6m", "1y", "2y", "3y"], help="Historical lookback")
    p_cluster.add_argument("--start", help="Start date YYYYMMDD")
    p_cluster.add_argument("--end", help="End date YYYYMMDD")
    p_cluster.add_argument("--k", type=int, default=3, help="Number of clusters (default: 3)")
    p_cluster.add_argument("--agent", default="user", choices=["user", "all-agents", "spider"], help="Traffic filter")
    p_cluster.add_argument("--output-dir", default="./artifacts", help="Directory for charts and PDF report")
    p_cluster.add_argument("--verify", action="store_true", help="Run deterministic verification gate on generated artifacts")

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        return 0

    if args.subcommand in ("compare", "report"):
        if not getattr(args, "topic", None) and not getattr(args, "topics", None):
            parser.error("Subcommand 'compare' requires at least one of --topic or --topics.")

    if args.subcommand == "analyze":
        return cmd_analyze(args)
    elif args.subcommand in ("compare", "report", "benchmark"):
        return cmd_compare(args)
    elif args.subcommand == "cluster":
        return cmd_cluster(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
