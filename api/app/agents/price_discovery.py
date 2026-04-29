"""Price Discovery agent.

For a given chemical (and optional region/grade), produce a defensible market price benchmark
in dollars per kg of active ingredient by:

1. Crafting targeted search queries from the platform's `price_sources.json` source registry
   (e.g., "USGS Mineral Commodity Summaries 2026 aluminum sulfate price",
   "NSF/ANSI 60 ferric chloride supplier quote 2026", "BLS PPI WPU0613 chlorine April 2026").
2. Running the queries against the configured search API (Brave/Tavily/Exa/SerpAPI).
3. Fetching the top 3-5 most relevant pages and asking Claude to extract numeric price points
   with a confidence score and a citation URL.
4. Producing a typed PriceBenchmark with: low / median / high estimate, freshness, sources.

The platform uses these benchmarks for:
- RFP Builder: to suggest a "fair market price" reference number in the spec section.
- Bid Evaluator: as a column next to each supplier's normalized price, so the procurement
  officer can see which bids beat market and which are above.
- Risk Monitor: to flag price-shock alerts when latest median crosses 1.5σ over 90-day mean.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents.anthropic_client import get_client
from app.config import get_settings
from app.services.search import SearchResult, search_many

_settings = get_settings()

PRICE_SOURCES_PATH = Path(__file__).parent.parent / "intelligence" / "price_sources.json"
PRIORS_PATH = Path(__file__).parent.parent / "intelligence" / "chemical_priors.json"


def _load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


_PRICE_SOURCES = _load_json(PRICE_SOURCES_PATH)
_PRIORS = {c["name"].lower(): c for c in _load_json(PRIORS_PATH)["chemicals"]}


@dataclass
class PricePoint:
    value_usd_per_kg: float
    grade: str | None
    region: str | None
    freshness: str | None     # e.g., "Q1 2026", "April 2026", "2025"
    source_url: str
    source_name: str | None
    confidence: float         # 0.0-1.0
    raw_quote: str | None = None  # the literal sentence from the page


@dataclass
class PriceBenchmark:
    chemical: str
    cas_number: str | None
    low_usd_per_kg: float
    median_usd_per_kg: float
    high_usd_per_kg: float
    sample_size: int
    points: list[PricePoint] = field(default_factory=list)
    queries_used: list[str] = field(default_factory=list)
    methodology_note: str = ""


# Query templates — built from price_sources.json. Each chemical gets several queries that hit
# different parts of the price-discovery taxonomy: government series, trade press, RFP awards,
# producer disclosures, paid-source-summarized articles.
QUERY_TEMPLATES: dict[str, list[str]] = {
    # General-purpose templates that work for any chemical
    "generic": [
        '"{chemical}" price per ton 2026',
        '"{chemical}" $/kg market price 2026',
        '"{chemical}" RFP award price utility 2025 OR 2026',
        '"{chemical}" "per pound" OR "per kg" delivered price utility',
        '{chemical} producer price index 2026',
        '"{chemical}" {cas} contract price 2026',
        '"NSF/ANSI 60" "{chemical}" supplier quote',
    ],
    # Chemical-family-specific
    "aluminum_coagulant": [
        '"alum" OR "aluminum sulfate" "$/dry ton" 2026',
        '"polyaluminum chloride" PAC delivered price utility 2026',
        'AWWA "aluminum sulfate" RFP award 2025 OR 2026',
    ],
    "iron_coagulant": [
        '"ferric chloride" delivered price 2026 site:gov',
        '"ferric sulfate" "per gallon" OR "per dry ton" 2026',
        'spent pickling liquor ferric chloride spot 2026',
    ],
    "chlor_alkali": [
        'chlorine ECU price chlor-alkali Q1 2026',
        '"sodium hypochlorite" "per gallon" delivered 2026',
        '"calcium hypochlorite" price 2026 import India',
        'caustic soda spot price ICIS OR Argus 2026',
        'chlorine institute production shipment 2026',
    ],
    "phosphate": [
        '"phosphoric acid" food grade price 2026',
        '"zinc orthophosphate" price 2026 utility',
        '"sodium hexametaphosphate" SHMP price 2026',
        'phosphate rock fertilizer price Argus 2026',
    ],
    "ammonia": [
        '"anhydrous ammonia" Tampa benchmark price 2026',
        'Henry Hub natural gas ammonia 2026',
    ],
    "industrial_gas": [
        '"liquid oxygen" "per ton" merchant price 2026',
        '"liquid carbon dioxide" food grade utility 2026',
    ],
    "polymer_precursor": [
        'polyacrylamide cationic flocculant price 2026',
        'polyDADMAC coagulant delivered price 2026',
    ],
    "raw_mineral": [
        'USGS Mineral Commodity Summaries 2026 {chemical} price',
        'World Bank pink sheet {chemical} 2026',
    ],
}


PRICE_EXTRACTION_TOOL = {
    "name": "record_price_points",
    "description": "Record numeric price points found in the source page text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "points": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "value_usd_per_kg": {"type": "number"},
                        "grade": {"type": ["string", "null"]},
                        "region": {"type": ["string", "null"]},
                        "freshness": {"type": ["string", "null"], "description": "e.g., 'Q1 2026', 'April 2026', '2025'"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "raw_quote": {"type": "string"},
                    },
                    "required": ["value_usd_per_kg", "confidence", "raw_quote"],
                },
            }
        },
        "required": ["points"],
    },
}

EXTRACTION_SYSTEM = """You read a webpage and extract numeric price points for a specific water treatment chemical.

