"""
Visualizer module for Wikipedia Market Intelligence.
Generates clean, publication-ready high-DPI charts for single topic trends and multi-language comparisons.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")  # Headless backend for server/CLI environments
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime


PALETTE = [
    "#2563eb",  # Blue
    "#10b981",  # Emerald
    "#f59e0b",  # Amber
    "#8b5cf6",  # Violet
    "#ec4899",  # Pink
    "#06b6d4",  # Cyan
    "#f97316",  # Orange
]


def set_plot_style() -> None:
    """Configures clean, modern typography and styling for plots."""
    plt.rcParams["font.sans-serif"] = ["Segoe UI", "DejaVu Sans", "Helvetica", "Arial"]
    plt.rcParams["axes.edgecolor"] = "#e2e8f0"
    plt.rcParams["axes.linewidth"] = 0.8
    plt.rcParams["grid.color"] = "#f1f5f9"
    plt.rcParams["grid.linestyle"] = "--"
    plt.rcParams["grid.linewidth"] = 0.6


def plot_single_topic_trend(
    dates: List[datetime],
    views: List[float],
    baseline: List[float],
    spikes: List[Dict[str, Any]],
    topic: str,
    lang: str,
    trust_score: float,
    verdict: str,
    output_path: str | Path,
    kalman_trend: Optional[List[float]] = None,
    forecast: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Plots daily views with 30-day moving median baseline, Kalman filtered latent state,
    anomalous spikes, and optional 90-day forward-looking prediction interval.
    """
    set_plot_style()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10.5, 5.2), dpi=200)

    # 1. Raw daily views as light area/line
    ax.plot(
        dates,
        views,
        color="#94a3b8",
        alpha=0.40,
        linewidth=0.85,
        label="Raw Daily Pageviews",
    )
    ax.fill_between(dates, views, alpha=0.06, color="#3b82f6")

    # 2. Robust 30-day baseline trend line
    if baseline:
        ax.plot(
            dates,
            baseline,
            color="#3b82f6",
            linewidth=1.6,
            linestyle="--",
            alpha=0.75,
            label="30-Day Median Baseline",
        )

    # 3. Shumway: Kalman Filtered & Smoothed Latent Trend
    if kalman_trend and len(kalman_trend) == len(dates):
        ax.plot(
            dates,
            kalman_trend,
            color="#1d4ed8",
            linewidth=2.4,
            label="Kalman Filtered Organic Trend (Shumway)",
        )

    # 4. Highlight top spikes
    if spikes:
        spike_dates = [datetime.strptime(s["date"], "%Y-%m-%d") for s in spikes[:5]]
        spike_vals = [s["views"] for s in spikes[:5]]
        ax.scatter(
            spike_dates,
            spike_vals,
            color="#ef4444",
            s=42,
            zorder=5,
            edgecolors="#991b1b",
            label="Viral / News Spikes",
        )

    # 5. Shumway: 90-day Forward Forecast & 95% Confidence Band
    if forecast and "point_forecast" in forecast and dates:
        from datetime import timedelta
        fc_points = forecast["point_forecast"]
        fc_low = forecast["lower_95"]
        fc_high = forecast["upper_95"]
        last_dt = dates[-1]
        fc_dates = [last_dt + timedelta(days=i) for i in range(1, len(fc_points) + 1)]

        ax.plot(
            fc_dates,
            fc_points,
            color="#8b5cf6",
            linewidth=2.0,
            linestyle="-.",
            label="90-Day Projection (Kalman/Shumway)",
        )
        ax.fill_between(
            fc_dates,
            fc_low,
            fc_high,
            color="#8b5cf6",
            alpha=0.20,
            label="95% Confidence Interval",
        )

    # Styling & Labels
    ax.set_title(
        f"Market Dynamics: {topic} ({lang.upper()}.wikipedia)\n"
        f"Trust Score: {trust_score}/100 — {verdict}",
        fontsize=11.5,
        fontweight="bold",
        pad=12,
        color="#0f172a",
    )
    ax.set_ylabel("Daily Pageviews", fontsize=9.5, fontweight="semibold", color="#334155")
    ax.grid(True, alpha=0.6)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.autofmt_xdate()

    # Legend & layout
    ax.legend(
        frameon=True,
        facecolor="#ffffff",
        edgecolor="#e2e8f0",
        fontsize=8.5,
        loc="upper right",
    )
    plt.tight_layout()

    fig.savefig(output_path, format="png", bbox_inches="tight")
    plt.close(fig)
    return output_path



