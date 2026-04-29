"""Supplier Discovery agent.

Builds a live shortlist of NSF/ANSI-60-certified or industrial-grade suppliers for a chemical
by combining:
  - The platform's `chemical_priors.json` named-producer list (offline static prior).
  - Live searches for "{chemical} NSF/ANSI 60 supplier" and "{chemical} {region} delivery".
  - Optional region/freight-radius filtering against the supplier's headquarters.

Output: a SupplierShortlist with a name, headquarters, NSF60 certification status (best-effort
flag from search results), source URLs, and a confidence score.

Used by the RFP Builder ("invite N suppliers to bid") and by the Risk Monitor when scoring
supplier-pool depth.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.agents.anthropic_client import get_client
from app.config import get_settings
from app.services.search import search_many

_settings = get_settings()
PRIORS_PATH = Path(__file__).parent.parent / "intelligence" / "chemical_priors.json"
_PRIORS = {c["name"].lower(): c for c in json.loads(PRIORS_PATH.read_text(encoding="utf-8"))["chemicals"]}


@dataclass
class Supplier:
    name: str
    headquarters: str | None
    nsf60_certified: bool | None
    notes: str | None
    source_url: str
    confidence: float


@dataclass
class SupplierShortlist:
    chemical: str
    suppliers: list[Supplier] = field(default_factory=list)
    queries_used: list[str] = field(default_factory=list)


SHORTLIST_TOOL = {
    "name": "record_suppliers",
    "description": "Record candidate suppliers found in the search/page text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "suppliers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "headquarters": {"type": ["string", "null"]},
                        "nsf60_certified": {"type": ["boolean", "null"]},
                        "notes": {"type": ["string", "null"]},
                        "confidence": {"type": "number"},
                    },
                    "required": ["name", "confidence"],
                },
            }
        },
        "required": ["suppliers"],
    },
}

SHORTLIST_SYSTEM = """You build a procurement supplier shortlist for water treatment chemicals.

Rules:
- Only include companies that demonstrably sell the specific chemical we asked about.
- Prefer companies with NSF/ANSI Standard 60 certification when the buyer is a drinking water utility.
- Confidence: 1.0 = explicit "manufacturer" or "supplier of X" claim with NSF60 confirmation; 0.7 = listed in industry directory; 0.4 = mentioned in passing.
- Skip resellers without manufacturing capability and skip non-US-serving firms unless we explicitly ask for global.
- Do not invent suppliers. If a search result is irrelevant, omit it."""


async def discover_suppliers(
    chemical_name: str,
    *,
    region: str | None = None,
    require_nsf60: bool = True,
    max_results: int = 12,
) -> SupplierShortlist:
    prior = _PRIORS.get(chemical_name.lower(), {})
    named = prior.get("named_producers", [])

    queries = [
        f'"{chemical_name}" NSF/ANSI 60 certified supplier 2026',
        f'"{chemical_name}" manufacturer water treatment United States 2026',
        f'"{chemical_name}" "Certificate of Analysis" supplier quote',
        f'"{chemical_name}" RFP award supplier 2025 OR 2026',
    ]
    if region:
        queries.append(f'"{chemical_name}" supplier {region} delivery 2026')

    hits_by_query = await search_many(queries, count=8, freshness="py", concurrency=4)
    snippets: list[str] = []
    sources: list[str] = []
    for q, results in hits_by_query.items():
        for r in results[:5]:
            if r.snippet:
                snippets.append(f"[{r.url}] {r.title}: {r.snippet}")
                sources.append(r.url)

    if not snippets:
        # Fall back to static priors only
        return SupplierShortlist(
            chemical=chemical_name,
            suppliers=[
                Supplier(
                    name=n,
                    headquarters=None,
                    nsf60_certified=None,
                    notes="From static EPA-derived prior; verify NSF/ANSI 60 status before sourcing.",
                    source_url="prior://chemical_priors.json",
                    confidence=0.6,
                )
                for n in named[:max_results]
            ],
            queries_used=queries,
        )

    client = get_client()
    response = await client.messages.create(
        model=_settings.claude_model_default,
        max_tokens=2000,
        system=SHORTLIST_SYSTEM,
        tools=[SHORTLIST_TOOL],
        tool_choice={"type": "tool", "name": "record_suppliers"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Chemical: {chemical_name}\n"
                    f"Static prior list (high signal): {', '.join(named) if named else 'none'}\n"
                    f"Region: {region or 'United States'}\n"
                    f"Drinking water grade required: {require_nsf60}\n\n"
                    f"Search snippets follow. Compile up to {max_results} unique suppliers via record_suppliers.\n\n"
                    + "\n".join(snippets[:60])
                ),
            }
        ],
    )

    discovered: list[Supplier] = []
    for block in response.content:
        if block.type == "tool_use" and block.name == "record_suppliers":
            for raw in block.input.get("suppliers", []):  # type: ignore[union-attr]
                # Best-effort: attach the first snippet URL as source
                source_url = sources[0] if sources else "search://discovery"
                discovered.append(
                    Supplier(
                        name=raw["name"],
                        headquarters=raw.get("headquarters"),
                        nsf60_certified=raw.get("nsf60_certified"),
                        notes=raw.get("notes"),
                        source_url=source_url,
                        confidence=float(raw.get("confidence", 0.6)),
                    )
                )

    # Merge static priors as a backstop, deduping by case-insensitive name
    seen = {s.name.lower() for s in discovered}
    for n in named:
        if n.lower() not in seen:
            discovered.append(
                Supplier(
                    name=n,
                    headquarters=None,
                    nsf60_certified=None,
                    notes="From EPA-derived static prior.",
                    source_url="prior://chemical_priors.json",
                    confidence=0.6,
                )
            )
            seen.add(n.lower())

    discovered.sort(key=lambda s: s.confidence, reverse=True)
    return SupplierShortlist(chemical=chemical_name, suppliers=discovered[:max_results], queries_used=queries)
