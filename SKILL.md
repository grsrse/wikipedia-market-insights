---
name: wikipedia-market-insights
description: Analyze Wikipedia reader traffic across languages to validate B2C product hypotheses, detect trend reliability (Trust Score), filter viral spikes, and generate 1-page executive PDF briefs with charts. Use whenever evaluating new course topics, market expansion, language localization, or comparing interest trends across Wikipedia editions.
license: MIT
compatibility: Python 3.9+ with requests, matplotlib, reportlab
metadata:
  author: Genesis Academy Case Solution
  version: "1.0.1"
---

# Wikipedia Market Insights

A quantitative market intelligence skill for B2C founders, product managers, and AI agents. It leverages Wikimedia's official Pageviews API to validate user demand, compare language markets, measure organic trend reliability, and produce executive decision memos.

## When to Use This Skill

Activate this skill when:
- Evaluating whether to launch a new product feature, curriculum topic, or educational course (e.g. "Should we add an Astronomy course to our learning app?").
- Assessing trend trustworthiness (e.g. "Is interest growing organically, or is it distorted by viral news spikes and bots?").
- Prioritizing international market expansion and language localization (e.g. "Compare Polish vs Czech interest for Intermittent Fasting over the last 2 years").
- Generating a shareable, publication-grade **1-page PDF Executive Brief** and visual trend charts for founders and investors.

---

## Core Capabilities & Methodology

1. **Bot & Crawler Elimination**: Enforces `agent=user` filtering in the Wikimedia Analytics Query Service (AQS) to measure genuine human readership.
2. **Automated Interlanguage Topic Mapping**: Translates and resolves article concepts across Wikipedia editions via MediaWiki Interlanguage Links and Wikidata API (no manual keyword guessing needed).
3. **Statistical Trust Score (0–100) & Council of Rivals**:
   - **Baseline Growth**: Computes the trajectory of the 60-day moving median to track core audience expansion.
   - **Spike Impact Ratio**: Isolates transient viral/news anomalies (> 2.5x IQR above median).
   - **Council of Rivals (Soares Architecture)**: Synthesizes 3 independent, uncompromised evaluation lenses:
     1. *UA & Growth Marketer* — evaluates momentum, virality, and paid channel testing.
     2. *Risk & Epistemology Auditor* — evaluates spike fragility and fake news-driven trends.
     3. *Monetization Strategist* — evaluates purchasing power (GDP/ARPU tiering) and pricing models.
4. **Shumway State-Space Kalman Smoothing & Forecasting**:
   - Decomposes noisy daily pageviews into unobserved organic level and trend states ($K_t = 0$ imputation for API dropouts).
   - Projects 90-day forward forecasts with calibrated 95% analytical confidence intervals.
5. **Tibshirani Unsupervised Clustering & Bootstrap Uncertainty**:
   - Groups international markets via K-Means into 4 business cohorts (*Tier 1 Established Core*, *High-Growth Breakthrough*, *Fragile / News-Driven Traps*, *Mature Steady Market*).
   - Resamples residual distributions ($B = 250$) to estimate non-parametric 95% confidence intervals $[TS_{\text{low}}, TS_{\text{high}}]$ for Trust Score.
6. **Market Normalization**: Calculates topic views per 1M total Wikipedia project views, allowing fair comparison between large and small linguistic populations (e.g. Polish vs Czech).
7. **Executive 1-Page PDF Generation & Verification Gate**:
   - Produces a compact, investor-ready A4 PDF document containing KPIs, embedded charts, market rankings, and caveats.
   - Includes deterministic quality gate (`scripts/verify_memo.py`) asserting strictly 1 page, valid PNG magic bytes, and JSON schema integrity.
8. **Ambient Market Radar (Patton Architecture)**:
   - Autonomous background monitor (`scripts/ambient_radar.py`) implementing the 5-phase loop (Sense, Interpret, Decide, Act, Learn).
   - Evaluates the mathematical Restraint Budget ($S \ge 0.70$) to proactively discover breakout topics without notification spam.

---

## Tool Immutability & Universal Agent Contract

> [!IMPORTANT]
> **IMMUTABLE PRODUCTION PACKAGE (FROZEN SKILL):**
> This skill is fully self-contained and hardened. Downstream AI agents (Claude Haiku 4.5, GPT-4o, etc.) **MUST NEVER** attempt to modify Python scripts, monkey-patch internals, or write ad-hoc glue code. All workflows are executed strictly via the deterministic CLI.

### Universal Dimensionality Matrix ($N$ Topics $\times$ $M$ Languages)
The unified CLI automatically normalizes any query dimension and applies the optimal visual layout and PDF structure without runtime code changes:

