"""SearchService — provider-agnostic web search client.

Powers both:
  1. Risk Monitor — live disruption / news / force-majeure signals.
  2. Price Discovery — live spot/contract pricing for the Bid Evaluator and RFP Builder.

Supports four providers via the SEARCH_PROVIDER env var:
  - brave   : api.search.brave.com (default)
  - tavily  : api.tavily.com
  - exa     : api.exa.ai
  - serpapi : serpapi.com

The same API key is reused across the platform; a single env var (SEARCH_API_KEY) holds it.

Design notes:
- All calls are async (httpx).
- Each result is normalized to {title, url, snippet, published_at, source}.
- Cached for 1 hour by query+provider — repeated queries inside the same job don't re-spend
  search credits.
- Aggressive timeout (8s) and retry (3) so a slow provider doesn't block the worker.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Literal

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

_settings = get_settings()


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    published_at: str | None = None
    source: str | None = None


# Simple in-process cache. In production with multiple worker replicas, swap to Redis.
_cache: dict[str, tuple[float, list[SearchResult]]] = {}
_CACHE_TTL_S = 3600


def _cache_key(provider: str, query: str, freshness: str | None, count: int) -> str:
    return hashlib.sha256(
        f"{provider}|{query}|{freshness or ''}|{count}".encode()
    ).hexdigest()


def _from_cache(key: str) -> list[SearchResult] | None:
    if key in _cache:
        ts, results = _cache[key]
        if time.time() - ts < _CACHE_TTL_S:
            return results
        del _cache[key]
    return None


def _to_cache(key: str, results: list[SearchResult]) -> None:
    _cache[key] = (time.time(), results)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def _brave_search(
    query: str, *, count: int = 10, freshness: str | None = None
) -> list[SearchResult]:
    """Brave Search API. freshness ∈ {None, 'pd' (24h), 'pw' (week), 'pm' (month), 'py' (year)}."""
    params: dict[str, Any] = {"q": query, "count": count}
    if freshness:
        params["freshness"] = freshness
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": _settings.search_api_key,
    }
    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.get("https://api.search.brave.com/res/v1/web/search", params=params, headers=headers)
        r.raise_for_status()
        data = r.json()
    out: list[SearchResult] = []
    for hit in (data.get("web") or {}).get("results", []) or []:
        out.append(
            SearchResult(
                title=hit.get("title", ""),
                url=hit.get("url", ""),
                snippet=hit.get("description", ""),
                published_at=hit.get("age"),
                source=hit.get("profile", {}).get("name") if isinstance(hit.get("profile"), dict) else hit.get("meta_url", {}).get("hostname"),
            )
        )
    return out


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def _tavily_search(
    query: str, *, count: int = 10, freshness: str | None = None
) -> list[SearchResult]:
    """Tavily Search API. Maps freshness to Tavily's days param."""
    days_map = {"pd": 1, "pw": 7, "pm": 30, "py": 365}
    days = days_map.get(freshness or "")
    body: dict[str, Any] = {
        "api_key": _settings.search_api_key,
        "query": query,
        "max_results": count,
        "search_depth": "advanced",
        "include_answer": False,
    }
    if days:
        body["days"] = days
    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.post("https://api.tavily.com/search", json=body)
        r.raise_for_status()
        data = r.json()
    out: list[SearchResult] = []
    for hit in data.get("results", []):
        out.append(
            SearchResult(
                title=hit.get("title", ""),
                url=hit.get("url", ""),
                snippet=hit.get("content", ""),
                published_at=hit.get("published_date"),
                source=None,
            )
        )
    return out


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def _exa_search(
    query: str, *, count: int = 10, freshness: str | None = None
) -> list[SearchResult]:
    days_map = {"pd": 1, "pw": 7, "pm": 30, "py": 365}
    body: dict[str, Any] = {"query": query, "numResults": count, "useAutoprompt": True}
    if freshness in days_map:
        body["startPublishedDate"] = _iso_days_ago(days_map[freshness])
    headers = {"Content-Type": "application/json", "x-api-key": _settings.search_api_key}
    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.post("https://api.exa.ai/search", json=body, headers=headers)
        r.raise_for_status()
        data = r.json()
    out: list[SearchResult] = []
    for hit in data.get("results", []):
        out.append(
            SearchResult(
                title=hit.get("title", ""),
                url=hit.get("url", ""),
                snippet=hit.get("text", "") or hit.get("highlight", ""),
                published_at=hit.get("publishedDate"),
                source=hit.get("author"),
            )
        )
    return out


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def _serpapi_search(
    query: str, *, count: int = 10, freshness: str | None = None
) -> list[SearchResult]:
    params: dict[str, Any] = {"q": query, "api_key": _settings.search_api_key, "num": count, "engine": "google"}
    tbs_map = {"pd": "qdr:d", "pw": "qdr:w", "pm": "qdr:m", "py": "qdr:y"}
    if freshness in tbs_map:
        params["tbs"] = tbs_map[freshness]
    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.get("https://serpapi.com/search", params=params)
        r.raise_for_status()
        data = r.json()
    out: list[SearchResult] = []
    for hit in data.get("organic_results", []):
        out.append(
            SearchResult(
                title=hit.get("title", ""),
                url=hit.get("link", ""),
                snippet=hit.get("snippet", ""),
                published_at=hit.get("date"),
                source=hit.get("source"),
            )
        )
    return out


def _iso_days_ago(days: int) -> str:
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


PROVIDERS = {
    "brave": _brave_search,
    "tavily": _tavily_search,
    "exa": _exa_search,
    "serpapi": _serpapi_search,
}


async def search(
    query: str,
    *,
    count: int = 10,
    freshness: Literal["pd", "pw", "pm", "py"] | None = None,
    provider: str | None = None,
) -> list[SearchResult]:
    """Run a single web search. Returns normalized results from the configured provider."""
    if not _settings.search_api_key:
        return []
    prov = provider or _settings.search_provider
    fn = PROVIDERS.get(prov, _brave_search)

    key = _cache_key(prov, query, freshness, count)
    cached = _from_cache(key)
    if cached is not None:
        return cached

    errored = False
    try:
        results = await fn(query, count=count, freshness=freshness)
    except Exception:
        results = []
        errored = True

    # Don't poison the cache when a transient 429/503 returned no rows. Cache only on
    # genuine successful responses (which may legitimately be empty).
    if not errored:
        _to_cache(key, results)
    return results


async def search_many(
    queries: list[str],
    *,
    count: int = 8,
    freshness: Literal["pd", "pw", "pm", "py"] | None = None,
    concurrency: int = 4,
) -> dict[str, list[SearchResult]]:
    """Run many searches with bounded concurrency. Returns a dict keyed by query."""
    sem = asyncio.Semaphore(concurrency)

    async def run_one(q: str) -> tuple[str, list[SearchResult]]:
        async with sem:
            return q, await search(q, count=count, freshness=freshness)

    pairs = await asyncio.gather(*(run_one(q) for q in queries))
    return dict(pairs)


def to_jsonable(results: list[SearchResult]) -> list[dict]:
    return [asdict(r) for r in results]
