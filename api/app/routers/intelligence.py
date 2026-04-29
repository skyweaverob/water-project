"""Intelligence endpoints — live price discovery, supplier discovery, disruption monitoring,
and public-data signal feeds. Powered by the user's search API key.
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.disruption_monitor import scan_chemical
from app.agents.price_discovery import discover_price
from app.agents.supplier_discovery import discover_suppliers
from app.auth import resolve_tenant
from app.db import get_session
from app.models import Tenant
from app.services import public_signals
from app.services.price_resolver import resolve_price
from app.services.public_signals import FRED_PPI


router = APIRouter(prefix="/intelligence", tags=["intelligence"])


class PriceBenchmarkOut(BaseModel):
    chemical: str
    cas_number: str | None
    low_usd_per_kg: float
    median_usd_per_kg: float
    high_usd_per_kg: float
    sample_size: int
    points: list[dict]
    queries_used: list[str]
    methodology_note: str


@router.get("/price/{chemical_name}", response_model=PriceBenchmarkOut)
async def get_price(
    chemical_name: str,
    region: str | None = None,
    tenant: Tenant = Depends(resolve_tenant),
) -> PriceBenchmarkOut:
    """Deep search-driven benchmark (slow but thorough). For the fast `/price-resolver`
    endpoint that picks the highest-quality available source, see `/price-resolver/...`."""
    benchmark = await discover_price(chemical_name, region=region)
    return PriceBenchmarkOut(
        chemical=benchmark.chemical,
        cas_number=benchmark.cas_number,
        low_usd_per_kg=benchmark.low_usd_per_kg,
        median_usd_per_kg=benchmark.median_usd_per_kg,
        high_usd_per_kg=benchmark.high_usd_per_kg,
        sample_size=benchmark.sample_size,
        points=[asdict(p) for p in benchmark.points],
        queries_used=benchmark.queries_used,
        methodology_note=benchmark.methodology_note,
    )


class PriceResolveOut(BaseModel):
    chemical: str
    source: str            # intratec | fred | search | prior | none
    usd_per_kg_active: float | None
    confidence: float
    as_of: str | None
    region: str | None
    note: str | None
    citations: list[dict]


@router.get("/price-resolver/{chemical_name}", response_model=PriceResolveOut)
async def get_price_resolved(
    chemical_name: str,
    region: str = "USA",
    tenant: Tenant = Depends(resolve_tenant),
) -> PriceResolveOut:
    """Best-available price for a chemical. Tries Intratec → FRED → search → static prior.
    Returns one row tagged with the source so the UI can show buyers which numbers are
    authoritative ($/kg from Intratec) vs. derived (FRED index) vs. inferred (search agent)."""
    quote = await resolve_price(chemical_name, region=region)
    return PriceResolveOut(
        chemical=quote.chemical,
        source=quote.source,
        usd_per_kg_active=quote.usd_per_kg_active,
        confidence=quote.confidence,
        as_of=quote.as_of,
        region=quote.region,
        note=quote.note,
        citations=quote.citations,
    )


class SupplierShortlistOut(BaseModel):
    chemical: str
    suppliers: list[dict]
    queries_used: list[str]


@router.get("/suppliers/{chemical_name}", response_model=SupplierShortlistOut)
async def get_suppliers(
    chemical_name: str,
    region: str | None = None,
    require_nsf60: bool = True,
    tenant: Tenant = Depends(resolve_tenant),
) -> SupplierShortlistOut:
    sl = await discover_suppliers(chemical_name, region=region, require_nsf60=require_nsf60)
    return SupplierShortlistOut(
        chemical=sl.chemical, suppliers=[asdict(s) for s in sl.suppliers], queries_used=sl.queries_used
    )


class DisruptionScanOut(BaseModel):
    chemical: str
    events: list[dict]
    queries_used: list[str]


@router.get("/disruptions/{chemical_name}", response_model=DisruptionScanOut)
async def get_disruptions(
    chemical_name: str,
    tenant: Tenant = Depends(resolve_tenant),
) -> DisruptionScanOut:
    scan = await scan_chemical(chemical_name)
    return DisruptionScanOut(
        chemical=scan.chemical, events=[asdict(e) for e in scan.events], queries_used=scan.queries_used
    )


class FredSeriesOut(BaseModel):
    series_id: str
    points: list[dict]


@router.get("/signals/fred/{key}", response_model=FredSeriesOut)
async def fred_signal(key: str, observation_start: str | None = None) -> FredSeriesOut:
    series_id = FRED_PPI.get(key, key)
    pts = await public_signals.fred_series(series_id, observation_start=observation_start)
    return FredSeriesOut(series_id=series_id, points=pts)


@router.get("/signals/quakes")
async def quakes(min_magnitude: float = Query(4.5, ge=0), hours: int = 24) -> list[dict]:
    return await public_signals.usgs_earthquakes(min_magnitude=min_magnitude, hours=hours)


@router.get("/signals/storms")
async def storms() -> list[dict]:
    return await public_signals.nhc_active_storms()


@router.get("/signals/edgar")
async def edgar(days: int = 30) -> list[dict]:
    return await public_signals.sec_edgar_force_majeure(days=days)


@router.get("/signals/news")
async def gdelt(query: str, hours: int = 24) -> list[dict]:
    return await public_signals.gdelt_news(query, hours=hours)
