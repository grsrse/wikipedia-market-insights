# Institutional Reflexion Ledger: Wikipedia Market Insights Gotchas

This ledger captures empirical edge cases, API behavioral quirks, and failure modes discovered during the development and real-world deployment of the `wikipedia-market-insights` skill.

---

## 1. MediaWiki API & AQS Protocol Gotchas

### Bot vs. User Traffic (`agent=user`)
- **Failure Mode**: Querying `agent=all-agents` includes automated search engine crawlers, academic scrapers, and Wikipedia indexing bots. In niche or non-English topics (e.g. `uk.wikipedia`), bot traffic can constitute 60–80% of total recorded hits, causing artificial spikes and false demand signals.
- **Rule**: Always enforce `agent=user` in the Analytics Query Service (AQS) endpoint.

### Interlanguage Link Discrepancies
- **Failure Mode**: Literal keyword translation (e.g., translating "intermittent fasting" literally into Polish as "przerywany post" instead of the canonical Wikipedia lemma "post przerywany") produces 404 Not Found errors or redirects to broader general diet pages.
- **Rule**: Always use the MediaWiki API action `query&prop=langlinks` on the source article (or Wikidata entity ID) to resolve the exact canonical title used in the target language edition.

### URL Encoding of Special Characters
- **Failure Mode**: Slashing characters, accented characters (e.g. Polish `ł, ą, ę`, Czech `ř, š`, Ukrainian `і, ї, є`) and spaces in article titles can cause HTTP 400 or corrupted statistics if double-encoded or unquoted.
- **Rule**: Article titles must be normalized by replacing spaces with underscores (`_`) before passing to the REST API, without re-encoding existing percent-escapes.

---

## 2. Statistical Anomaly & Outlier Gotchas

### The Solar Eclipse Anomaly (Media-Driven PR Event)
- **Failure Mode**: On August 12, 2026, the Ukrainian Wikipedia article `Астрономія` experienced an unprecedented single-day traffic spike (8,412 views vs. a median of 412 views) due to a total solar eclipse visible across Europe. Naive algorithms that compute Average Daily Views would calculate an artificially inflated market growth (+34%).
- **Rule**: Always use the Median Absolute Deviation (MAD) rolling baseline rather than the mean. The `detect_spikes()` method isolates days exceeding $2.5 \times \text{IQR}$ and attributes that volume to `spike_volume_ratio`, penalizing the Trust Score.

### Seasonality in Health & Diet Topics
- **Failure Mode**: Topics like "Intermittent Fasting" experience predictable 200–300% volume surges in early January (New Year's resolutions) and late May (pre-summer fitness).
- **Rule**: When evaluating MoM (Month-over-Month) growth, require multi-quarter or YoY (Year-over-Year) baseline comparison to avoid mistaking annual seasonality for secular market breakout.

---

## 3. Environment & Operating System Gotchas

### Windows Console Encoding (cp1251 / cp936 / cp1252)
- **Failure Mode**: Python subprocesses or scripts printing non-ASCII article titles (e.g. Ukrainian `Астрономія`, Polish `Post przerywany`) to stdout crash on Windows with:
  `UnicodeEncodeError: 'charmap' codec can't encode character ...`
- **Rule**: In every script entry point, explicitly reconfigure `sys.stdout` and `sys.stderr`:
  ```python
  import sys
  for stream in (sys.stdout, sys.stderr):
      try:
          stream.reconfigure(encoding="utf-8")
      except (AttributeError, ValueError):
          pass
  ```

---

## 4. ReportLab PDF 1-Page Layout Constraints

### The 1-Page Overflow Cliff
- **Failure Mode**: Adding an extra row to a table or increasing paragraph font size by 1 point pushes a single orphan line onto Page 2, breaking the executive summary requirement.
- **Rule**:
  1. Set document margins strictly to `0.4 * inch` (28.8 pt).
  2. Embed charts with explicit dimensions: width `7.2 * inch`, height `2.5 * inch`.
  3. Keep metric tables to exactly 4 rows with row height $\le 16\text{ pt}$.
  4. Always pipe generated PDFs through `scripts/verify_memo.py` to assert `len(reader.pages) == 1`.
