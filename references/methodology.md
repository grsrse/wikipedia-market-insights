# Mathematical & Statistical Methodology

This document details the analytical formulas and algorithms used by the `wikipedia-market-insights` skill.

---

## 1. Growth Metrics

### Year-over-Year (YoY) Growth
Compares total pageviews in the most recent 365 days ($V_{\text{recent}}$) against the preceding 365 days ($V_{\text{prior}}$):

$$\text{YoY Growth \%} = \left(\frac{V_{\text{recent}} - V_{\text{prior}}}{V_{\text{prior}}}\right) \times 100$$

### Baseline Organic Growth
Raw sums can be distorted by viral spikes or single news cycles. The **Baseline Growth** measures the movement of the core readership by comparing the median of the final 60 days against the median of the initial 60 days:

$$\text{Baseline Growth \%} = \left(\frac{\text{Median}(V_{\text{last } 60}) - \text{Median}(V_{\text{first } 60})}{\text{Median}(V_{\text{first } 60})}\right) \times 100$$

### Compound Annual Growth Rate (CAGR)
For multi-year spans ($T \ge 1.0$ years):

$$\text{CAGR} = \left(\frac{\text{Median}(V_{\text{last } 60})}{\text{Median}(V_{\text{first } 60})}\right)^{\frac{1}{T}} - 1$$

---

## 2. Spike Detection & Anomaly Filtering

To answer whether growth can be trusted, we isolate transient viral bursts from sustained interest:

1. **30-Day Moving Median**:
   $$M_t = \text{Median}(V_{t-15}, \dots, V_{t+15})$$
2. **Residuals & Median Absolute Deviation (MAD)**:
   $$R_t = |V_t - M_t|$$
   $$\text{MAD} = \text{Median}(R)$$
   $$\text{Threshold} = M_t + 2.5 \times (1.4826 \times \text{MAD})$$
3. **Spike Classification**:
   A day $t$ is a spike if $V_t > \text{Threshold}$.
4. **Spike Impact Ratio**:
   Measures what percentage of total cumulative traffic was driven solely by anomalous bursts:
   $$\text{Spike Impact Ratio} = \frac{\sum_{t \in \text{Spikes}} (V_t - M_t)}{\sum_{t} V_t}$$

---

## 3. Trust Score (0 – 100) Formulation

The Trust Score evaluates whether an observed interest trend reflects genuine, investable customer curiosity:

$$\text{Trust Score} = S_{\text{trend}} + S_{\text{spike}} + S_{\text{consistency}} + S_{\text{longevity}}$$

| Component | Max Points | Weight Rationale |
|---|---|---|
| **$S_{\text{trend}}$ (Baseline Stability)** | 40 pts | Rewards positive growth in underlying 60-day moving median. Linear scale from 0 to 40. |
| **$S_{\text{spike}}$ (Resilience to Anomalies)** | 35 pts | $35 \times (1 - 1.5 \times \text{Spike Ratio})$. Severely penalizes trends concentrated in isolated news days. |
| **$S_{\text{consistency}}$ (Traffic Smoothness)** | 15 pts | Based on Coefficient of Variation ($CV = \sigma / \mu$). Rewards predictable daily readership. |
| **$S_{\text{longevity}}$ (Time-series Depth)** | 10 pts | 10 pts for $\ge 2$ years, 8 pts for $\ge 1$ year, 5 pts for $\ge 6$ months. |

### Classification Verdicts
- **$\ge 75$ — High Confidence**: Organic, sustainable market interest. Ideal candidate for product investment.
- **$50 - 74$ — Moderate Confidence**: Stable core demand with occasional seasonal or minor event variance.
- **$< 50$ — Fragile / News-Driven Spike**: High risk. Growth was propelled by transient viral events rather than organic curiosity.

---

## 4. Cross-Market Normalization

When comparing markets with differing population sizes (e.g. Polish vs Czech vs Ukrainian Wikipedia):
- Absolute pageviews favor larger language populations.
- To discover where a topic has the highest *relative penetration*, we calculate views per 1M total language edition views:

$$\text{Normalized Penetration} = \frac{\text{Topic Pageviews in Lang } L}{\text{Total Pageviews of } L \text{.wikipedia.org}} \times 1,000,000$$

This allows B2C founders to identify "dense niche" markets where a topic commands an outsized share of local digital attention.