Strict rules:
- ONLY extract prices that are explicitly stated as a unit price for the chemical we're researching.
- Convert all prices to USD per KILOGRAM of active ingredient. Conversions:
    * $/lb → multiply by 2.20462
    * $/short ton → divide by 907.185
    * $/metric ton → divide by 1000
    * $/gallon (assume density 1.0 unless stated otherwise; flag low confidence)
    * Concentration: if the price is for a 49% solution, divide by 0.49 to get $/kg active.
- For confidence: 1.0 = explicit current contract/spot quote with units; 0.7 = stated number with some ambiguity (units inferred); 0.4 = a price mentioned in passing or historical.
- Skip irrelevant chemicals, generic 'inflation' commentary, equipment prices, and any price not tied to this chemical.
- Always include the literal sentence in raw_quote.
- If no price is present, call record_price_points with an empty points array.
"""


def _queries_for(chemical_name: str, cas: str | None, family: str | None) -> list[str]:
    fam_key = (family or "").lower()
    family_template_key = {
        "aluminum_coagulant": "aluminum_coagulant",
        "iron_coagulant": "iron_coagulant",
        "chlor_alkali": "chlor_alkali",
        "phosphate": "phosphate",
        "ammonia": "ammonia",
        "industrial_gas": "industrial_gas",
        "polymer_precursor": "polymer_precursor",
        "raw_mineral": "raw_mineral",
    }.get(fam_key)

    templates = QUERY_TEMPLATES["generic"][:]
    if family_template_key:
        templates += QUERY_TEMPLATES[family_template_key]

    queries: list[str] = []
    for t in templates:
        q = t.replace("{chemical}", chemical_name).replace("{cas}", cas or "")
        queries.append(q)
    return queries[:10]  # cap query count per discovery run


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=8))
async def _fetch_text(url: str, *, max_chars: int = 15000) -> str | None:
    """Best-effort page fetch. Returns None on failure rather than raising — we tolerate
    flaky pages because the search API gives us many redundant URLs."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers={"User-Agent": "Aquaprice/1.0"}) as client:
            r = await client.get(url)
            if r.status_code != 200 or not r.text:
                return None
            text = r.text
            # Strip HTML tags crudely; for production use a real parser.
            import re

            text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
            text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:max_chars]
    except Exception:
        return None