| Dimensionality | CLI Invocation Example | Generated Artifacts & Structure |
| :--- | :--- | :--- |
| **$1 \times 1$** (Solo Market) | `run.py analyze --topic "A" --lang es` | Single-topic trend chart (Kalman + Spikes) + **strictly 1-page A4 PDF**. |
| **$1 \times M$** (Cross-Language) | `run.py compare --topic "A" --langs "pl,de,fr"` | Cross-language comparison bar chart + **strictly 1-page A4 PDF**. |
| **$N \times 1$** (Battle in 1 Market) | `run.py compare --topics "A,B" --langs "es"` | 2×2 benchmark grid + individual trend charts + **strictly $1 + N$ pages PDF**. |
| **$N \times M$** (Full Benchmark) | `run.py compare --topics "A,B,C" --langs "de,fr"` | 2×2 benchmark grid + cross-market charts + **strictly $1 + N$ pages PDF**. |

### Graceful Degradation Protocol
If an article is missing or returns 404 in Wikipedia for one of the target languages, the CLI does **NOT** fail. It returns `status: "partial_success"` with a structured `warnings` array in JSON, renders the report using available data, and provides the agent with an actionable remediation tip.

---

## Agent Execution Instructions

Run the unified CLI script `scripts/run.py` from the skill directory or workspace root:

> [!NOTE]
> **Invocation Path**:
> - **From repository root / parent directory**: `python wikipedia-market-insights/scripts/run.py ...` (or in standalone skill copies: `python scripts/run.py ...`)
> - **From inside the skill directory**: `python scripts/run.py ...`

### Scenario 1: Deep Dive Topic Analysis with Kalman & 90-Day Forecast
```bash
python wikipedia-market-insights/scripts/run.py analyze \
  --topic "Астрономія" \
  --lang uk \
  --period 2y \
  --forecast \
  --forecast-days 90 \
  --output-dir ./artifacts \
  --verify
```

---

### Scenario 2: Cross-Market Comparison with Forecasting & Quality Gate
```bash
python wikipedia-market-insights/scripts/run.py compare \
  --topic "Intermittent fasting" \
  --langs pl,cs,de,uk \
  --period 2y \
  --forecast \
  --output-dir ./artifacts \
  --verify
```

---

### Scenario 3: Multi-Topic Cross-Language Benchmark (Competing Product Hypotheses)
Benchmark multiple competing product hypotheses simultaneously to identify volume leaders and growth momentum:
```bash
python wikipedia-market-insights/scripts/run.py compare \
  --topics "Pilates,Calisthenics,Stretching" \
  --langs de,fr \
  --period 3y \
  --output-dir ./artifacts \
  --verify
```

---

### Scenario 4: K-Means Market Clustering into Commercial Cohorts (Tibshirani ML)
```bash
python wikipedia-market-insights/scripts/run.py cluster \
  --topic "English language" \
  --langs en,es,uk,pl,de \
  --period 2y \
  --k 3 \
  --output-dir ./artifacts \
  --verify
```

---

### Scenario 5: Autonomous Ambient Market Radar (Background Sensing)
Execute proactive background monitoring of high-velocity topics across languages:

```bash
# Single scheduled batch scan
python wikipedia-market-insights/scripts/ambient_radar.py --scan --languages en,pl,de --output-dir ./artifacts/alerts

# Continuous background monitor daemon
python wikipedia-market-insights/scripts/ambient_radar.py --watch --interval 3600
```

---

## How the Agent Should Interpret & Present Results

When responding to the user:
1. **Highlight the Primary Verdict & Council of Rivals**: State the overall verdict, cite the **Trust Score**, and present the perspectives from the UA Marketer, Risk Auditor, and Monetization Strategist.
2. **Clarify Anomalies**: Mention if spikes occurred (e.g. *"Note: 18% of traffic was concentrated in April due to the solar eclipse, but baseline interest remains +14% higher than last year"*).
3. **Provide Normalized Market Ranking**: When comparing countries, explain both absolute volume and normalized share per 1M readers.
4. **Reference Artifacts & Verification**: Provide markdown links to the verified 1-page PDF report (`file:///...`) and chart PNGs.
5. **Consult Institutional Memory**: Check `references/gotchas.md` for known API quirks or domain seasonality before drawing conclusions.

---

## Detailed References

- [Institutional Reflexion Ledger](references/gotchas.md) — Known API quirks, solar eclipse anomalies, and layout constraints
- [API Endpoints & Technical Specs](references/api.md) — MediaWiki and Wikimedia AQS protocol
- [Mathematical Methodology & Formulas](references/methodology.md) — MAD spike isolation, IQR, and Restraint equations
- [Roadmap for Iterative Expansion](references/expansion.md) — Integration with Google Trends, App Store, and Neo4j
