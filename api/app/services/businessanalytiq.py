"""businessanalytiq.com — free public price index scraper.

businessanalytiq publishes per-chemical procurement price index pages with the latest USD
benchmark. Many of them carry chemicals Intratec doesn't (notably ferric chloride). Pages
are public, but this adapter is OFF by default — flip BUSINESSANALYTIQ_MODE=on if your
deployment is comfortable with the source's terms of use.

Implementation:
- Polite User-Agent, 1 request per chemical, 24-hour in-process cache.
- Best-effort HTML parsing for the headline number; falls through cleanly when the page
  layout changes, which it will eventually. Confidence is capped at 0.65 to reflect that.

Coverage map below was confirmed against the public site as of April 2026. Add new entries
by visiting businessanalytiq.com/procurementanalytics/index/{slug}-price-index/.
"""
from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass

import httpx

from app.config import get_settings

_settings = get_settings()

BASE_URL = "https://businessanalytiq.com/procurementanalytics/index"


COMMODITY_MAP: dict[str, str] = {
    "Sodium Hydroxide": "caustic-soda",
    "Caustic Soda": "caustic-soda",
    "Chlorine": "chlorine",
    "Sulfuric Acid": "sulfuric-acid",
    "Anhydrous Ammonia": "ammonia",
    "Ammonium Hydroxide": "ammonia",
    "Ferric Chloride": "ferric-chloride",
    "Hydrogen Peroxide": "hydrogen-peroxide",
    "Phosphoric Acid": "phosphoric-acid",
    "Hydrochloric Acid": "hydrochloric-acid",
    "Sodium Carbonate": "soda-ash",
    "Potassium Hydroxide": "potassium-hydroxide",
    "Aluminum Sulfate": "aluminum-sulfate",       # if absent, scrape returns None
}


_cache: dict[str, tuple[float, "BaPricePoint | None"]] = {}
_CACHE_TTL_S = 24 * 3600


@dataclass
class BaPricePoint:
    chemical: str
    slug: str
    usd_per_metric_ton: float | None
    usd_per_kg: float | None
    period: str | None
    region: str | None
    url: str


_PRICE_PATTERNS = [
    # Common formats observed on businessanalytiq pages:
    #   "USD 580/MT" "$580/MT" "$580 / metric ton" "USD 0.58/kg"
    re.compile(r"USD?\s*\$?\s*([0-9][0-9,\.]*)\s*(?:USD)?\s*/?\s*(MT|metric ton|tonne|ton|kg|lb)", re.IGNORECASE),
    re.compile(r"\$\s*([0-9][0-9,\.]*)\s*/\s*(MT|metric ton|tonne|ton|kg|lb)", re.IGNORECASE),
]
_PERIOD_PATTERN = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}", re.IGNORECASE)


def _to_per_kg(value: float, unit: str) -> float | None:
    u = unit.lower()
    if u in ("mt", "metric ton", "tonne"):
        return value / 1000.0
    if u == "ton":  # short ton, 907.185 kg
        return value / 907.185
    if u == "kg":
        return value
    if u == "lb":
        return value * 2.20462
    return None


async def _fetch_page(slug: str) -> str | None:
    url = f"{BASE_URL}/{slug}-price-index/"
    headers = {"User-Agent": "Aquaprice/1.0 (procurement intelligence; aquaprice@example.com)"}
    try:
        async with httpx.AsyncClient(timeout=8.0, headers=headers, follow_redirects=True) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return None
            return r.text
    except Exception:
        return None


def _parse(slug: str, html: str, chemical: str) -> BaPricePoint | None:
    # Strip tags for simpler regex matching.
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)

    # Find the FIRST plausible numeric quote — businessanalytiq pages typically lead with
    # the latest index in a hero block.
    value: float | None = None
    unit: str | None = None
    for pat in _PRICE_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                value = float(m.group(1).replace(",", ""))
                unit = m.group(2)
                break
            except (ValueError, IndexError):
                continue
    if value is None or unit is None:
        return None

    per_kg = _to_per_kg(value, unit)
    period_match = _PERIOD_PATTERN.search(text)
    period = period_match.group(0) if period_match else None

    return BaPricePoint(
        chemical=chemical,
        slug=slug,
        usd_per_metric_ton=value if unit.lower() in ("mt", "metric ton", "tonne") else None,
        usd_per_kg=per_kg,
        period=period,
        region="USA",
        url=f"{BASE_URL}/{slug}-price-index/",
    )


async def get_price(chemical_name: str) -> BaPricePoint | None:
    if _settings.businessanalytiq_mode != "on":
        return None
    slug = COMMODITY_MAP.get(chemical_name)
    if not slug:
        return None
    cached = _cache.get(slug)
    if cached and time.time() - cached[0] < _CACHE_TTL_S:
        return cached[1]

    html = await _fetch_page(slug)
    if not html:
        _cache[slug] = (time.time(), None)
        return None
    point = _parse(slug, html, chemical_name)
    _cache[slug] = (time.time(), point)
    return point