async def _extract_points(chemical: str, page_text: str, source_url: str, source_name: str | None) -> list[PricePoint]:
    """Ask Claude to extract numeric price points from a single page."""
    if not page_text:
        return []
    client = get_client()
    response = await client.messages.create(
        model=_settings.claude_model_default,
        max_tokens=1500,
        system=EXTRACTION_SYSTEM,
        tools=[PRICE_EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": "record_price_points"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Chemical: {chemical}\nSource URL: {source_url}\n\n"
                    f"Page text:\n---\n{page_text}\n---\n\n"
                    "Extract any USD-per-kg-active-ingredient prices via record_price_points."
                ),
            }
        ],
    )
    points: list[PricePoint] = []
    for block in response.content:
        if block.type == "tool_use" and block.name == "record_price_points":
            for raw in block.input.get("points", []):  # type: ignore[union-attr]
                points.append(
                    PricePoint(
                        value_usd_per_kg=float(raw["value_usd_per_kg"]),
                        grade=raw.get("grade"),
                        region=raw.get("region"),
                        freshness=raw.get("freshness"),
                        source_url=source_url,
                        source_name=source_name,
                        confidence=float(raw.get("confidence", 0.5)),
                        raw_quote=raw.get("raw_quote"),
                    )
                )
    return points


async def discover_price(
    chemical_name: str,
    *,
    cas_number: str | None = None,
    family: str | None = None,
    region: str | None = None,
    max_pages: int = 5,
) -> PriceBenchmark:
    """Top-level entrypoint. Returns a PriceBenchmark."""
    prior = _PRIORS.get(chemical_name.lower(), {})
    cas = cas_number or prior.get("cas")
    fam = family or prior.get("family")

    queries = _queries_for(chemical_name, cas, fam)
    if region:
        queries = [f"{q} {region}" for q in queries]

    # Run all queries (bounded concurrency)
    results_by_query = await search_many(queries, count=6, freshness="py", concurrency=4)

    # Deduplicate URLs across queries; keep ranking by query order.
    seen: set[str] = set()
    candidates: list[SearchResult] = []
    for q in queries:
        for r in results_by_query.get(q, []):
            if r.url and r.url not in seen:
                seen.add(r.url)
                candidates.append(r)

    # Filter to most likely price-bearing pages
    price_keywords = ("price", "$", "per kg", "per ton", "per pound", "per gallon", "per lb", "ppi", "rfp", "bid", "award", "tariff")
    scored = [
        (sum(1 for k in price_keywords if k in (r.snippet or "").lower()) + (1 if any(k in (r.title or "").lower() for k in price_keywords) else 0), r)
        for r in candidates
    ]
    scored.sort(key=lambda t: t[0], reverse=True)
    top = [r for _score, r in scored[:max_pages]]

    # Fetch pages in parallel; extract points
    import asyncio as _aio
    pages = await _aio.gather(*(_fetch_text(r.url) for r in top))
    extractions = await _aio.gather(
        *(_extract_points(chemical_name, txt or "", r.url, r.source) for r, txt in zip(top, pages))
    )
    points: list[PricePoint] = [p for batch in extractions for p in batch]

    # Filter implausibly out-of-range points (defense against bad extractions).
    # Most water-treatment chemicals are $0.10 - $5.00 per kg active. KMnO4, polymers, and
    # specialty FSA can run $5-$25/kg. Reject anything < $0.01 or > $100.
    points = [p for p in points if 0.01 <= p.value_usd_per_kg <= 100.0]
    # Down-weight low-confidence points by dropping them from the median calc but keeping
    # them in the citation list.
    high_conf = [p.value_usd_per_kg for p in points if p.confidence >= 0.5]
    if not high_conf:
        return PriceBenchmark(
            chemical=chemical_name,
            cas_number=cas,
            low_usd_per_kg=0.0,
            median_usd_per_kg=0.0,
            high_usd_per_kg=0.0,
            sample_size=0,
            points=points,
            queries_used=queries,
            methodology_note="No high-confidence price points found. The Bid Evaluator should treat any returned median as advisory.",
        )

    return PriceBenchmark(
        chemical=chemical_name,
        cas_number=cas,
        low_usd_per_kg=min(high_conf),
        median_usd_per_kg=median(high_conf),
        high_usd_per_kg=max(high_conf),
        sample_size=len(high_conf),
        points=points,
        queries_used=queries,
        methodology_note=(
            f"Median across {len(high_conf)} high-confidence price points (confidence ≥ 0.5) "
            f"sourced via {_settings.search_provider} search; LLM extraction normalized all units to USD per kg of active ingredient."
        ),
    )
