# Wikimedia Analytics API Reference

## Base Endpoints

Wikimedia provides open RESTful analytics data under:
`https://wikimedia.org/api/rest_v1/metrics/pageviews/`

### 1. Per-Article Pageviews
Returns daily or monthly pageview counts for a specific article.

```http
GET /metrics/pageviews/per-article/{project}/{access}/{agent}/{article}/{granularity}/{start}/{end}
```

- **`project`**: Language edition domain, e.g. `uk.wikipedia.org`, `pl.wikipedia.org`, `cs.wikipedia.org`.
- **`access`**:
  - `all-access` (Default, recommended)
  - `desktop`
  - `mobile-app`
  - `mobile-web`
- **`agent`**:
  - `user` (Crucial for market intelligence: excludes automated spiders and search engine crawlers).
  - `spider`
  - `all-agents`
- **`article`**: Article title. Spaces must be replaced by underscores (`_`) and percent-encoded.
- **`granularity`**: `daily` or `monthly`.
- **`start` / `end`**: `YYYYMMDD` (daily) or `YYYYMM01` (monthly). Data available starting from July 1, 2015.

### 2. Project-Level Aggregate Pageviews
Returns total pageview counts for the entire language project.

```http
GET /metrics/pageviews/aggregate/{project}/{access}/{agent}/{granularity}/{start}/{end}
```

Used by this skill to normalize topic views against the overall size of the language edition:
$$\text{Normalized Share} = \frac{\text{Topic Views}}{\text{Total Project Views}} \times 1,000,000$$

---

## MediaWiki Interlanguage Links API

To resolve a topic across languages without manual translation:

```http
GET https://{source_lang}.wikipedia.org/w/api.php?action=query&titles={title}&prop=langlinks&lllimit=500&redirects=1&format=json
```

- Handles automatic redirects (e.g. synonyms or alternate spellings).
- Returns the exact canonical article title in all other language editions.

---

## Best Practices & Policies

1. **User-Agent Header**: Wikimedia requires a distinct User-Agent header containing contact or project info. Anonymous generic User-Agents can be throttled.
2. **Rate Limits**: The API allows up to ~100 requests/second, but client-side caching is implemented in `.cache/` to ensure deterministic, near-instant responses for repeated agent operations.
3. **Latency**: Daily data updates daily at ~04:00 UTC for the previous calendar day.
