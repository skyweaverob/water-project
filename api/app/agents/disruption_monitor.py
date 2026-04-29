"""Disruption Monitor agent.

For a chemical (or a portfolio of chemicals), search the live web for force-majeure
declarations, plant outages, hurricane/winter-storm impact on Gulf Coast petrochem,
chlor-alkali capacity changes, antidumping duty orders, rail incidents, and any other
documented event that would shift the buy-side risk score over the next 30-90 days.

Returns DisruptionEvents that are:
  - Persisted to the `disruption_events` table for the affected chemical(s).
  - Routed to RiskAlerts when severity meets threshold.

Used by the Risk Monitor's nightly worker job.
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
class DisruptionEvent:
    chemical: str
    severity: str            # info | watch | warning
    headline: str
    body: str
    event_type: str          # force_majeure | weather | tariff | plant_closure | antidumping | rail | other
    source_url: str
    published_at: str | None
    confidence: float


@dataclass
class DisruptionScan:
    chemical: str
    events: list[DisruptionEvent] = field(default_factory=list)
    queries_used: list[str] = field(default_factory=list)


DISRUPTION_TOOL = {
    "name": "record_disruptions",
    "description": "Record material supply chain disruption events from the search results.",
    "input_schema": {
        "type": "object",
        "properties": {
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "headline": {"type": "string"},
                        "body": {"type": "string"},
                        "event_type": {
                            "type": "string",
                            "enum": [
                                "force_majeure",
                                "weather",
                                "tariff",
                                "plant_closure",
                                "antidumping",
                                "rail",
                                "feedstock",
                                "labor",
                                "other",
                            ],
                        },
                        "severity": {"type": "string", "enum": ["info", "watch", "warning"]},
                        "source_url": {"type": "string"},
                        "published_at": {"type": ["string", "null"]},
                        "confidence": {"type": "number"},
                    },
                    "required": ["headline", "body", "event_type", "severity", "source_url", "confidence"],
                },
            }
        },
        "required": ["events"],
    },
}

DISRUPTION_SYSTEM = """You read news search results and extract supply chain disruption events for water treatment chemicals.

Severity guide:
- info: a future risk or generic commentary, no impact on supply yet.
- watch: a real event that may affect availability/pricing within 30-90 days (e.g., hurricane track approaching, antidumping investigation opened).
- warning: a confirmed disruption already affecting supply (force majeure declared, plant closed, allocation announced, tariff in effect).

Rules:
- Skip stock-market noise, generic earnings, ESG marketing, equipment-vendor PR.
- Skip events older than 60 days unless they reveal a still-active disruption.
- Always include the source URL.
- Confidence: 1.0 = official supplier or government announcement; 0.7 = trade press; 0.4 = aggregator/blog.
- Prefer specificity over volume: 3 high-quality events beats 10 vague ones."""


# Family-aware feedstock and weather queries — encodes the supply chain patterns from corpus_intelligence.md
FEEDSTOCK_BY_FAMILY: dict[str, list[str]] = {
    "aluminum_coagulant": ['"bauxite" supply shortage 2026', '"aluminum hydroxide" force majeure 2026'],
    "iron_coagulant": ['"steel pickling" liquor shortage 2026', 'spent pickling liquor recycling 2026'],
    "chlor_alkali": [
        'chlor-alkali capacity outage 2026',
        '"chlorine" force majeure 2026',
        '"sodium hydroxide" allocation 2026',
        'Winter Storm Gulf Coast chlor-alkali 2026',
        'hurricane Gulf Coast petrochemical 2026',
    ],
    "phosphate": [
        'phosphate rock supply 2026',
        '"Mosaic" phosphate force majeure 2026',
        'phosphoric acid utility allocation 2026',
    ],
    "ammonia": ['"anhydrous ammonia" force majeure 2026', "Henry Hub natural gas spike ammonia 2026"],
    "industrial_gas": ['"liquid oxygen" shortage hospital 2026', '"liquid carbon dioxide" shortage 2026'],
    "polymer_precursor": ['"acrylonitrile" force majeure 2026', '"allyl chloride" outage 2026', "SNF Holding capacity 2026"],
    "raw_mineral": ["USGS mineral shortage 2026", "critical minerals supply disruption water treatment 2026"],
}


def _queries(chemical: str, family: str | None) -> list[str]:
    base = [
        f'"{chemical}" force majeure 2025 OR 2026',
        f'"{chemical}" supply chain disruption 2026',
        f'"{chemical}" plant closure OR allocation 2025 OR 2026',
        f'"{chemical}" antidumping countervailing duty 2026',
        f'"{chemical}" water utility shortage 2026',
    ]
    fam = FEEDSTOCK_BY_FAMILY.get((family or "").lower(), [])
    return base + fam


async def scan_chemical(chemical_name: str, *, family: str | None = None) -> DisruptionScan:
    prior = _PRIORS.get(chemical_name.lower(), {})
    fam = family or prior.get("family")
    queries = _queries(chemical_name, fam)
    results_by_query = await search_many(queries, count=6, freshness="pm", concurrency=4)

    snippets: list[str] = []
    for q, results in results_by_query.items():
        for r in results[:4]:
            if r.snippet:
                snippets.append(f"[{r.url}] ({r.published_at or 'no date'}) {r.title}: {r.snippet}")

    if not snippets:
        return DisruptionScan(chemical=chemical_name, events=[], queries_used=queries)

    client = get_client()
    response = await client.messages.create(
        model=_settings.claude_model_default,
        max_tokens=2000,
        system=DISRUPTION_SYSTEM,
        tools=[DISRUPTION_TOOL],
        tool_choice={"type": "tool", "name": "record_disruptions"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"Chemical: {chemical_name}\nFamily: {fam}\n\n"
                    "Extract the material disruption events from the snippets via record_disruptions. "
                    "Aim for ≤8 of the most operationally relevant events.\n\n"
                    + "\n".join(snippets[:50])
                ),
            }
        ],
    )

    events: list[DisruptionEvent] = []
    for block in response.content:
        if block.type == "tool_use" and block.name == "record_disruptions":
            for raw in block.input.get("events", []):  # type: ignore[union-attr]
                # Defensive: tool schema marks these required, but we should not let a
                # malformed tool_use crash the entire daily worker run.
                headline = raw.get("headline")
                body = raw.get("body")
                if not headline or not body:
                    continue
                events.append(
                    DisruptionEvent(
                        chemical=chemical_name,
                        severity=raw.get("severity", "info"),
                        headline=headline,
                        body=body,
                        event_type=raw.get("event_type", "other"),
                        source_url=raw.get("source_url", ""),
                        published_at=raw.get("published_at"),
                        confidence=float(raw.get("confidence", 0.6)),
                    )
                )
    return DisruptionScan(chemical=chemical_name, events=events, queries_used=queries)
