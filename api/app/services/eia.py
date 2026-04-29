"""EIA Open Data API adapter.

Free with an API key from https://www.eia.gov/opendata/. Daily granularity for the energy
series that drive water-treatment chemical pricing — finer than the FRED republish.

Why bother when FRED carries the same series?
- FRED is monthly. EIA Henry Hub is daily. For ammonia and chloramine procurement, daily
  resolution lets the Risk Monitor catch a 2-σ gas-price spike same-day.
- EIA exposes refinery utilization at weekly granularity — directly relevant to sulfur
  byproduct supply, which gates sulfuric acid and SO2 availability.

Series catalog (subset relevant to our 46 chemicals):
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import get_settings

_settings = get_settings()

API_URL = "https://api.eia.gov/v2"

# Series-id → human label
SERIES: dict[str, str] = {
    "NG.RNGWHHD.D": "Henry Hub natural gas spot, daily $/MMBtu",
    "PET.RWTC.D": "WTI crude oil spot, daily $/bbl",
    "PET.WPULEUS3.W": "US refinery percent utilization, weekly",
    "PET.WCRRIUS2.W": "US weekly crude inputs to refineries, thousand bbl/day",
    "ELEC.PRICE.US-ALL.M": "US average retail electricity price, monthly cents/kWh",
}


@dataclass
class EiaPoint:
    period: str
    value: float


async def fetch_series(series_id: str, *, length: int = 365) -> list[EiaPoint]:
    """Fetch the last ``length`` data points of an EIA series. Empty list if no key set
    or the API fails — callers should treat this as best-effort signal data."""
    if not _settings.eia_api_key:
        return []

    # The v2 API splits the series id by `.` into route segments. e.g. NG.RNGWHHD.D →
    # /v2/natural-gas/pri/fut/data ... but EIA also accepts the legacy `seriesid` query
    # against /v2/seriesid/{id} which is much simpler and stable.
    url = f"{API_URL}/seriesid/{series_id}"
    params: dict[str, Any] = {
        "api_key": _settings.eia_api_key,
        "length": length,
    }

    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            r = await client.get(url, params=params)
            if r.status_code != 200:
                return []
            data = r.json()
        except Exception:
            return []

    rows = (data.get("response") or {}).get("data", []) or []
    out: list[EiaPoint] = []
    for row in rows:
        period = row.get("period") or row.get("Period") or ""
        # The value field name varies by series; try the common ones.
        for key in ("value", "Value", "price", "Price"):
            v = row.get(key)
            if v is not None:
                try:
                    out.append(EiaPoint(period=str(period), value=float(v)))
                except (TypeError, ValueError):
                    pass
                break
    out.sort(key=lambda p: p.period)
    return out


async def latest(series_id: str) -> EiaPoint | None:
    pts = await fetch_series(series_id, length=5)
    return pts[-1] if pts else None
