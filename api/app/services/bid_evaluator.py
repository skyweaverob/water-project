"""Bid Evaluator.

Normalizes supplier bids to dollars per kg of *active ingredient delivered*, applies
risk-weighted scoring per the RFP's evaluation weights, and produces a board- or
corporate-ready award memo PDF.

The memo cites the EPA fact sheet directly when justifying risk-weighted scoring decisions.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# Risk band → numerical risk multiplier used when computing risk-adjusted score.
# Higher band → larger multiplier penalty, which downweights cheap-but-risky bids.
RISK_PENALTY: dict[str, float] = {
    "Low": 0.00,
    "Moderate-Low": 0.05,
    "Moderate": 0.10,
    "Moderate-High": 0.18,
    "High": 0.25,
}


@dataclass
class BidLine:
    description: str
    unit: str               # kg, gal, lb, ton
    unit_price: float       # dollars per `unit`
    delivered_concentration_pct: float | None = None  # % active ingredient (e.g., 49 for 49% alum)


@dataclass
class BidExtract:
    supplier_name: str
    line_items: list[BidLine]
    submitted_at: str | None = None


@dataclass
class NormalizedBid:
    supplier_name: str
    normalized_price_per_kg_active: float
    is_conforming: bool
    nonconformance_notes: list[str]
    line_items: list[BidLine]


# Unit conversions to kg
UNIT_TO_KG: dict[str, float] = {
    "kg": 1.0,
    "lb": 0.45359237,
    "ton": 907.18474,        # short ton, common in U.S. industry
    "gal": 3.785,            # liters; assumes density 1.0; see note below
}


def normalize_bid(bid: BidExtract, default_concentration: float | None = None) -> NormalizedBid:
    """Normalize line items to $/kg of active ingredient.

    Logic:
    - Convert price to $/kg using UNIT_TO_KG.
    - For liquid products in gallons we assume density 1.0 unless the bid lists density —
      this is a known approximation for most aqueous chemicals near 1.0; specialty chemicals
      should override.
    - Divide by delivered_concentration_pct/100 to express as price per kg of *active*
      ingredient. If a bidder fails to specify concentration, the bid is flagged
      non-conforming.
    """
    if not bid.line_items:
        return NormalizedBid(
            supplier_name=bid.supplier_name,
            normalized_price_per_kg_active=float("inf"),
            is_conforming=False,
            nonconformance_notes=["No line items provided."],
            line_items=[],
        )

    # Use the lowest-priced primary line item that fully specifies the product.
    primary: BidLine | None = None
    notes: list[str] = []

    for li in bid.line_items:
        if li.unit not in UNIT_TO_KG:
            notes.append(f"Unit '{li.unit}' is not supported; line skipped.")
            continue
        if li.delivered_concentration_pct is None and default_concentration is None:
            notes.append(f"Line '{li.description}' missing delivered concentration; cannot normalize.")
            continue
        if primary is None or li.unit_price < primary.unit_price:
            primary = li

    if primary is None:
        return NormalizedBid(
            supplier_name=bid.supplier_name,
            normalized_price_per_kg_active=float("inf"),
            is_conforming=False,
            nonconformance_notes=notes or ["No conforming line item."],
            line_items=bid.line_items,
        )

    conc = primary.delivered_concentration_pct or default_concentration or 100.0
    price_per_kg = primary.unit_price / UNIT_TO_KG[primary.unit]
    price_per_kg_active = price_per_kg / (conc / 100.0)

    return NormalizedBid(
        supplier_name=bid.supplier_name,
        normalized_price_per_kg_active=price_per_kg_active,
        is_conforming=not notes,
        nonconformance_notes=notes,
        line_items=bid.line_items,
    )


def score_bid(
    bid: NormalizedBid,
    cheapest: float,
    weights: dict[str, float],
    risk_band: str,
) -> float:
    """Composite score 0-100 with risk adjustment baked in.

    price component   = weights['price'] * (cheapest / bid_price) * 100
    technical/refs    = full weight if conforming, else 0
    resilience        = (1 - risk_penalty) * weight * 100
    """
    if not bid.is_conforming or bid.normalized_price_per_kg_active == float("inf"):
        return 0.0

    price_score = weights.get("price", 0.5) * (cheapest / bid.normalized_price_per_kg_active) * 100
    technical_score = weights.get("technical", 0.2) * 100
    resilience_score = weights.get("resilience", 0.2) * (1 - RISK_PENALTY.get(risk_band, 0.05)) * 100
    references_score = weights.get("references", 0.1) * 100

    return round(price_score + technical_score + resilience_score + references_score, 2)


def evaluate_bids(
    extracts: list[BidExtract],
    weights: dict[str, float],
    risk_band: str,
    default_concentration: float | None = None,
) -> list[tuple[NormalizedBid, float]]:
    normalized = [normalize_bid(b, default_concentration) for b in extracts]
    conforming_prices = [n.normalized_price_per_kg_active for n in normalized if n.is_conforming]
    cheapest = min(conforming_prices) if conforming_prices else 1.0
    scored = [(n, score_bid(n, cheapest, weights, risk_band)) for n in normalized]
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored


def render_memo_pdf(
    rfp_title: str,
    chemical_name: str,
    facility_name: str,
    risk_band: str,
    weights: dict[str, float],
    scored: list[tuple[NormalizedBid, float]],
    epa_citation: str,
    memo_format: str = "municipal",
) -> bytes:
    """Generate the award-memo PDF. Restrained typography to match the platform aesthetic."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
    )

    base = getSampleStyleSheet()["Normal"]
    base.fontName = "Helvetica"
    h1 = ParagraphStyle("h1", parent=base, fontName="Helvetica-Bold", fontSize=18, leading=22, spaceAfter=10)
    h2 = ParagraphStyle("h2", parent=base, fontName="Helvetica-Bold", fontSize=12, leading=16, spaceBefore=12, spaceAfter=6)
    body = ParagraphStyle("body", parent=base, fontSize=10, leading=14)
    caption = ParagraphStyle("cap", parent=base, fontSize=8, leading=10, textColor=colors.HexColor("#86868B"))

    story = []

    if memo_format == "municipal":
        header = "Memorandum to the Procurement Committee"
        addressee = "From the Office of the Plant Superintendent"
    else:
        header = "Procurement Award Recommendation"
        addressee = "To: Corporate Procurement and ESG Committees"

    story.append(Paragraph(header, h1))
    story.append(Paragraph(addressee, caption))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Subject", h2))
    story.append(Paragraph(f"{rfp_title} — Award Recommendation", body))

    story.append(Paragraph("Background", h2))
    story.append(
        Paragraph(
            f"This memo summarizes the evaluation of bids received for {chemical_name} supply to "
            f"{facility_name}. The chemical's EPA Supply Chain Profile rates the composite supply-chain "
            f"risk as <b>{risk_band}</b>. Evaluation criteria were weighted accordingly: "
            + ", ".join(f"{k.title()} {int(v * 100)}%" for k, v in weights.items())
            + ".",
            body,
        )
    )

    story.append(Paragraph("Bid Evaluation Summary", h2))
    table_data = [["Rank", "Supplier", "$ / kg active", "Conforming", "Composite score"]]
    for i, (n, s) in enumerate(scored, start=1):
        table_data.append(
            [
                str(i),
                n.supplier_name,
                f"${n.normalized_price_per_kg_active:.4f}" if n.is_conforming else "—",
                "Yes" if n.is_conforming else "No",
                f"{s:.1f}",
            ]
        )
    tbl = Table(table_data, hAlign="LEFT", colWidths=[0.5 * inch, 2.5 * inch, 1.2 * inch, 1.0 * inch, 1.2 * inch])
    tbl.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#D2D2D7")),
                ("LINEBELOW", (0, 1), (-1, -2), 0.25, colors.HexColor("#F5F5F7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#86868B")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(tbl)

    if scored:
        winner, winner_score = scored[0]
        story.append(Paragraph("Recommendation", h2))
        rationale = (
            f"Award the contract to <b>{winner.supplier_name}</b> "
            f"at a normalized delivered cost of "
            f"${winner.normalized_price_per_kg_active:.4f} per kg of active ingredient. "
            f"Composite risk-adjusted score: {winner_score:.1f}/100."
        )
        story.append(Paragraph(rationale, body))

    story.append(Paragraph("Risk-Weighting Justification", h2))
    story.append(
        Paragraph(
            f"Resilience criterion weighting was set per the EPA Supply Chain Profile for "
            f"{chemical_name}, which assigns a {risk_band} composite rating. "
            f"The evaluation discount applied to resilience was "
            f"{int(RISK_PENALTY.get(risk_band, 0.05) * 100)}%, scaling per the platform's "
            f"published methodology. Source: {epa_citation}.",
            body,
        )
    )

    story.append(Spacer(1, 24))
    story.append(Paragraph("Generated by Aquaprice. Bidder responses are on file with procurement.", caption))

    doc.build(story)
    return buf.getvalue()
