# Iterative Expansion Roadmap: Scaling to Complex Research & Large Data

This document explains how to evolve the `wikipedia-market-insights` skill from single-topic validation into an enterprise-grade market intelligence system capable of handling complex research domains and massive data volumes.

---

## 1. Topic Clusters & Semantic Taxonomies (Wikidata & Categories)

### Current State
Analyzes a single canonical article per language edition (e.g. "Astronomy").

### Next Iteration: Category & Cluster Expansion
A single article rarely captures the entire market for a B2C application. For instance, interest in "Language Learning" spans hundreds of articles: "Duolingo", "CEFR", "English grammar", "IELTS", "TOEFL", "Second-language acquisition".

1. **Category Traversal via MediaWiki API**:
   - Query `action=query&list=categorymembers&cmtitle=Category:Astronomy&cmlimit=500`.
   - Recursively fetch subcategories down to depth 2.
2. **Wikidata SPARQL Knowledge Graphs**:
   - Query Wikidata endpoint (`https://query.wikidata.org/sparql`) to retrieve all entities with `instance of` or `subclass of` the target concept.
   - Aggregate pageview curves across all cluster members to form a **Composite Topic Index**.
3. **Weighting by Importance**:
   - Apply PageRank or in-degree citation weights to prevent obscure stub articles from skewing the index.

---

## 2. Scaling to Massive Datasets (Wikimedia Dumps & Clickstream)

### Current State
Queries the live REST API on demand, suitable for up to dozens of articles with in-memory/disk caching.

### Scaling Architecture for Big Data
When researching whole industries (e.g. 50,000 health/wellness articles across 30 languages):

1. **Wikimedia Monthly Dumps (Pageview Complete)**:
   - Process official Wikimedia parquet/tsv dumps (`dumps.wikimedia.org/other/pageview_complete/`).
   - Use DuckDB or Apache Arrow/Polars for local high-speed columnar querying without network latency or API rate limits.
2. **Clickstream Analysis**:
   - Wikimedia publishes monthly **Clickstream Data** showing user navigation paths: `(source_article, target_article, transition_type, count)`.
   - *Application:* Discover what topics users read *immediately before* and *immediately after* the target article. This identifies customer intent, search pathways, and adjacent product niches.

---

## 3. Cross-Source Market Triangulation

Wikipedia pageviews are a premier measure of **curiosity and knowledge-seeking**, but product success requires triangulating multiple signals:

| Source | Signal Captured | Complementary Value |
|---|---|---|
| **Wikipedia Pageviews** | Educational curiosity, deep interest | Early top-of-funnel indicator |
| **Google Trends API** | Commercial search intent | Validates active search volume & commercial queries |
| **Reddit & Social Sentiment** | Pain points & community discussions | Qualitative feedback, unaddressed user frustrations |
| **App Store / Google Play Trends** | App-specific market saturation | Validates existing competitor traction in the market |
| **Purchasing Power Parity (PPP) / GDP** | Willingness and ability to pay | Converts interest index into addressable revenue potential |

---

## 4. Advanced Time-Series Modeling & Predictive Forecasting

1. **Seasonal Decomposition (STL)**:
   - Automatically separate seasonal cycles (e.g. annual January spike for fitness and diet topics, September surge for school subjects).
2. **Forward Projections (Prophet / NeuralProphet)**:
   - Provide 6- to 12-month forward forecasts with 80% confidence bands to predict market size by product launch date.
3. **Leading Indicator Discovery**:
   - Cross-correlate English Wikipedia trends with localized editions. Often, consumer trends emerge in English 6–18 months before propagating to Polish, Czech, or Ukrainian language markets.

---

## 5. Summary Implementation Path for Product Teams

```
┌────────────────────────────────────────────────────────┐
│ Phase 1: Current Implementation                        │
│ - Single & comparative topic analysis via AQS API      │
│ - Statistical Trust Score & spike isolation            │
│ - 1-Page PDF Executive Brief & CLI integration         │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Phase 2: Semantic Clustering (Wikidata / Categories)    │
│ - Multi-article composite topic indices                │
│ - Automated synonym & sub-discipline grouping          │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Phase 3: Big Data & Triangulation (DuckDB & Multi-API) │
│ - Ingestion of Wikimedia monthly bulk dumps            │
│ - Clickstream referrer analysis                        │
│ - Triangulation with Google Trends & App Store metrics │
└────────────────────────────────────────────────────────┘
```
