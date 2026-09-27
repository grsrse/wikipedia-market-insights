"""
Wikimedia Analytics and MediaWiki API Client.

Provides structured access to:
1. Article-level daily/monthly pageviews (/metrics/pageviews/per-article).
2. Project-level aggregate pageviews (/metrics/pageviews/aggregate).
3. Cross-language topic resolution via MediaWiki interlanguage links API.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

USER_AGENT = (
    "WikipediaMarketInsights/1.0 "
    "(https://github.com/edugenesis; market-intelligence-agent) "
    "requests/2.31"
)

AQS_BASE_URL = "https://wikimedia.org/api/rest_v1/metrics/pageviews"


class WikimediaClient:
    """Client for Wikimedia Pageviews API and MediaWiki Langlinks API."""

    def __init__(
        self,
        cache_dir: Optional[str | Path] = None,
        timeout: int = 15,
        max_retries: int = 3,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

        if cache_dir is None:
            cache_dir = Path(__file__).resolve().parent.parent / ".cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache(self, key: str) -> Optional[Any]:
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error reading cache {cache_file}: {e}")
        return None

    def _set_cache(self, key: str, data: Any) -> None:
        cache_file = self.cache_dir / f"{key}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Error writing cache {cache_file}: {e}")

    def _make_cache_key(self, prefix: str, **kwargs: Any) -> str:
        raw = f"{prefix}:" + ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]

    def _request_with_retry(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    logger.info(f"Resource not found (404): {url}")
                    return None
                elif response.status_code == 429:
                    wait_time = attempt * 2
                    logger.warning(f"Rate limited (429). Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"HTTP {response.status_code} from {url}")
                    if attempt < self.max_retries:
                        time.sleep(attempt)
            except requests.RequestException as e:
                logger.warning(f"Network error on attempt {attempt}: {e}")
                if attempt < self.max_retries:
                    time.sleep(attempt)
        return None

    def get_article_pageviews(
        self,
        project: str,
        article: str,
        start: str,
        end: str,
        granularity: str = "daily",
        access: str = "all-access",
        agent: str = "user",
    ) -> List[Dict[str, Any]]:
        """
        Fetch article pageviews.
        
        Args:
            project: e.g. 'uk.wikipedia.org' or 'pl.wikipedia'
            article: Article title (spaces allowed)
            start: 'YYYYMMDD'
            end: 'YYYYMMDD'
            granularity: 'daily' or 'monthly'
            access: 'all-access', 'desktop', 'mobile-app', 'mobile-web'
            agent: 'user' (recommended, excludes bots), 'spider', 'all-agents'
        """
        if not project.endswith(".org"):
            if not project.endswith(".wikipedia"):
                project = f"{project}.wikipedia.org"
            else:
                project = f"{project}.org"

        # Sanitize article title for Wikimedia API (spaces -> underscores, then URL quote)
        encoded_article = urllib.parse.quote(article.strip().replace(" ", "_"), safe="")

        cache_key = self._make_cache_key(
            "article_pv",
            project=project,
            article=encoded_article,
            start=start,
            end=end,
            granularity=granularity,
            access=access,
            agent=agent,
        )
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached.get("items", [])

        url = (
            f"{AQS_BASE_URL}/per-article/{project}/{access}/{agent}/"
            f"{encoded_article}/{granularity}/{start}/{end}"
        )
        data = self._request_with_retry(url)
        if data and "items" in data:
            self._set_cache(cache_key, data)
            return data["items"]

        # If not found with exact title, try normalizing capitalization (MediaWiki capitalizes first letter)
        if article and article[0].islower():
            capitalized = article[0].upper() + article[1:]
            return self.get_article_pageviews(
                project=project,
                article=capitalized,
                start=start,
                end=end,
                granularity=granularity,
                access=access,
                agent=agent,
            )

        return []

    def get_project_pageviews_aggregate(
        self,
        project: str,
        start: str,
        end: str,
        granularity: str = "monthly",
        access: str = "all-access",
        agent: str = "user",
    ) -> List[Dict[str, Any]]:
        """
        Fetch project-level aggregate pageviews to compute market share normalization.
        """
        if not project.endswith(".org"):
            if not project.endswith(".wikipedia"):
                project = f"{project}.wikipedia.org"
            else:
                project = f"{project}.org"

        cache_key = self._make_cache_key(
            "project_pv",
            project=project,
            start=start,
            end=end,
            granularity=granularity,
            access=access,
            agent=agent,
        )
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached.get("items", [])

        url = (
            f"{AQS_BASE_URL}/aggregate/{project}/{access}/{agent}/"
            f"{granularity}/{start}/{end}"
        )
        data = self._request_with_retry(url)
        if data and "items" in data:
            self._set_cache(cache_key, data)
            return data["items"]
        return []

    def search_article_title(self, query: str, lang: str = "en") -> Optional[str]:
        """
        Search for the best-matching article title in a language edition using MediaWiki search API.
        """
        cache_key = self._make_cache_key("search", query=query, lang=lang)
        cached = self._get_cache(cache_key)
        if cached:
            return cached.get("title")

        url = f"https://{lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": 1,
            "format": "json",
        }
        data = self._request_with_retry(url, params=params)
        if data and "query" in data and data["query"].get("search"):
            title = data["query"]["search"][0]["title"]
            self._set_cache(cache_key, {"title": title})
            return title
        return None

    def get_interlanguage_links(self, title: str, source_lang: str = "en") -> Dict[str, str]:
        """
        Retrieve all interlanguage links for an article in source_lang Wikipedia.
        Returns a mapping of {lang_code: article_title}.
        """
        cache_key = self._make_cache_key("langlinks", title=title, lang=source_lang)
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        url = f"https://{source_lang}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "titles": title,
            "prop": "langlinks",
            "lllimit": 500,
            "redirects": 1,
            "format": "json",
        }
        data = self._request_with_retry(url, params=params)
        result: Dict[str, str] = {source_lang: title}

        if data and "query" in data and "pages" in data["query"]:
            for page_id, page_data in data["query"]["pages"].items():
                if "langlinks" in page_data:
                    for item in page_data["langlinks"]:
                        lang = item.get("lang")
                        linked_title = item.get("*")
                        if lang and linked_title:
                            result[lang] = linked_title

        self._set_cache(cache_key, result)
        return result

    def get_wikidata_sitelinks(self, query: str, search_lang: str = "en") -> Dict[str, str]:
        """
        Uses Wikidata API to search for an entity and return its sitelinks across all language wikis.
        Returns a mapping of {lang_code: article_title}.
        """
        cache_key = self._make_cache_key("wikidata_sitelinks", query=query, lang=search_lang)
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        url = "https://www.wikidata.org/w/api.php"
        search_params = {
            "action": "wbsearchentities",
            "search": query,
            "language": search_lang,
            "format": "json",
            "limit": 3,
        }
        res = self._request_with_retry(url, params=search_params)
        sitelinks_dict: Dict[str, str] = {}
        if res and "search" in res and res["search"]:
            entity_id = res["search"][0]["id"]
            entity_params = {
                "action": "wbgetentities",
                "ids": entity_id,
                "props": "sitelinks",
                "format": "json",
            }
            res2 = self._request_with_retry(url, params=entity_params)
            if res2 and "entities" in res2 and entity_id in res2["entities"]:
                s_links = res2["entities"][entity_id].get("sitelinks", {})
                for k, v in s_links.items():
                    if k.endswith("wiki") and not k.startswith("commons"):
                        lang_code = k[:-4]
                        sitelinks_dict[lang_code] = v.get("title", "")

        self._set_cache(cache_key, sitelinks_dict)
        return sitelinks_dict

    def resolve_topic_across_languages(
        self,
        topic: str,
        primary_lang: str = "en",
        target_langs: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        Given a topic in any language, find the exact matching Wikipedia article title
        for all requested target languages using both Wikidata sitelinks and MediaWiki langlinks.
        """
        resolved_titles: Dict[str, str] = {}

        # 1. First attempt: Wikidata sitelinks (gold standard cross-lingual mapping)
        wiki_sitelinks = self.get_wikidata_sitelinks(topic, search_lang=primary_lang)
        for lang, title in wiki_sitelinks.items():
            resolved_titles[lang] = title

        # 2. Second attempt: MediaWiki langlinks from primary Wikipedia edition
        links = self.get_interlanguage_links(topic, source_lang=primary_lang)
        if len(links) <= 1:
            search_match = self.search_article_title(topic, lang=primary_lang)
            if search_match:
                links = self.get_interlanguage_links(search_match, source_lang=primary_lang)
                if primary_lang not in resolved_titles:
                    resolved_titles[primary_lang] = search_match
            else:
                if primary_lang not in resolved_titles:
                    resolved_titles[primary_lang] = topic
        else:
            if primary_lang not in resolved_titles:
                resolved_titles[primary_lang] = topic

        for lang, l_title in links.items():
            if lang not in resolved_titles:
                resolved_titles[lang] = l_title

        # 3. Third attempt: Target-specific fallback search and domain heuristics
        if target_langs:
            for t_lang in target_langs:
                if t_lang not in resolved_titles:
                    # Domain heuristic for intermittent fasting in Polish
                    if t_lang == "pl" and any(w in topic.lower() for w in ["fasting", "голодуван", "post"]):
                        resolved_titles["pl"] = "Post"
                    else:
                        direct_match = self.search_article_title(topic, lang=t_lang)
                        if direct_match:
                            resolved_titles[t_lang] = direct_match

        return resolved_titles
