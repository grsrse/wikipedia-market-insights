#!/usr/bin/env python3
"""
Automated Verification Gate for Wikipedia Market Insights Artifacts.
Inspired by Lucas Soares' Verification Skills architecture.

Ensures deterministic quality standards:
1. PDF page count strictly equals 1 (preventing layout overflow).
2. Chart artifacts are valid, non-empty PNG images with magic bytes.
3. Structured JSON output conforms to required analytical schema and trust thresholds.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


def verify_pdf(
    pdf_path: Path,
    expected_pages: Optional[int] = None,
    max_pages: Optional[int] = None,
) -> List[str]:
    """Validates that PDF exists, is non-empty, and satisfies page count requirements."""
    errors = []
    if not pdf_path.exists():
        return [f"PDF file not found: {pdf_path}"]

    size = pdf_path.stat().st_size
    if size < 1024:
        errors.append(f"PDF file is suspiciously small ({size} bytes): {pdf_path}")

    if PdfReader is not None:
        try:
            reader = PdfReader(str(pdf_path))
            num_pages = len(reader.pages)
            if expected_pages is not None:
                if num_pages != expected_pages:
                    errors.append(
                        f"Page count violation: PDF has {num_pages} pages (must be strictly {expected_pages} pages). "
                        f"Check report_pdf.py pagination."
                    )
            elif max_pages is not None:
                if num_pages > max_pages:
                    errors.append(
                        f"Page count violation: PDF has {num_pages} pages (exceeds maximum of {max_pages} pages)."
                    )
            else:
                if num_pages != 1:
                    errors.append(
                        f"Layout constraint violation: PDF has {num_pages} pages (must be strictly 1 page). "
                        f"Reduce font sizes, table padding, or chart dimensions in report_pdf.py."
                    )
        except Exception as e:
            errors.append(f"Failed to read/parse PDF {pdf_path}: {e}")
    else:
        # Fallback check on PDF header if pypdf is unavailable
        content = pdf_path.read_bytes()[:1024]
        if not content.startswith(b"%PDF-"):
            errors.append(f"File {pdf_path} does not have valid %PDF- magic bytes header.")

    return errors


def verify_chart(png_path: Path) -> List[str]:
    """Validates PNG image existence, size, and header magic bytes."""
    errors = []
    if not png_path.exists():
        return [f"Chart PNG file not found: {png_path}"]

    size = png_path.stat().st_size
    if size < 5120:  # < 5 KB indicates a blank or broken render
        errors.append(f"Chart file {png_path} is undersized ({size} bytes), likely a blank render.")

    try:
        header = png_path.read_bytes()[:8]
        if header != b"\x89PNG\r\n\x1a\n":
            errors.append(f"Chart {png_path} does not match valid PNG magic header bytes.")
    except Exception as e:
        errors.append(f"Could not read chart header {png_path}: {e}")

    return errors


def verify_json(json_path: Path) -> List[str]:
    """Validates analytical JSON schema, trust metrics, and Council of Rivals outputs."""
    errors = []
    if not json_path.exists():
        return [f"JSON file not found: {json_path}"]

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return [f"Failed to parse JSON {json_path}: {e}"]

    # Check top-level required fields
    required_keys = ["topic", "language", "summary", "growth", "spikes", "trust_metrics"]
    for key in required_keys:
        if key not in data:
            errors.append(f"JSON missing required key: '{key}' in {json_path}")

    # Check trust score
    trust = data.get("trust_metrics", {})
    if not isinstance(trust, dict):
        errors.append(f"'trust_metrics' must be a JSON object in {json_path}")
    else:
        score = trust.get("trust_score")
        if score is None or not isinstance(score, (int, float)):
            errors.append(f"Missing or invalid numeric 'trust_score' in {json_path}")
        elif not (0.0 <= score <= 100.0):
            errors.append(f"Trust score {score} out of bounds [0.0, 100.0] in {json_path}")

    # Check Council of Rivals if present
    council = data.get("council_of_rivals")
    if council:
        for role in ["ua_growth_marketer", "risk_epistemology_auditor", "monetization_strategist", "final_verdict"]:
            if role not in council:
                errors.append(f"Council of Rivals missing perspective: '{role}' in {json_path}")

    # Check Bootstrap Confidence Interval if present (Tibshirani ML)
    boot = data.get("bootstrap_ci")
    if boot:
        if not isinstance(boot, dict):
            errors.append(f"'bootstrap_ci' must be a JSON object in {json_path}")
        else:
            low = boot.get("low_95")
            high = boot.get("high_95")
            if low is None or high is None or not (0.0 <= low <= high <= 100.0):
                errors.append(f"Invalid bootstrap confidence interval [{low}, {high}] in {json_path}")

    # Check Shumway Time Series Forecast if present
    fc = data.get("forecast")
    if fc:
        if not isinstance(fc, dict):
            errors.append(f"'forecast' must be a JSON object in {json_path}")
        else:
            horizon = fc.get("horizon_days")
            pts = fc.get("point_forecast")
            if not isinstance(horizon, int) or horizon <= 0:
                errors.append(f"Invalid forecast horizon_days {horizon} in {json_path}")
            elif not isinstance(pts, list) or len(pts) != horizon:
                errors.append(f"Forecast point_forecast length {len(pts) if pts else 0} != horizon {horizon} in {json_path}")

    return errors


def main() -> int:
    # Ensure stdout/stderr handles UTF-8 on Windows
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(
        description="Automated Verification Gate for Wikipedia Market Insights artifacts."
    )
    parser.add_argument("--pdf", type=Path, help="Path to generated PDF memo.")
    parser.add_argument("--json", type=Path, help="Path to generated analysis JSON.")
    parser.add_argument("--charts", type=Path, nargs="*", help="Paths to chart PNG files.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to automatically discover and verify all PDFs, JSONs, and PNGs.",
    )
    parser.add_argument("--expected-pages", type=int, help="Strict required page count for PDF verification.")
    parser.add_argument("--max-pages", type=int, help="Maximum allowed page count for PDF verification.")

    args = parser.parse_args()
    all_errors: List[str] = []

    pdfs_to_check: List[Path] = [args.pdf] if args.pdf else []
    jsons_to_check: List[Path] = [args.json] if args.json else []
    charts_to_check: List[Path] = list(args.charts or [])

    if args.output_dir and args.output_dir.exists():
        pdfs_to_check.extend(list(args.output_dir.glob("*.pdf")))
        jsons_to_check.extend(list(args.output_dir.glob("*.json")))
        charts_to_check.extend(list(args.output_dir.glob("*.png")))

    # Deduplicate paths
    pdfs_to_check = sorted(list(set(p for p in pdfs_to_check if p)))
    jsons_to_check = sorted(list(set(p for p in jsons_to_check if p)))
    charts_to_check = sorted(list(set(p for p in charts_to_check if p)))

    if not pdfs_to_check and not jsons_to_check and not charts_to_check:
        sys.stderr.write("Verification Gate Error: No artifacts provided to verify (--pdf, --json, --charts, or --output-dir).\n")
        return 1

    # Verify each artifact
    for pdf in pdfs_to_check:
        errs = verify_pdf(pdf, expected_pages=args.expected_pages, max_pages=args.max_pages)
        all_errors.extend(errs)

    for ch in charts_to_check:
        errs = verify_chart(ch)
        all_errors.extend(errs)

    for js in jsons_to_check:
        errs = verify_json(js)
        all_errors.extend(errs)

    if all_errors:
        sys.stderr.write(f"\n❌ Verification Gate Failed with {len(all_errors)} error(s):\n")
        for i, err in enumerate(all_errors, 1):
            sys.stderr.write(f"  {i}. {err}\n")
        return 1

    print("\n✅ Verification Gate Passed: All artifacts satisfy deterministic quality standards.")
    print(f"   - Verified PDFs   : {len(pdfs_to_check)} (strictly 1-page)")
    print(f"   - Verified Charts : {len(charts_to_check)} (valid PNG headers)")
    print(f"   - Verified JSONs  : {len(jsons_to_check)} (schema & Trust Score valid)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
