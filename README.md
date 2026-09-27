# Wikipedia Market Insights — Quantitative Intelligence Agent Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9+-green.svg)](https://www.python.org/)
[![Architecture: Frozen Skill](https://img.shields.io/badge/Agent%20Standard-agentskills.io-purple.svg)](https://agentskills.io)
[![Version: 1.0.1](https://img.shields.io/badge/Version-1.0.1-orange.svg)](SKILL.md)

A production-hardened, self-contained quantitative market intelligence agent skill for B2C founders, venture researchers, and autonomous AI agents (Claude Haiku 4.5, GPT-4o, Qwen Code).

It queries official Wikimedia Analytics Query Service (AQS) and MediaWiki APIs to validate consumer demand, isolate viral hype anomalies from organic growth via Hampel/MAD filtering, project future trajectory using Shumway state-space Kalman smoothing, and compile guaranteed 1-page executive decision memos via ReportLab.

---

## 1. System Architecture & Module Decomposition

The package follows the **Frozen Agent Skill Specification** (`agentskills.io`). Downstream agents interact exclusively via deterministic CLI commands; no runtime code modification or monkey-patching is permitted.

```text
wikipedia-market-insights/
├── SKILL.md              # Compact agent instruction sheet & execution scenarios (< 500 lines)
├── README.md             # Technical developer & architecture reference
├── requirements.txt      # Zero-dependency footprint (requests, matplotlib, reportlab)
├── scripts/              # Deterministic execution pipeline (CLI & statistical core)
│   ├── run.py            # Unified CLI dispatcher (analyze, compare, cluster, report, benchmark)
│   ├── client.py         # Wikimedia AQS client, MediaWiki langlinks resolver & local disk cache
│   ├── analyzer.py       # Core statistical engine (MAD filter, Trust Score, Kalman, Council of Rivals)
│   ├── visualizer.py     # Matplotlib visualizer (trends, Kalman projections, cross-market bars, 2x2 grids)
│   ├── report_pdf.py     # ReportLab executive PDF generator (strictly 1-page & 1+N page layouts)
│   ├── verify_memo.py    # Deterministic quality gate (PDF page count, PNG magic bytes, JSON schema)
│   └── ambient_radar.py  # Patton Ambient Agent loop (Sense-Interpret-Decide-Act-Learn + Restraint budget)
└── references/           # Detailed domain reference documentation
    ├── api.md            # Wikimedia REST & MediaWiki Action API technical protocol
    ├── methodology.md    # Mathematical derivations, Hampel constants, and ranking formulas
    ├── gotchas.md        # API quirks, solar eclipse anomalies, and layout constraints
    └── expansion.md      # Future architectural roadmap (Google Trends, App Store, Neo4j)
```

### Module Responsibilities

| Module | Primary Responsibility | Key Interfaces |
| :--- | :--- | :--- |
| [`scripts/client.py`](scripts/client.py) | Network transport, rate-limit isolation, disk caching (`.cache/`), Wikidata concept alignment | `WikimediaClient.get_article_pageviews()`, `resolve_topic_across_languages()` |
| [`scripts/analyzer.py`](scripts/analyzer.py) | Time-series decomposition, MAD filtering, Trust Score formulation, Kalman state-space projection, Council of Rivals | `TopicAnalyzer.calculate_growth()`, `detect_spikes()`, `calculate_trust_score()`, `evaluate_council_of_rivals()` |
| [`scripts/visualizer.py`](scripts/visualizer.py) | Publication-grade chart generation, Kalman interval shading, adaptive 2×2 subplots | `plot_single_topic_trend()`, `plot_cross_language_comparison()`, `plot_multi_topic_benchmark()` |
| [`scripts/report_pdf.py`](scripts/report_pdf.py) | Dynamic ReportLab document rendering with strict vertical budget enforcement | `PDFReportGenerator.generate_single_topic_report()`, `generate_comparison_report()`, `generate_benchmark_report()` |
| [`scripts/verify_memo.py`](scripts/verify_memo.py) | Post-generation validation gate preventing degraded artifacts from reaching founders | `verify_artifacts()`, `verify_cli()` |
| [`scripts/ambient_radar.py`](scripts/ambient_radar.py) | Background velocity sensing and notification throttling via mathematical restraint | `AmbientMarketRadar.run_scan_cycle()`, `calculate_restraint_score()` |
| [`scripts/run.py`](scripts/run.py) | Subcommand routing, CLI argument parsing, JSON serialization to stdout | `main()` |

---

## 2. Mathematical & Statistical Methodology

### 2.1. Growth Formulations

#### Year-over-Year (YoY) Growth

$$
\text{YoY Growth} = \left(\frac{V_{\text{recent}} - V_{\text{prior}}}{V_{\text{prior}}}\right) \times 100
$$

Where:
- $V_{\text{recent}}$ is the total pageviews across the most recent 365 days.
- $V_{\text{prior}}$ is the total pageviews across the preceding 365 days.

#### Baseline Organic Growth

$$
\text{Baseline Growth} = \left(\frac{\text{Median}(V_{\text{last } 60}) - \text{Median}(V_{\text{first } 60})}{\text{Median}(V_{\text{first } 60})}\right) \times 100
$$

Compares the 60-day moving median between window endpoints to immunize the growth trajectory against isolated news spikes.

#### Compound Annual Growth Rate (CAGR)

For observation periods $T \ge 1.0$ years:

$$
\text{CAGR} = \left(\frac{\text{Median}(V_{\text{last } 60})}{\text{Median}(V_{\text{first } 60})}\right)^{\frac{1}{T}} - 1
$$

---

### 2.2. Robust Anomaly Isolation (MAD & Hampel Filter)

Traditional standard deviation $\sigma$ is severely inflated by large viral spikes ($O(n)$ sensitivity). The skill employs a non-parametric **Hampel-type Median Absolute Deviation (MAD)** filter:

#### 1. 30-Day Moving Baseline

$$
M_t = \text{Median}(V_{t-15}, \dots, V_{t+15})
$$

#### 2. Absolute Residuals & Scale Consistency

$$
R_t = |V_t - M_t|, \quad \text{MAD} = \text{Median}(R)
$$

$$
\hat{\sigma}_{\text{robust}} = 1.4826 \times \text{MAD}
$$

The factor $1.4826 = \frac{1}{\Phi^{-1}(0.75)}$ ensures asymptotic consistency with standard deviation under a Gaussian null.

#### 3. Dynamic Anomaly Threshold

$$
\text{Threshold}_t = M_t + 2.5 \times \hat{\sigma}_{\text{robust}}
$$

#### 4. Spike Impact Ratio

$$
\text{Spike Volume Ratio} = \frac{\sum_{t \in \text{Spikes}} (V_t - M_t)}{\sum_t V_t}
$$

---

### 2.3. Quantitative Trust Score ($0 - 100$)

Evaluates whether observed reader curiosity represents sustained, investable intent:

$$
\text{Trust Score} = S_{\text{trend}} + S_{\text{spike}} + S_{\text{consistency}} + S_{\text{longevity}}
$$

| Sub-metric | Range | Mathematical Derivation | Architectural Purpose |
| :--- | :--- | :--- | :--- |
| **$S_{\text{trend}}$ (Baseline Growth)** | $0 - 40$ pts | Piecewise linear mapping of Baseline Growth (+50% $\to$ 40 pts; +20% $\to$ 30 pts; 0% $\to$ 20 pts; <-50% $\to$ 0 pts). | Rewards sustained expansion of core audience. |
| **$S_{\text{spike}}$ (Hype Resilience)** | $0 - 35$ pts | $35 \times \max(0, 1.0 - 1.5 \times \text{Spike Volume Ratio})$. | Heavily penalizes trends driven by transient press coverage. |
| **$S_{\text{consistency}}$ (Variance)** | $0 - 15$ pts | Tiered via Coefficient of Variation $CV = \frac{\sigma}{\mu}$ ($CV < 0.6 \to 15$ pts; $CV < 1.0 \to 10$ pts; $CV < 1.8 \to 5$ pts). | Rewards smooth, predictable daily engagement. |
| **$S_{\text{longevity}}$ (Depth)** | $0 - 10$ pts | Step function on historical observation days ($\ge 700\text{d} \to 10$ pts; $\ge 365\text{d} \to 8$ pts; $\ge 180\text{d} \to 5$ pts). | Penalizes newly created articles with unproven longevity. |

**Classification Verdicts**:

- **$\ge 75$ — High Confidence**: Organic, sustainable market interest. Low launch risk.
- **$50 - 74$ — Moderate Confidence**: Steady core demand with minor seasonal/event volatility.
- **$< 50$ — Fragile / News-Driven Spike**: High risk. Growth was propelled by transient viral events.

---

### 2.4. Shumway & Stoffer State-Space Kalman Smoothing & Forecasting

Rather than heavy, non-converging ARIMA/SARIMA models, the skill employs a linear Gaussian state-space model:

$$
x_t = F x_{t-1} + w_t, \quad w_t \sim \mathcal{N}(0, Q)
$$

$$
y_t = H x_t + v_t, \quad v_t \sim \mathcal{N}(0, R)
$$

Where state $x_t = [\mu_t, \beta_t]^T$ represents unobserved local level and drift, $F = \begin{bmatrix} 1 & 1 \\ 0 & 1 \end{bmatrix}$, and $H = \begin{bmatrix} 1 & 0 \end{bmatrix}$.

- **Dropout Imputation**: If an API outage occurs or $y_t = 0$, the Kalman gain $K_t$ is set to $0$, projecting the hidden state purely via system dynamics.
- **Analytical 90-Day Forecast**: Forward extrapolation with calibrated 95% analytical prediction bounds:

$$
\hat{y}_{t+h} = H F^h x_t \pm 1.96 \sqrt{H P_{t+h|t} H^T + R}
$$

---

### 2.5. Non-Parametric Bootstrap Confidence Intervals (Tibshirani / Efron)

To quantify statistical uncertainty in the Trust Score without parametric assumptions:

- Resamples the residual distribution $e_t = V_t - M_t$ with replacement across $B = 250$ replications.
- Re-evaluates Trust Score across bootstrap datasets to output empirical 95% confidence intervals $[TS_{\text{low}}, TS_{\text{high}}]$ (representing the 2.5th and 97.5th percentiles).

---

### 2.6. Cross-Market Normalization & Multi-Criteria Ranking

To prevent large linguistic editions (e.g. `en.wikipedia` or `de.wikipedia`) from overshadowing high-intent niche regions (e.g. `pl` or `cs`), views are normalized per 1,000,000 total project pageviews:

$$
\text{Normalized Density} = \frac{\text{Topic Pageviews in Lang } L}{\text{Total Project Pageviews of } L\text{.wikipedia.org}} \times 1,000,000
$$

**Multi-Criteria Market Ranking**:

$$
\text{Rank Score} = 0.50 \cdot \frac{TS_L}{\max(TS)} + 0.30 \cdot \frac{\max(0, YoY_L)}{\max(YoY)} + 0.20 \cdot \frac{\text{NormDens}_L}{\max(\text{NormDens})}
$$

All vectors are scaled to $[0, 1]$ across the active market cohort to guarantee balanced decision-making.

---

## 3. Protocol & API Endpoints

### 3.1. Wikimedia Analytics Query Service (AQS)
- **Endpoint**:
  `GET https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/{access}/{agent}/{article}/{granularity}/{start}/{end}`
- **Standard Header**:
  `User-Agent: WikipediaMarketInsights/1.0 (https://agentskills.io; quantitative-market-intelligence@genesis-academy.internal)`
- **Enforced Filter**:
  `agent=user` (strictly excludes web spiders, crawlers, and automated bots).
- **Graceful Handling**:
  Returns structured 404 degradation warnings when an article does not exist in a localized edition without terminating execution.

### 3.2. MediaWiki Interlanguage Resolution
- **Endpoint**:
  `GET https://{primary_lang}.wikipedia.org/w/api.php?action=query&prop=langlinks&lllimit=500&titles={topic}&format=json`
- **Fallback**:
  Queries the Wikidata entity API (`action=wbgetentities`) by sitelink to discover the exact localized Wikipedia slug regardless of title renamings.

---

## 4. Council of Rivals (Soares Agent Architecture)

To eliminate the common LLM bias of blindly validating user hypotheses, the skill executes an uncompromised **Council of Rivals** evaluating 3 adversarial perspectives:

```text
                         ┌─────────────────────────────┐
                         │   Topic Data & Analytics    │
                         └──────────────┬──────────────┘
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             ▼                          ▼                          ▼
┌─────────────────────────┐┌─────────────────────────┐┌─────────────────────────┐
│  UA & Growth Marketer   ││  Risk & Epistemology    ││ Monetization Strategist │
│ ─────────────────────── ││ ─────────────────────── ││ ─────────────────────── │
│ Momentum Score (0-100)  ││ Fragility Score (0-100) ││ Purchasing Tier (1-3)   │
│ Channel test (TikTok/   ││ Asymmetric VETO power   ││ Optimal pricing model   │
│   Meta Reels vs SEO)    ││   if Fragility > 65     ││   ($4.99 - $29.99/mo)   │
└────────────┬────────────┘└────────────┬────────────┘└────────────┬────────────┘
             │                          │                          │
             └──────────────────────────┼──────────────────────────┘
                                        ▼
                         ┌─────────────────────────────┐
                         │   Synthesized Executive     │
                         │          Verdict            │
                         │ ─────────────────────────── │
                         │ • STRONG_PROCEED            │
                         │ • PROCEED_WITH_CAUTION      │
                         │ • DO_NOT_LAUNCH             │
                         └─────────────────────────────┘
```

---

## 5. CLI Command Reference & Argument Specifications

All workflows are driven via `scripts/run.py`:

```bash
python scripts/run.py <subcommand> [flags]
```

### Subcommands Overview

| Subcommand | Purpose | Primary Outputs |
| :--- | :--- | :--- |
| `analyze` | Deep-dive statistical analysis of a single topic in one language edition | Trend PNG, strictly 1-page PDF memo, JSON data |
| `compare` | Multi-market comparison ($1 \times M$) or multi-topic cross-language benchmark ($N \times M$) | Comparison/Benchmark PNGs, strictly 1 or $1+N$ page PDF, JSON |
| `cluster` | Unsupervised Tibshirani K-Means clustering into commercial market tiers | Cluster scatter PNG, 1-page PDF, JSON |
| `report` | Executive summary generator across predefined market cohorts | Formatted comparative table and strategic recommendations |

### 5.1. `analyze` Flags

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--topic` | `str` | *(Required)* | Article title in the target Wikipedia edition. |
| `--lang` | `str` | `en` | Wikipedia language code (e.g. `en`, `pl`, `de`, `uk`, `cs`). |
| `--period` | `str` | `2y` | Observation horizon: `6m`, `1y`, `2y`, `3y`, `all`. |
| `--forecast` | `flag` | `False` | Enables Shumway state-space Kalman forecasting. |
| `--forecast-days` | `int` | `90` | Forecast horizon in days ($14 - 180$). |
| `--output-dir` | `path` | `./artifacts` | Target directory for generated PNG and PDF files. |
| `--verify` | `flag` | `False` | Executes the strict `verify_memo.py` validation gate. |

### 5.2. `compare` Flags

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--topic` | `str` | `None` | Single topic to compare across multiple languages ($1 \times M$). |
| `--topics` | `str` | `None` | Comma-separated topics to benchmark ($N \times M$ or $N \times 1$). |
| `--langs` | `str` | `en,de,fr` | Comma-separated Wikipedia language codes. |
| `--period` | `str` | `2y` | Observation horizon (`6m`, `1y`, `2y`, `3y`). |
| `--output-dir` | `path` | `./artifacts` | Target directory for generated charts and PDF. |
| `--verify` | `flag` | `False` | Enforces the $1$ or $1+N$ page budget verification gate. |

### 5.3. `cluster` Flags

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--topic` | `str` | *(Required)* | Topic to evaluate across international editions. |
| `--langs` | `str` | *(Required)* | Comma-separated language editions to cluster. |
| `--k` | `int` | `3` | Number of K-Means clusters ($2 \le k \le 5$). |
| `--period` | `str` | `2y` | Observation horizon. |

### 5.4. `ambient_radar.py` (Background Daemon) Flags

| Flag | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--scan` | `flag` | `False` | Runs a single batch velocity sensing pass. |
| `--watch` | `flag` | `False` | Starts an autonomous background monitoring loop. |
| `--interval` | `int` | `3600` | Polling interval in seconds. |
| `--threshold` | `float` | `0.70` | Restraint Budget threshold ($S \ge \text{threshold}$ triggers action). |

---

## 6. Installation & Verification

### Requirements
- Python 3.9+
- Zero compiled C/C++ dependencies or proprietary backends.

```bash
git clone https://github.com/grsrse/wikipedia-market-insights.git
cd wikipedia-market-insights
pip install -r requirements.txt
```

### Smoke Test Verification
Validate the pipeline locally using the built-in `--verify` gate:

```bash
# 1x1 Analyze test
python scripts/run.py analyze --topic "Pizza" --lang pl --period 6m --verify

# NxM Benchmark test
python scripts/run.py compare --topics "Coffee,Tea" --langs en,de --period 1y --verify
```

---

## 7. License

Distributed under the MIT License. See `LICENSE` or `SKILL.md` for details.
