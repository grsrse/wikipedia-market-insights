#!/usr/bin/env python3
"""
Ambient Market Radar for Wikipedia Market Insights.
Implements the 5-Phase Ambient Loop and Restraint Budget Architecture from
'Building Ambient AI Agents' (Frederick Joseph Patton & Leman Pinar Patton).

Phases:
1. Sense: Continuous / scheduled ingestion of topic watchlists across Wikipedia languages.
2. Interpret: Anomaly detection, rolling median trend extraction, and Council of Rivals scoring.
3. Decide: Mathematical Restraint Budget evaluation (S >= 0.70 required to trigger alert).
4. Act: In-situ generation of verified 1-page executive alert memos and charts.
5. Learn: Telemetry persistence and fatigue penalty calibration in radar_state.json.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure scripts dir is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import WikimediaClient
from analyzer import TopicAnalyzer
from visualizer import plot_single_topic_trend
from report_pdf import PDFReportGenerator
from verify_memo import verify_pdf, verify_chart, verify_json

# Default Watchlist of high-velocity consumer search themes
DEFAULT_WATCHLIST = [
    "Intermittent fasting",
    "Creatine",
    "Cold plunge",
    "Pomodoro Technique",
    "Spaced repetition",
    "Generative artificial intelligence",
]

DEFAULT_LANGUAGES = ["en", "pl", "de"]


class AmbientRadarEngine:
    """Orchestrates the 5-Phase Ambient Loop for proactive market intelligence."""

    def __init__(
        self,
        output_dir: Path,
        cache_dir: Optional[Path] = None,
        restraint_threshold: float = 0.70,
        decay_lambda: float = 0.35,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.cache_dir = Path(cache_dir) if cache_dir else self.output_dir / ".radar_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.cache_dir / "radar_state.json"
        self.restraint_threshold = restraint_threshold
        self.decay_lambda = decay_lambda

        self.client = WikimediaClient(cache_dir=str(self.cache_dir / "http"))
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "alerts_history": [],
            "recent_alerts_count": 0,
            "last_alert_timestamp": 0,
            "fatigue_penalty": 0.0,
        }

    def _save_state(self) -> None:
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def calculate_restraint_score(
        self,
        trust_score: float,
        growth_pct: float,
        spike_ratio: float,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Evaluates Patton's Restraint Budget Equation:
        S = Confidence * Severity * exp(-lambda * N_recent) * (1 - FatiguePenalty)
        """
        now = time.time()
        # Confidence derived from Trust Score
        confidence = max(0.0, min(1.0, trust_score / 100.0))

        # Severity / Business Opportunity derived from positive organic baseline growth
        opportunity = max(0.2, min(1.0, (growth_pct + 10.0) / 60.0))

        # Update decay and fatigue
        recent_count = self.state.get("recent_alerts_count", 0)
        last_alert = self.state.get("last_alert_timestamp", 0)
        fatigue_penalty = self.state.get("fatigue_penalty", 0.0)

        # Decay alert count and fatigue if time has elapsed since a previous alert
        if last_alert > 0:
            time_since_last = now - last_alert
            if time_since_last > 86400:
                recent_count = max(0, recent_count - int(time_since_last // 86400))
                self.state["recent_alerts_count"] = recent_count

            if time_since_last > 3600:
                fatigue_penalty *= math.exp(-0.1 * (time_since_last / 3600.0))
                self.state["fatigue_penalty"] = round(fatigue_penalty, 3)

        decay_term = math.exp(-self.decay_lambda * recent_count)
        restraint_score = confidence * opportunity * decay_term * (1.0 - fatigue_penalty)
        restraint_score = round(max(0.0, min(1.0, restraint_score)), 3)

        components = {
            "confidence": round(confidence, 3),
            "opportunity": round(opportunity, 3),
            "decay_factor": round(decay_term, 3),
            "fatigue_penalty": round(fatigue_penalty, 3),
            "recent_alerts_count": recent_count,
        }
        return restraint_score, components

    def scan_topic(
        self,
        topic: str,
        languages: List[str],
        days: int = 90,
        force: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Executes the 5-phase loop on a single candidate topic."""
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=days)
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        print(f"\n[Radar: Sense] Scanning '{topic}' across languages: {', '.join(languages)}...")

        # Phase 1: Sense
        resolved_titles = self.client.resolve_topic_across_languages(
            topic=topic,
            primary_lang="en",
            target_langs=languages,
        )

        lang_data: Dict[str, Any] = {}
        for lang in languages:
            art_title = resolved_titles.get(lang) or topic
            items = self.client.get_article_pageviews(
                project=f"{lang}.wikipedia",
                article=art_title,
                start=start_str,
                end=end_str,
            )
            if items:
                lang_data[lang] = {
                    "title": art_title,
                    "items": items,
                }

        if not lang_data:
            print(f"  → No data discovered for '{topic}'. Observing silently.")
            return None

        # Phase 2: Interpret
        primary_lang = "en" if "en" in lang_data else list(lang_data.keys())[0]
        analyzer = TopicAnalyzer(lang_data[primary_lang]["items"])
        analysis = analyzer.to_analysis_dict(
            topic=topic,
            lang=primary_lang,
            article_title=lang_data[primary_lang]["title"],
        )

        trust = analysis["trust_metrics"]["trust_score"]
        growth = analysis["growth"].get("baseline_median_growth_pct", 0.0)
        spikes = analysis["spikes"]["ratio"]

        # Phase 3: Decide (Restraint Budget)
        restraint_score, components = self.calculate_restraint_score(
            trust_score=trust,
            growth_pct=growth,
            spike_ratio=spikes,
        )

        verdict_str = analysis["council_of_rivals"]["final_verdict"]["verdict"]
        print(f"  → Analysis: Trust={trust:.1f} | Growth={growth:+.1f}% | Council Verdict={verdict_str}")
        print(f"  → Restraint Budget: Score={restraint_score:.3f} (Threshold: {self.restraint_threshold})")

        should_act = force or (restraint_score >= self.restraint_threshold and verdict_str != "DO_NOT_LAUNCH")

        if not should_act:
            print(f"  [Radar: Restraint] Action suppressed (Score {restraint_score:.3f} < {self.restraint_threshold}). Silent observation logged.")
            return None

        # Phase 4: Act (Tier 3: Executive Memo & Visualizer)
        print(f"  🚀 [Radar: Act] Restraint threshold exceeded! Generating Verified 1-Page Memo...")
        slug = topic.lower().replace(" ", "_")
        chart_path = self.output_dir / f"trend_alert_{slug}.png"
        pdf_path = self.output_dir / f"market_memo_alert_{slug}.pdf"
        json_path = self.output_dir / f"alert_{slug}.json"

        # Generate Chart
        spikes_info = analyzer.detect_spikes()
        plot_single_topic_trend(
            dates=analyzer.dates,
            views=analyzer.views,
            baseline=spikes_info["rolling_baseline"],
            spikes=spikes_info["spikes"],
            topic=topic,
            lang=primary_lang,
            trust_score=trust,
            verdict=verdict_str,
            output_path=chart_path,
        )

        # Generate PDF Memo
        pdf_generator = PDFReportGenerator(pdf_path)
        pdf_generator.generate_single_topic_report(
            analysis=analysis,
            chart_image_path=chart_path,
        )

        # Attach radar metadata to alert JSON
        alert_record = {
            **analysis,
            "radar_metadata": {
                "timestamp": datetime.now().isoformat(),
                "restraint_score": restraint_score,
                "restraint_components": components,
            },
            "artifacts": {
                "pdf": str(pdf_path),
                "chart": str(chart_path),
            },
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(alert_record, f, indent=2)

        # Deterministic Verification Gate
        pdf_errs = verify_pdf(pdf_path)
        chart_errs = verify_chart(chart_path)
        json_errs = verify_json(json_path)
        if pdf_errs or chart_errs or json_errs:
            print(f"  ⚠️ Warning: Verification Gate detected issues in generated alert: {pdf_errs + chart_errs + json_errs}")
        else:
            print(f"  ✅ Verified: Alert memo generated and verified as strictly 1-page.")

        # Phase 5: Learn
        self.state["alerts_history"].append({
            "timestamp": time.time(),
            "topic": topic,
            "score": restraint_score,
        })
        self.state["recent_alerts_count"] = self.state.get("recent_alerts_count", 0) + 1
        self.state["last_alert_timestamp"] = time.time()
        self.state["fatigue_penalty"] = min(0.60, self.state.get("fatigue_penalty", 0.0) + 0.15)
        self._save_state()

        return alert_record

    def run_scan(self, watchlist: List[str], languages: List[str], force: bool = False) -> List[Dict[str, Any]]:
        """Scans all topics in watchlist once."""
        alerts = []
        for topic in watchlist:
            rec = self.scan_topic(topic=topic, languages=languages, force=force)
            if rec:
                alerts.append(rec)
        return alerts


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="Ambient Market Radar for Wikipedia Market Insights.")
    parser.add_argument("--scan", action="store_true", help="Execute a single pass over the watchlist.")
    parser.add_argument("--watch", action="store_true", help="Run continuously in background monitor mode.")
    parser.add_argument("--interval", type=int, default=3600, help="Interval in seconds between passes in --watch mode.")
    parser.add_argument("--watchlist", type=str, help="Comma-separated topics or path to a JSON file.")
    parser.add_argument("--languages", type=str, default="en,pl,de", help="Comma-separated language codes.")
    parser.add_argument("--output-dir", type=str, default="artifacts/alerts", help="Output directory for alert memos.")
    parser.add_argument("--threshold", type=float, default=0.70, help="Restraint score threshold (0.0 to 1.0).")
    parser.add_argument("--force", action="store_true", help="Bypass restraint budget filter (for testing).")

    args = parser.parse_args()

    # Parse watchlist
    if args.watchlist:
        if os.path.exists(args.watchlist):
            with open(args.watchlist, "r", encoding="utf-8") as f:
                watchlist = json.load(f)
        else:
            watchlist = [t.strip() for t in args.watchlist.split(",") if t.strip()]
    else:
        watchlist = DEFAULT_WATCHLIST

    languages = [l.strip().lower() for l in args.languages.split(",") if l.strip()]
    output_dir = Path(args.output_dir)

    radar = AmbientRadarEngine(
        output_dir=output_dir,
        restraint_threshold=args.threshold,
    )

    print("=" * 70)
    print("📡 Ambient Market Radar Activated")
    print(f"   Watchlist Topics : {len(watchlist)}")
    print(f"   Languages        : {', '.join(languages)}")
    print(f"   Restraint Barrier: S >= {args.threshold:.2f}")
    print(f"   Output Directory : {output_dir.resolve()}")
    print("=" * 70)

    if args.watch:
        print(f"Starting continuous monitor (cycle interval: {args.interval}s). Press Ctrl+C to stop.")
        try:
            while True:
                radar.run_scan(watchlist=watchlist, languages=languages, force=args.force)
                print(f"\nCycle complete. Sleeping for {args.interval} seconds...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nAmbient Market Radar stopped by user.")
            return 0
    else:
        # Default to single scan
        alerts = radar.run_scan(watchlist=watchlist, languages=languages, force=args.force)
        print("\n" + "=" * 70)
        print(f"Scan complete. Emitted {len(alerts)} actionable alert memo(s).")
        print("=" * 70)
        return 0


if __name__ == "__main__":
    sys.exit(main())
