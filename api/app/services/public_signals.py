"""Public-data signal sources.

Free, authoritative APIs that complement the search service. These don't consume search
credits and tend to have better latency and reliability than search-aggregated news.

Implemented:
- FRED PPI series (BLS via St. Louis Fed) — chlor-alkali index, industrial chemicals
- USGS earthquake feed
- NOAA NHC active tropical cyclones
- SEC EDGAR full-text search (force majeure 8-K filings)
- EPA ECHO facility lookup (NPDES violations near a producer)
- GDELT 2.0 doc API (free news with country/category filters)

Each function returns plain dicts/lists ready for JSON serialization.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from app.config import get_settings

_settings = get_settings()

# Map water-treatment-relevant PPI series IDs (BLS via FRED).
# Series codes pulled from the BLS PPI catalog used in the corpus.
FRED_PPI: dict[str, str] = {
    "industrial_chemicals_composite": "WPU0613",
    "chlor_alkali": "WPU06130302",
    "sodium_hydroxide": "WPU0613020X",
    "alkalies_chlorine": "WPU0613",
    "natural_gas_henry_hub": "DHHNGSP",   # daily Henry Hub spot
    "wti_crude": "DCOILWTICO",
    "potash_world_bank": "PPOTASHUSDM",
    "phosphate_rock_world_bank": "PPHOSPHATESUSDM",
}


async def fred_series(series_id: str, *, observation_start: str | None = None) -> list[dict]:
    """Fetch a FRED CSV series and return [{date, value}]. No API key required for graph endpoint."""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    if observation_start:
        url += f"&cosd={observation_start}"
    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.get(url)
        if r.status_code != 200:
            return []
    out: list[dict] = []
    for line in r.text.splitlines()[1:]:
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) < 2:
            continue
        d, v = parts[0].strip(), parts[1].strip()
        if v in (".", ""):
            continue
        try:
            out.append({"date": d, "value": float(v)})
        except ValueError:
            continue
    return out


async def usgs_earthquakes(*, min_magnitude: float = 4.5, hours: int = 24) -> list[dict]:
    """Recent significant earthquakes — feedstock-region exposure (e.g., Chile lithium, Peru phosphate)."""
    feed = "all_day" if hours <= 24 else "all_week"
    url = f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{feed}.geojson"
    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.get(url)
        if r.status_code != 200:
            return []
        data = r.json()
    out = []
    for f in data.get("features", []):
        props = f.get("properties", {})
        if (props.get("mag") or 0) < min_magnitude:
            continue
        out.append(
            {
                "magnitude": props.get("mag"),
                "place": props.get("place"),
                "time": datetime.fromtimestamp((props.get("time") or 0) / 1000, tz=timezone.utc).isoformat(),
                "url": props.get("url"),
            }
        )
    return out


async def nhc_active_storms() -> list[dict]:
    """Active tropical cyclones from NOAA NHC — Gulf Coast petrochem proximity is the procurement signal."""
    url = "https://www.nhc.noaa.gov/CurrentStorms.json"
    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.get(url)
        if r.status_code != 200:
            return []
        data = r.json()
    return [
        {
            "name": s.get("name"),
            "classification": s.get("classification"),
            "intensity": s.get("intensity"),
            "basin": s.get("binNumber"),
            "lat": s.get("lat"),
            "lon": s.get("lon"),
            "advisory_url": s.get("publicAdvisory", {}).get("url") if isinstance(s.get("publicAdvisory"), dict) else None,
        }
        for s in data.get("activeStorms", [])
    ]


async def sec_edgar_force_majeure(*, days: int = 30) -> list[dict]:
    """SEC EDGAR full-text search for recent 8-K filings mentioning force majeure or unplanned outage."""
    url = (
        "https://efts.sec.gov/LATEST/search-index"
        '?q=%22force+majeure%22+OR+%22unplanned+outage%22'
        "&forms=8-K"
        f"&dateRange=custom&startdt={(datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')}"
        f"&enddt={datetime.utcnow().strftime('%Y-%m-%d')}"
    )
    async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": "Aquaprice research aquaprice@example.com"}) as client:
        r = await client.get(url)
        if r.status_code != 200:
            return []
        data = r.json()
    hits = (data.get("hits") or {}).get("hits", []) or []
    out = []
    for h in hits[:50]:
        src = h.get("_source", {})
        out.append(
            {
                "company": src.get("display_names", []),
                "form": src.get("form"),
                "filed": src.get("file_date"),
                "url": f"https://www.sec.gov/Archives/edgar/data/{src.get('ciks', [''])[0]}/{src.get('adsh','').replace('-', '')}/{src.get('xsl','')}".rstrip("/"),
                "matched": src.get("snippet"),
            }
        )
    return out


async def gdelt_news(query: str, *, hours: int = 24, max_records: int = 50) -> list[dict]:
    """GDELT 2.0 Doc API — free, no key, 15-minute cadence."""
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "JSON",
        "maxrecords": max_records,
        "timespan": f"{hours}h",
    }
    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.get("https://api.gdeltproject.org/api/v2/doc/doc", params=params)
        if r.status_code != 200:
            return []
        try:
            data = r.json()
        except Exception:
            return []
    return [
        {
            "title": a.get("title"),
            "url": a.get("url"),
            "domain": a.get("domain"),
            "seendate": a.get("seendate"),
            "language": a.get("language"),
        }
        for a in data.get("articles", []) or []
    ]


async def epa_echo_facilities(*, state: str | None = None, sic_code: str = "2812") -> list[dict]:
    """EPA ECHO facility lookup. SIC 2812 = Alkalies and Chlorine. Returns recent NPDES violations."""
    params = {
        "output": "JSON",
        "p_sic": sic_code,
    }
    if state:
        params["p_st"] = state
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get("https://echodata.epa.gov/echo/efs_rest_services.get_facilities", params=params)
        if r.status_code != 200:
            return []
        try:
            data = r.json()
        except Exception:
            return []
    return [
        {
            "name": (f or {}).get("FacName"),
            "city": (f or {}).get("FacCity"),
            "state": (f or {}).get("FacState"),
            "violations_3yr": (f or {}).get("CWAQtrsWithNC"),
            "url": (f or {}).get("FacDerivedHuc"),
        }
        for f in (data.get("Results", {}) or {}).get("Facilities", [])[:50]
    ]