def plot_cross_language_comparison(
    market_data: List[Dict[str, Any]],
    topic: str,
    output_path: str | Path,
) -> Path:
    """
    Plots comparative charts across language editions:
    Subplot 1: Total Volume & Growth
    Subplot 2: Trust Score & Normalized Market Share
    """
    set_plot_style()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=200)

    langs = [m["language"].upper() for m in market_data]
    total_views = [m["summary"]["total_views"] for m in market_data]
    yoy_growths = [m["growth"]["yoy_growth_percent"] for m in market_data]
    trust_scores = [m["trust_metrics"]["trust_score"] for m in market_data]
    norm_views = [m.get("normalized_views_per_million") or 0.0 for m in market_data]

    # Chart 1: Total Pageviews + YoY Growth %
    colors = PALETTE[: len(langs)]
    bars = ax1.bar(langs, total_views, color=colors, alpha=0.85, edgecolor="#ffffff", width=0.55)
    ax1.set_title(f"Audience Volume: '{topic}'", fontsize=11, fontweight="bold", pad=10)
    ax1.set_ylabel("Total Pageviews", fontsize=10, fontweight="semibold")
    ax1.grid(True, axis="y", alpha=0.6)

    # Annotate YoY on bars
    for bar, yoy in zip(bars, yoy_growths):
        h = bar.get_height()
        sign = "+" if yoy > 0 else ""
        ax1.text(
            bar.get_x() + bar.get_width() / 2.0,
            h + (max(total_views) * 0.02),
            f"{int(h):,}\n({sign}{yoy:.1f}%)",
            ha="center",
            va="bottom",
            fontsize=8.5,
            fontweight="bold",
            color="#1e293b",
        )

    # Chart 2: Trust Score vs Normalized Market Share
    # If normalized views exist, plot them with Trust Score coloring
    if any(v > 0 for v in norm_views):
        bars2 = ax2.bar(langs, norm_views, color="#6366f1", alpha=0.8, edgecolor="#ffffff", width=0.55)
        ax2.set_title("Normalized Interest (Views per 1M Total Wiki Views)", fontsize=11, fontweight="bold", pad=10)
        ax2.set_ylabel("Views / 1M Project Pageviews", fontsize=10, fontweight="semibold")
        ax2.grid(True, axis="y", alpha=0.6)

        for bar, t_score in zip(bars2, trust_scores):
            h = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2.0,
                h + (max(norm_views) * 0.02),
                f"{h:.1f}\n[Trust: {t_score:.0f}]",
                ha="center",
                va="bottom",
                fontsize=8.5,
                fontweight="bold",
                color="#1e293b",
            )
    else:
        # Plot Trust Scores directly
        bars2 = ax2.bar(langs, trust_scores, color="#059669", alpha=0.8, width=0.55)
        ax2.set_title("Trust & Reliability Score (0-100)", fontsize=11, fontweight="bold", pad=10)
        ax2.set_ylabel("Trust Score", fontsize=10, fontweight="semibold")
        ax2.set_ylim(0, 110)
        ax2.grid(True, axis="y", alpha=0.6)
        for bar, t in zip(bars2, trust_scores):
            ax2.text(
                bar.get_x() + bar.get_width() / 2.0,
                t + 2,
                f"{t:.1f}",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )

    plt.suptitle(
        f"Cross-Language Market Comparison for '{topic}'",
        fontsize=13,
        fontweight="bold",
        y=1.02,
        color="#0f172a",
    )
    plt.tight_layout()

    fig.savefig(output_path, format="png", bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_market_clusters(
    clustered_markets: List[Dict[str, Any]],
    topic: str,
    output_path: str | Path,
) -> Path:
    """
    Tibshirani et al. (Chapter 10): 2D Market Cluster Map.
    Plots markets along axes of Total Views (log scale) vs Trust Score,
    colored by assigned K-Means business cohorts.
    """
    set_plot_style()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(9, 5.5), dpi=200)

    cohort_colors = {
        0: "#2563eb",  # Blue
        1: "#10b981",  # Green
        2: "#f59e0b",  # Amber
        3: "#ef4444",  # Red
    }

    seen_cohorts = set()
    for m in clustered_markets:
        c_id = m.get("cluster_id", 0)
        c_name = m.get("cohort_name", f"Cluster {c_id}")
        v_val = m.get("total_views")
        if v_val is None and "summary" in m and isinstance(m["summary"], dict):
            v_val = m["summary"].get("total_views", 1)
        views = float(v_val or 1)

        t_val = m.get("trust_score")
        if t_val is None and "trust_metrics" in m and isinstance(m["trust_metrics"], dict):
            t_val = m["trust_metrics"].get("trust_score", 50)
        trust = float(t_val if t_val is not None else 50)

        lang = m.get("language", "").upper()
        color = cohort_colors.get(c_id % len(cohort_colors), "#64748b")

        label = c_name if c_id not in seen_cohorts else None
        seen_cohorts.add(c_id)

        ax.scatter(
            views,
            trust,
            color=color,
            s=120,
            alpha=0.85,
            edgecolors="#1e293b",
            linewidth=1.2,
            zorder=4,
            label=label,
        )
        ax.text(
            views * 1.08,
            trust + 0.8,
            lang,
            fontsize=9.5,
            fontweight="bold",
            color="#0f172a",
            va="center",
        )

    ax.set_xscale("log")
    ax.set_title(
        f"K-Means Market Cohort Clustering for '{topic}'",
        fontsize=12,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Total Pageviews (Log Scale)", fontsize=9.5, fontweight="semibold")
    ax.set_ylabel("Trust & Reliability Score (0-100)", fontsize=9.5, fontweight="semibold")
    ax.grid(True, which="both", alpha=0.5)
    ax.legend(
        frameon=True,
        facecolor="#ffffff",
        edgecolor="#e2e8f0",
        fontsize=8.5,
        loc="lower right",
    )
    plt.tight_layout()

    fig.savefig(output_path, format="png", bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_multi_topic_benchmark(
    benchmark_data: Dict[str, Dict[str, Any]],
    topics: List[str],
    langs: List[str],
    output_path: str | Path,
) -> Path:
    """
    Plots a multi-topic cross-language benchmark dashboard (2x2 grid):
    - Subplot (0,0): Total Audience Volume (Views)
    - Subplot (0,1): YoY Growth Dynamics %
    - Subplot (1,0): Trust Score & 95% Bootstrap CI
    - Subplot (1,1): Normalized Market Share (Views / 1M Project Views)
    """
    set_plot_style()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(12, 6.4), dpi=200)

    # Color mapping for languages
    lang_palette = ["#2563eb", "#ec4899", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4"]
    lang_colors = {l: lang_palette[i % len(lang_palette)] for i, l in enumerate(langs)}

    num_topics = len(topics)
    x = np.arange(num_topics)
    num_langs = len(langs)
    total_bar_width = 0.75
    bar_width = total_bar_width / max(1, num_langs)

    # (0,0) Total Volume
    ax = axes[0, 0]
    for idx, l in enumerate(langs):
        offset = (idx - (num_langs - 1) / 2) * bar_width
        views = [
            benchmark_data.get(t, {}).get(l, {}).get("summary", {}).get("total_views", 0)
            for t in topics
        ]
        bars = ax.bar(x + offset, views, bar_width, label=l.upper(), color=lang_colors[l], alpha=0.85)
        for b in bars:
            h = b.get_height()
            if h > 0:
                txt = f"{int(h/1000)}k" if h >= 1000 else str(int(h))
                ax.text(b.get_x() + b.get_width()/2, h + (max(views) * 0.02 if views else 1), txt, ha="center", va="bottom", fontsize=7.5, fontweight="bold")
    ax.set_title("1. Total Audience Volume (Pageviews)", fontsize=11, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(topics, fontweight="semibold")
    ax.set_ylabel("Total Pageviews")
    ax.legend(frameon=True, fontsize=8.5)
    ax.grid(True, axis="y", alpha=0.6)

    # (0,1) YoY Growth Rate
    ax = axes[0, 1]
    ax.axhline(0, color="#64748b", linestyle="--", linewidth=0.9)
    for idx, l in enumerate(langs):
        offset = (idx - (num_langs - 1) / 2) * bar_width
        growths = [
            benchmark_data.get(t, {}).get(l, {}).get("growth", {}).get("yoy_growth_percent", 0.0)
            for t in topics
        ]
        bars = ax.bar(x + offset, growths, bar_width, label=l.upper(), color=lang_colors[l], alpha=0.85)
        for b in bars:
            h = b.get_height()
            va = "bottom" if h >= 0 else "top"
            sign = "+" if h > 0 else ""
            ax.text(b.get_x() + b.get_width()/2, h + (2 if h >= 0 else -3), f"{sign}{h:.1f}%", ha="center", va=va, fontsize=7.5, fontweight="bold")
    ax.set_title("2. YoY Growth Rate % (Dynamics & Momentum)", fontsize=11, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(topics, fontweight="semibold")
    ax.set_ylabel("YoY Growth %")
    ax.legend(frameon=True, fontsize=8.5)
    ax.grid(True, axis="y", alpha=0.6)

    # (1,0) Trust Score with 95% Bootstrap CI
    ax = axes[1, 0]
    for idx, l in enumerate(langs):
        offset = (idx - (num_langs - 1) / 2) * bar_width
        scores = [
            benchmark_data.get(t, {}).get(l, {}).get("trust_metrics", {}).get("trust_score", 50.0)
            for t in topics
        ]
        yerr_lower = []
        yerr_upper = []
        for t in topics:
            m = benchmark_data.get(t, {}).get(l, {})
            ts = m.get("trust_metrics", {}).get("trust_score", 50.0)
            ci = m.get("bootstrap_ci") or {}
            low = ci.get("low_95", ts)
            high = ci.get("high_95", ts)
            yerr_lower.append(max(0.0, ts - low))
            yerr_upper.append(max(0.0, high - ts))

        yerr = [yerr_lower, yerr_upper]
        ax.bar(x + offset, scores, bar_width, label=l.upper(), color=lang_colors[l], alpha=0.85, yerr=yerr, capsize=3)
    ax.set_title("3. Trust & Baseline Stability Score (0-100, 95% CI)", fontsize=11, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(topics, fontweight="semibold")
    ax.set_ylabel("Trust Score")
    ax.set_ylim(0, 115)
    ax.legend(frameon=True, fontsize=8.5, loc="lower right")
    ax.grid(True, axis="y", alpha=0.6)

    # (1,1) Normalized Attention
    ax = axes[1, 1]
    for idx, l in enumerate(langs):
        offset = (idx - (num_langs - 1) / 2) * bar_width
        norm_v = [
            benchmark_data.get(t, {}).get(l, {}).get("normalized_views_per_million") or 0.0
            for t in topics
        ]
        ax.bar(x + offset, norm_v, bar_width, label=l.upper(), color=lang_colors[l], alpha=0.85)
    ax.set_title("4. Normalized Market Share (Views / 1M Total Wiki Views)", fontsize=11, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(topics, fontweight="semibold")
    ax.set_ylabel("Views / 1M Project Views")
    ax.legend(frameon=True, fontsize=8.5)
    ax.grid(True, axis="y", alpha=0.6)

    topic_names_str = " vs ".join(topics[:3])
    if len(topics) > 3:
        topic_names_str += f" (+{len(topics) - 3} more)"
    fig.suptitle(f"Cross-Topic Market Benchmark: {topic_names_str}", fontsize=13, fontweight="bold", y=0.99)
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            fig.tight_layout(rect=[0, 0.02, 1, 0.96])
    except Exception:
        fig.subplots_adjust(top=0.92, bottom=0.08, left=0.07, right=0.98, hspace=0.34, wspace=0.22)
    fig.savefig(output_path, format="png", bbox_inches="tight")
    plt.close(fig)
    return output_path

