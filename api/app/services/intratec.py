"""Intratec Primary Commodity Prices adapter.

Cheapest commercial commodity-price source that covers the majority of the platform's
water-treatment chemical list. The platform is built to slot Intratec in as a high-quality
override; everything else (FRED PPI, USGS, World Bank, search-API price discovery)
remains in place as fallback.

Three Intratec tiers (April 2026 pricing — verify at intratec.us):
- Starter   $299/yr — CSV/Excel only, 1-yr history.    Use the `csv` mode below.
- Pro       $499/yr — CSV/Excel only, 3-yr history.    Use the `csv` mode below.
- Advanced  $699/yr — REST API, 10-yr history, 5 users.Use the `api` mode below.

Env vars:
    INTRATEC_MODE      api | csv | off            (default: off — adapter is a no-op)
    INTRATEC_API_KEY   bearer token (Advanced tier)
    INTRATEC_API_URL   override; defaults to Intratec's published endpoint
    INTRATEC_CSV_DIR   path to a directory of CSV exports (Starter/Pro tiers)

Map from our chemical names to Intratec commodity slugs is in COMMODITY_MAP. Add new entries
as you confirm them against the Intratec catalog.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx

from app.config import get_settings

_settings = get_settings()


# Map: platform chemical name → Intratec commodity slug.
# These slugs match the URL pattern intratec.us/.../commodity/{slug}-prices.
# Verified against the public commodity pages for the chemicals where Intratec lists them;
# slugs marked with a trailing "?" are best-guess and should be confirmed once you
# have a paid login.
COMMODITY_MAP: dict[str, str] = {
    "Caustic Soda": "caustic-soda",
    "Sodium Hydroxide": "caustic-soda",
    "Chlorine": "chlorine",
    "Sodium Hypochlorite": "sodium-hypochlorite",
    "Sulfuric Acid": "sulfuric-acid",
    "Hydrochloric Acid": "hydrochloric-acid",
    "Phosphoric Acid": "phosphoric-acid",
    "Anhydrous Ammonia": "ammonia",
    "Ammonium Hydroxide": "ammonia",       # use upstream NH3 as a proxy
    "Hydrogen Peroxide": "hydrogen-peroxide",
    "Sodium Carbonate": "soda-ash",
    "Sodium Chloride": "salt",
    "Potassium Chloride": "potassium-chloride",
    "Potassium Hydroxide": "potassium-hydroxide",
    "Calcium Carbonate": "limestone",
    "Calcium Oxide": "lime",                # quicklime
    "Calcium Hydroxide": "hydrated-lime",   # slaked lime
    "Carbon Dioxide": "carbon-dioxide",
    "Oxygen": "oxygen",
    # Coverage gaps in Intratec — fall back to FRED / search agent:
    #   Aluminum Sulfate, Polyaluminum Chloride, Ferric Chloride, Ferric Sulfate,
    #   Ferrous Chloride, Ferrous Sulfate, Calcium Hypochlorite, Sodium Chlorite,
    #   Sodium Chlorate, Potassium Permanganate, Sulfur Dioxide, Fluorosilicic Acid,
    #   Citric Acid, Disodium Phosphate, Monosodium Phosphate, Sodium Salts of
    #   Polyphosphate, Zinc Orthophosphate, Sodium Silicate, Acrylamide, DADMAC,
    #   Aluminum Hydroxide, Bauxite, Ilmenite, Manganese, Zinc, Silica, Sulfur.
}

DEFAULT_API_URL = "https://api.intratec.us/v1/commodity/prices"


@dataclass
class IntratecPricePoint:
    chemical: str
    commodity_slug: str
    region: str
    period: str           # YYYY-MM
    usd_per_metric_ton: float
    source: str           # "intratec-api" | "intratec-csv"


async def _fetch_api(commodity_slug: str, region: str | None) -> list[IntratecPricePoint]:
    if not _settings.intratec_api_key:
        return []
    url = _settings.intratec_api_url or DEFAULT_API_URL
    headers = {"Authorization": f"Bearer {_settings.intratec_api_key}"}
    params: dict[str, str | int] = {"commodity": commodity_slug, "limit": 36}
    if region:
        params["region"] = region
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, headers=headers, params=params)
        if r.status_code != 200:
            return []
        try:
            data = r.json()
        except Exception:
            return []
    out: list[IntratecPricePoint] = []
    for row in data.get("series", []) or []:
        try:
            out.append(
                IntratecPricePoint(
                    chemical=row.get("commodity_name", commodity_slug),
                    commodity_slug=commodity_slug,
                    region=row.get("region", "USA"),
                    period=row.get("period", ""),
                    usd_per_metric_ton=float(row["price_usd_per_mt"]),
                    source="intratec-api",
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _fetch_csv(commodity_slug: str, region: str | None) -> list[IntratecPricePoint]:
    """Read from a manually-downloaded Intratec CSV (Starter/Pro tier path).

    Expected layout: one CSV file per commodity, named `{commodity_slug}.csv`, with header
    columns: period, region, price_usd_per_mt. The user drops them into INTRATEC_CSV_DIR
    after each monthly Intratec refresh.
    """
    csv_dir = _settings.intratec_csv_dir
    if not csv_dir:
        return []
    path = Path(csv_dir) / f"{commodity_slug}.csv"
    if not path.exists():
        return []
    out: list[IntratecPricePoint] = []
    with path.open("r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                if region and (row.get("region") or "").lower() != region.lower():
                    continue
                out.append(
                    IntratecPricePoint(
                        chemical=row.get("commodity_name", commodity_slug),
                        commodity_slug=commodity_slug,
                        region=row.get("region", "USA"),
                        period=row.get("period", ""),
                        usd_per_metric_ton=float(row["price_usd_per_mt"]),
                        source="intratec-csv",
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
    return out


async def get_prices(
    chemical_name: str, *, region: str | None = "USA"
) -> list[IntratecPricePoint]:
    """Resolve a chemical name to an Intratec commodity and return the price series.

    Returns an empty list if the chemical isn't in Intratec's catalog OR Intratec is
    disabled OR no data is available — the platform's price-source resolver then falls
    through to FRED / public signals / search-API discovery.
    """
    mode: Literal["api", "csv", "off"] = _settings.intratec_mode  # type: ignore[assignment]
    if mode == "off":
        return []
    slug = COMMODITY_MAP.get(chemical_name)
    if not slug:
        return []
    if mode == "api":
        return await _fetch_api(slug, region)
    if mode == "csv":
        return _fetch_csv(slug, region)
    return []


def latest_usd_per_kg(points: list[IntratecPricePoint]) -> float | None:
    """Pick the most recent point and convert metric tons to kg."""
    if not points:
        return None
    points_sorted = sorted(points, key=lambda p: p.period or "", reverse=True)
    return points_sorted[0].usd_per_metric_ton / 1000.0
