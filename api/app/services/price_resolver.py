"""Price-source resolver.

For a given chemical, pick the highest-quality source available and return a unified
PriceQuote. Tries sources in order:

    1. Intratec Primary Commodity Prices (commercial; best when subscribed).
    2. FRED PPI series (free; index, not absolute price — we attach a basis flag).
    3. Search-API price discovery agent (free if you already pay for the search key).

The Bid Evaluator and intelligence router both call into this so the platform stays
truthful about *which* source produced a number — buyers can see which prices are
authoritative and which are inferred.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from app.agents.price_discovery import discover_price
from app.services import intratec, public_signals

PRIORS_PATH = Path(__file__).parent.parent / "intelligence" / "chemical_priors.json"
_PRIORS = {c["name"].lower(): c for c in json.loads(PRIORS_PATH.read_text(encoding="utf-8"))["chemicals"]}


# Map: platform chemical → FRED series id, when one fits cleanly. Only used for index
# benchmarking, not absolute pricing.
FRED_FOR_CHEMICAL: dict[str, str] = {
    "Chlorine": "WPU06130302",
    "Sodium Hydroxide": "WPU061303024",
    "Sodium Hypochlorite": "WPU06130302",     # rolls under chlor-alkali index
    "Calcium Hypochlorite": "WPU06130302",
    "Hydrochloric Acid": "WPU06130302",
    "Anhydrous Ammonia": "DHHNGSP",            # gas proxy; NH3 ~70% gas-cost-driven
    "Ammonium Hydroxide": "DHHNGSP",
    "Phosphate Rock": "PPHOSPHATESUSDM",
    "Potassium Chloride": "PPOTASHUSDM",
    "Sulfuric Acid": "DCOILWTICO",             # very loose; sulfur is refinery byproduct
    "Sulfur Dioxide": "DCOILWTICO",
}


SourceTier = Literal["intratec", "fred", "search", "prior", "none"]


@dataclass
class PriceQuote:
    chemical: str
    source: SourceTier
    usd_per_kg_active: float | None
    confidence: float                # 0.0-1.0
    as_of: str | None = None
    region: str | None = None
    note: str | None = None
    citations: list[dict] = field(default_factory=list)


async def resolve_price(chemical_name: str, *, region: str | None = "USA") -> PriceQuote:
    # Tier 1: Intratec (when subscribed)
    intra = await intratec.get_prices(chemical_name, region=region)
    if intra:
        latest = max(intra, key=lambda p: p.period or "")
        return PriceQuote(
            chemical=chemical_name,
            source="intratec",
            usd_per_kg_active=latest.usd_per_metric_ton / 1000.0,
            confidence=0.95,
            as_of=latest.period,
            region=latest.region,
            note=f"Intratec {latest.commodity_slug} ({latest.source})",
            citations=[{"source": "intratec", "commodity": latest.commodity_slug, "period": latest.period}],
        )

    # Tier 2: FRED — returns an *index*, not absolute $/kg. We mark it as an index quote
    # so the bid evaluator UI can render it as "PPI: 212 (index, not $/kg)" rather than
    # falsely claiming a price.
    series_id = FRED_FOR_CHEMICAL.get(chemical_name)
    if series_id:
        pts = await public_signals.fred_series(series_id)
        if pts:
            latest = pts[-1]
            return PriceQuote(
                chemical=chemical_name,
                source="fred",
                usd_per_kg_active=None,         # index-only
                confidence=0.7,
                as_of=latest["date"],
                region="USA",
                note=f"FRED index {series_id} = {latest['value']:.1f} (latest available month)",
                citations=[{"source": "fred", "series": series_id, "date": latest["date"], "value": latest["value"]}],
            )

    # Tier 3: search-API price discovery agent — slow but works for niche chemicals.
    benchmark = await discover_price(chemical_name, region=region)
    if benchmark.sample_size > 0:
        return PriceQuote(
            chemical=chemical_name,
            source="search",
            usd_per_kg_active=benchmark.median_usd_per_kg,
            confidence=0.6,
            as_of=None,
            region=region,
            note=benchmark.methodology_note,
            citations=[
                {"source": "search", "url": p.source_url, "value": p.value_usd_per_kg, "freshness": p.freshness}
                for p in benchmark.points[:5]
            ],
        )

    # Tier 4: nothing live — fall back to the static prior (just a chemical-family hint).
    prior = _PRIORS.get(chemical_name.lower())
    if prior:
        return PriceQuote(
            chemical=chemical_name,
            source="prior",
            usd_per_kg_active=None,
            confidence=0.3,
            note=f"No live price source for {chemical_name}; family={prior.get('family')}, risk={prior.get('risk')}",
        )

    return PriceQuote(chemical=chemical_name, source="none", usd_per_kg_active=None, confidence=0.0)
