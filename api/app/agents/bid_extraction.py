"""Bid document extractor.

Reads a supplier-submitted bid (PDF or text) and asks Claude to extract the line items into
the BidLine schema used by the Bid Evaluator. Tool-use ensures structured output.
"""
from __future__ import annotations

from pathlib import Path

import pdfplumber
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents.anthropic_client import get_client
from app.config import get_settings

_settings = get_settings()


BID_EXTRACTION_TOOL = {
    "name": "record_bid",
    "description": "Record the structured bid extracted from a supplier's response.",
    "input_schema": {
        "type": "object",
        "properties": {
            "supplier_name": {"type": "string"},
            "submitted_at": {"type": ["string", "null"], "description": "ISO date if present"},
            "freight_terms": {"type": ["string", "null"]},
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "unit": {"type": "string", "enum": ["kg", "lb", "ton", "gal"]},
                        "unit_price": {"type": "number"},
                        "delivered_concentration_pct": {"type": ["number", "null"]},
                    },
                    "required": ["description", "unit", "unit_price"],
                },
            },
        },
        "required": ["supplier_name", "line_items"],
    },
}


SYSTEM_PROMPT = """You read supplier bid responses for water-treatment chemical procurement and extract structured pricing.

Rules:
- Output ONLY by calling record_bid.
- For unit_price use the literal price stated. Do not normalize across units.
- For delivered_concentration_pct, use the active-ingredient concentration the bidder commits to (e.g. 49 for "49% solution"). Leave null if not specified.
- If the bid lists a per-gallon price, set unit to "gal" — the downstream evaluator handles conversion.
- Do not invent line items. If the bid is unstructured prose, extract a single line item describing the offer.
"""


def parse_bid_pdf(path: Path) -> str:
    text = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text.append(page.extract_text() or "")
    return "\n\n".join(text)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=15))
async def extract_bid(text: str) -> dict:
    client = get_client()
    response = await client.messages.create(
        model=_settings.claude_model_default,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        tools=[BID_EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": "record_bid"},
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract the bid using record_bid. Bid response follows.\n\n"
                    f"---\n{text}\n---"
                ),
            }
        ],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "record_bid":
            return block.input  # type: ignore[return-value]
    raise RuntimeError("record_bid tool was not called.")
