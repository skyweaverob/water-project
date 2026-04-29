"""Phase 1 extraction agent.

Reads an EPA Supply Chain Profile PDF, extracts structured fields, returns a typed payload
plus per-field confidence scores. Uses Claude (claude-sonnet-4-5 by default) with a single
extraction prompt, structured-output via tool-use, and a deterministic post-validator.

The agent does NOT write to the database directly. The caller (`ingestion/run.py`) takes the
returned payload and persists it. This keeps the agent pure and testable.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pdfplumber
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents.anthropic_client import get_client
from app.config import get_settings

_settings = get_settings()


SECTION_HEADINGS = (
    "Product Description",
    "Use in Water Treatment",
    "Use as a Precursor to Other Water Treatment Chemicals",
    "Other Applications",
    "Primary Industrial Consumers",
    "Manufacturing, Transport, & Storage",
    "Manufacturing Process",
    "Product Transport",
    "Storage and Shelf Life",
    "Domestic Production & Consumption",
    "Domestic Production",
    "Domestic Consumption",
    "Trade & Tariffs",
    "Worldwide Trade",
    "Domestic Imports and Exports",
    "Tariffs",
    "Market History & Risk Evaluation",
    "History of Shortages",
    "Risk Evaluation",
    "References",
)


@dataclass
class ExtractedSection:
    page_num: int
    section: str
    text: str


@dataclass
class ExtractionResult:
    fields: dict[str, Any] = field(default_factory=dict)
    applications: list[dict] = field(default_factory=list)
    manufacturing_locations: list[dict] = field(default_factory=list)
    trade_data: list[dict] = field(default_factory=list)
    risk_assessment: dict = field(default_factory=dict)
    disruption_events: list[dict] = field(default_factory=list)
    substitutes_and_precursors: list[dict] = field(default_factory=list)
    sections: list[ExtractedSection] = field(default_factory=list)
    confidence: dict[str, float] = field(default_factory=dict)
    raw_text: str = ""


def parse_pdf(pdf_path: Path) -> tuple[str, list[ExtractedSection]]:
    """Extract full text + section-tagged page chunks from an EPA fact sheet."""
    full_text_parts: list[str] = []
    sections: list[ExtractedSection] = []
    current_section = "Executive Summary"

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            full_text_parts.append(page_text)

            for heading in SECTION_HEADINGS:
                if re.search(rf"^{re.escape(heading)}\s*$", page_text, re.MULTILINE):
                    current_section = heading
                    break

            sections.append(ExtractedSection(page_num=i, section=current_section, text=page_text))

    return "\n\n".join(full_text_parts), sections


EXTRACTION_TOOL_SCHEMA = {
    "name": "record_chemical_profile",
    "description": "Record the structured fields extracted from an EPA chemical supply-chain profile.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "cas_number": {"type": ["string", "null"]},
            "molecular_formula": {"type": ["string", "null"]},
            "physical_state": {"type": ["string", "null"]},
            "shelf_life_months": {"type": ["integer", "null"]},
            "product_family": {"type": ["string", "null"]},
            "water_treatment_use": {"type": ["string", "null"]},
            "is_direct_treatment_chemical": {"type": "boolean"},
            "is_precursor": {"type": "boolean"},
            "derivative_chemicals": {"type": "array", "items": {"type": "string"}},
            "pct_consumption_water_sector": {"type": ["number", "null"]},
            "applications": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "application_type": {"type": "string", "enum": ["water_treatment", "other"]},
                        "description": {"type": "string"},
                    },
                    "required": ["application_type", "description"],
                },
            },
            "manufacturing_locations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "country": {"type": ["string", "null"]},
                        "state": {"type": ["string", "null"]},
                        "facility_count": {"type": ["integer", "null"]},
                        "year": {"type": ["integer", "null"]},
                        "source": {"type": ["string", "null"]},
                    },
                },
            },
            "trade_data": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "year": {"type": "integer"},
                        "imports_kg": {"type": ["number", "null"]},
                        "exports_kg": {"type": ["number", "null"]},
                        "primary_import_partner": {"type": ["string", "null"]},
                        "primary_export_partner": {"type": ["string", "null"]},
                        "hts_code": {"type": ["string", "null"]},
                        "general_duty_pct": {"type": ["number", "null"]},
                        "china_section_301_duty_pct": {"type": ["number", "null"]},
                        "special_duty_countries": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["year"],
                },
            },
            "risk_assessment": {
                "type": "object",
                "properties": {
                    "assessment_year": {"type": ["integer", "null"]},
                    "criticality": {"type": ["string", "null"]},
                    "likelihood": {"type": ["string", "null"]},
                    "vulnerability": {"type": ["string", "null"]},
                    "composite_rating": {"type": ["string", "null"]},
                    "criticality_drivers": {"type": ["string", "null"]},
                    "likelihood_drivers": {"type": ["string", "null"]},
                    "vulnerability_drivers": {"type": ["string", "null"]},
                },
            },
            "disruption_events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "event_year": {"type": ["integer", "null"]},
                        "event_type": {"type": ["string", "null"]},
                        "description": {"type": "string"},
                        "source_citation": {"type": ["string", "null"]},
                    },
                },
            },
            "substitutes_and_precursors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "related_chemical_name": {"type": "string"},
                        "relationship_type": {
                            "type": "string",
                            "enum": ["substitute", "precursor", "derivative", "feedstock"],
                        },
                        "notes": {"type": ["string", "null"]},
                    },
                    "required": ["related_chemical_name", "relationship_type"],
                },
            },
            "confidence": {
                "type": "object",
                "description": "Per-field confidence 0.0-1.0",
                "additionalProperties": {"type": "number"},
            },
        },
        "required": ["name", "is_direct_treatment_chemical", "is_precursor"],
    },
}


SYSTEM_PROMPT = """You are an extraction agent for EPA Water Treatment Chemical Supply Chain Profiles. Your job is to read the full text of one fact sheet and emit structured fields by calling the record_chemical_profile tool.

Rules:
- Only extract values that are explicitly stated in the document. Do not infer.
- Use the exact spelling and casing the EPA uses (e.g., "Moderate-High", "Aluminum Sulfate").
- For percentages, return the numeric value (45 not "45%").
- For mass values in trade_data, convert "M kg" to kg (multiply by 1,000,000), "K kg" to kg (multiply by 1,000). Always emit raw kg.
- For each field you populate, also include a confidence score 0.0-1.0 in the `confidence` object, keyed by the field name. 1.0 = directly stated; 0.7 = stated but ambiguous; 0.4 = inferred from context. Skip fields you can't ground.
- If a field is not present in the document, omit it from the output rather than guessing.
- For risk_assessment composite_rating use one of: Low, Moderate-Low, Moderate, Moderate-High, High.
- water_treatment_use: one short sentence describing the chemical's function (e.g. "Coagulation in drinking water and wastewater treatment").
- is_direct_treatment_chemical: true if the document marks it "Direct Use Chemical" or describes direct use in water treatment.
- is_precursor: true if the document describes use as a precursor to make other treatment chemicals."""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
async def call_extraction_model(text: str, chemical_hint: str) -> dict:
    client = get_client()
    response = await client.messages.create(
        model=_settings.claude_model_default,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        tools=[EXTRACTION_TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "record_chemical_profile"},
        messages=[
            {
                "role": "user",
                "content": (
                    f"The chemical is named approximately: {chemical_hint}\n\n"
                    f"Full document text follows.\n\n---\n\n{text}\n\n---\n\n"
                    "Call record_chemical_profile with the structured extraction."
                ),
            }
        ],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "record_chemical_profile":
            return block.input  # type: ignore[return-value]
    raise RuntimeError("Model did not call record_chemical_profile.")


async def extract(pdf_path: Path) -> ExtractionResult:
    raw_text, sections = parse_pdf(pdf_path)

    # Best-effort hint from filename: "Aluminum Sulfate Supply Chain Profile.pdf" -> "Aluminum Sulfate"
    name_hint = pdf_path.stem.replace("_0", "").replace("Supply Chain Profile", "").strip()

    payload = await call_extraction_model(raw_text, name_hint)

    result = ExtractionResult(
        fields={
            k: payload.get(k)
            for k in (
                "name",
                "cas_number",
                "molecular_formula",
                "physical_state",
                "shelf_life_months",
                "product_family",
                "water_treatment_use",
                "is_direct_treatment_chemical",
                "is_precursor",
                "derivative_chemicals",
                "pct_consumption_water_sector",
            )
            if k in payload
        },
        applications=payload.get("applications", []) or [],
        manufacturing_locations=payload.get("manufacturing_locations", []) or [],
        trade_data=payload.get("trade_data", []) or [],
        risk_assessment=payload.get("risk_assessment", {}) or {},
        disruption_events=payload.get("disruption_events", []) or [],
        substitutes_and_precursors=payload.get("substitutes_and_precursors", []) or [],
        sections=sections,
        confidence=payload.get("confidence", {}) or {},
        raw_text=raw_text,
    )

    if "name" not in result.fields or not result.fields.get("name"):
        result.fields["name"] = name_hint
        result.confidence["name"] = 0.5

    return result


def serialize_for_review(result: ExtractionResult) -> str:
    """Pretty-print extraction for human review during ingestion."""
    return json.dumps(
        {
            "fields": result.fields,
            "applications": result.applications,
            "manufacturing_locations": result.manufacturing_locations,
            "trade_data": result.trade_data,
            "risk_assessment": result.risk_assessment,
            "disruption_events": result.disruption_events,
            "substitutes_and_precursors": result.substitutes_and_precursors,
            "confidence": result.confidence,
        },
        indent=2,
        default=str,
    )
