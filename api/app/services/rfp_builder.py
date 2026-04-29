"""RFP Builder.

Given a facility profile, a target chemical, and contract parameters, generate:
- Technical specs (concentration, NSF/ANSI 60, AWWA standard reference)
- Resilience clauses scaled to the chemical's EPA risk rating
- Evaluation criteria with weights tuned to risk profile
- Boilerplate procurement terms (municipal vs. industrial vertical)
- A DOCX file the user can hand to legal/procurement

Uses chemical_priors.json as the static prior; the live ingestion data overrides where available.
"""
from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document
from docx.shared import Pt

from app.models import Chemical, FacilityProfile

PRIORS_PATH = Path(__file__).parent.parent / "intelligence" / "chemical_priors.json"


def _load_priors() -> dict[str, dict]:
    raw = json.loads(PRIORS_PATH.read_text(encoding="utf-8"))
    return {c["name"].lower(): c for c in raw["chemicals"]}


_PRIORS = _load_priors()


@dataclass
class RfpInputs:
    facility: FacilityProfile
    chemical: Chemical
    annual_demand_kg: float
    contract_term_months: int = 24
    delivery_window_days: int = 14
    vertical: str = "municipal"


@dataclass
class RfpDraft:
    title: str
    technical_specs: list[str] = field(default_factory=list)
    resilience_clauses: list[str] = field(default_factory=list)
    evaluation_weights: dict[str, float] = field(default_factory=dict)
    boilerplate_terms: list[str] = field(default_factory=list)
    suggested_timeline: list[tuple[str, int]] = field(default_factory=list)
    supplier_shortlist_note: str = ""


# Risk band → resilience scaling
RESILIENCE_BY_BAND: dict[str, list[str]] = {
    "Low": [
        "Supplier shall provide a 30-day notice of any planned production downtime.",
    ],
    "Moderate-Low": [
        "Supplier shall maintain a minimum 14-day inventory buffer at the delivery point.",
        "Supplier shall disclose primary and backup manufacturing locations.",
    ],
    "Moderate": [
        "Supplier shall maintain a minimum 21-day inventory buffer at the delivery point.",
        "Force majeure clause shall require alternate-source allocation within 7 calendar days.",
        "Supplier shall disclose primary and backup manufacturing locations and primary feedstock origin.",
    ],
    "Moderate-High": [
        "Supplier shall maintain a minimum 30-day inventory buffer at the delivery point.",
        "Force majeure clause shall require alternate-source allocation within 5 calendar days.",
        "Supplier shall disclose primary, backup, and tertiary manufacturing locations and primary feedstock origin.",
        "Contract shall require quarterly written attestation of upstream-feedstock supply continuity.",
        "Buyer reserves right to audit supplier inventory and shipment records monthly.",
    ],
    "High": [
        "Supplier shall maintain a minimum 45-day inventory buffer at the delivery point.",
        "Force majeure clause shall require alternate-source allocation within 3 calendar days.",
        "Supplier shall disclose primary, backup, and tertiary manufacturing locations and primary feedstock origin.",
        "Contract shall require monthly written attestation of upstream-feedstock supply continuity.",
        "Buyer reserves right to audit supplier inventory and shipment records monthly.",
        "Buyer shall have right of first refusal on any allocation event.",
    ],
}


# Evaluation weights tuned by risk band — higher risk → more weight on resilience and references
WEIGHTS_BY_BAND: dict[str, dict[str, float]] = {
    "Low":            {"price": 0.60, "technical": 0.20, "resilience": 0.10, "references": 0.10},
    "Moderate-Low":   {"price": 0.50, "technical": 0.20, "resilience": 0.20, "references": 0.10},
    "Moderate":       {"price": 0.45, "technical": 0.20, "resilience": 0.25, "references": 0.10},
    "Moderate-High":  {"price": 0.35, "technical": 0.20, "resilience": 0.30, "references": 0.15},
    "High":           {"price": 0.30, "technical": 0.20, "resilience": 0.35, "references": 0.15},
}


# Map chemical → AWWA standard, where known. Pulled from the corpus reference.
AWWA_STANDARD: dict[str, str] = {
    "Aluminum Sulfate": "AWWA B403 — Liquid, Ground, or Lump Aluminum Sulfate",
    "Polyaluminum Chloride": "AWWA B408 — Polyaluminum Chloride",
    "Ferric Chloride": "AWWA B407 — Liquid Ferric Chloride",
    "Ferric Sulfate": "AWWA B406 — Ferric Sulfate",
    "Ferrous Sulfate": "AWWA B402 — Ferrous Sulfate",
    "Sodium Hypochlorite": "AWWA B300 — Hypochlorites",
    "Calcium Hypochlorite": "AWWA B300 — Hypochlorites",
    "Chlorine": "AWWA B301 — Liquid Chlorine",
    "Sodium Chlorite": "AWWA B303 — Sodium Chlorite",
    "Sodium Hydroxide": "AWWA B501 — Sodium Hydroxide",
    "Potassium Hydroxide": "AWWA B511 — Potassium Hydroxide",
    "Sodium Carbonate": "AWWA B201 — Soda Ash",
    "Sodium Chloride": "AWWA B200 — Sodium Chloride",
    "Phosphoric Acid": "AWWA B507 — Phosphoric Acid",
    "Disodium Phosphate": "AWWA B504 — Mono- and Disodium Phosphate",
    "Monosodium Phosphate": "AWWA B504 — Mono- and Disodium Phosphate",
    "Sodium Salts of Polyphosphate": "AWWA B502 / B503 — Sodium Polyphosphates",
    "Zinc Orthophosphate": "AWWA B506 — Zinc Orthophosphate",
    "Sulfur Dioxide": "AWWA B512 — Sulfur Dioxide",
    "Carbon Dioxide": "AWWA B510 — Carbon Dioxide",
    "Oxygen": "AWWA B304 — Liquid Oxygen",
    "Anhydrous Ammonia": "AWWA B305 — Anhydrous Ammonia",
    "Ammonium Hydroxide": "AWWA B306 — Aqua Ammonia",
    "Potassium Permanganate": "AWWA B603 — Potassium Permanganate",
    "Fluorosilicic Acid": "AWWA B703 — Fluorosilicic Acid",
    "Sodium Silicate": "AWWA B303 — Sodium Silicate",
}


def build_draft(inputs: RfpInputs, risk_rating: str | None) -> RfpDraft:
    band = (risk_rating or "Low").strip()
    if band not in RESILIENCE_BY_BAND:
        band = "Low"

    chem = inputs.chemical
    fac = inputs.facility
    prior = _PRIORS.get(chem.name.lower(), {})

    title = f"{chem.name} Supply Contract — {fac.name}"

    specs: list[str] = []
    awwa = AWWA_STANDARD.get(chem.name)
    if awwa:
        specs.append(f"Product shall conform to {awwa}.")
    if prior.get("nsf60_count"):
        specs.append("Supplier shall be certified to NSF/ANSI Standard 60 for drinking water treatment.")
    elif fac.sector == "drinking_water":
        specs.append("Supplier shall be certified to NSF/ANSI Standard 60 for drinking water treatment.")
    if chem.physical_state:
        specs.append(f"Product shall be supplied as {chem.physical_state}.")
    if chem.shelf_life_months:
        specs.append(
            f"Product shall have a minimum guaranteed shelf life of {chem.shelf_life_months} months from delivery."
        )
    specs.append("Each delivery shall be accompanied by a Certificate of Analysis stating concentration of active ingredient and impurity profile.")

    boilerplate_municipal = [
        "Buyer is a public agency. Award is contingent upon governing-body approval.",
        "Supplier shall comply with all applicable provisions of buyer's procurement code, including local-preference and small-business participation requirements where applicable.",
        "Public records: bid responses are subject to disclosure under applicable state public records law except for items properly designated as trade secret.",
        "Insurance: $2,000,000 commercial general liability, $1,000,000 auto, statutory workers' compensation.",
    ]
    boilerplate_industrial = [
        "Supplier shall comply with buyer's supplier code of conduct including ESG reporting requirements.",
        "Supplier shall provide annual GHG-emissions disclosure for delivered product.",
        "Indemnification: supplier shall indemnify buyer for any product non-conformance and any environmental release attributable to delivered product.",
        "Insurance: $5,000,000 commercial general liability, $2,000,000 auto, statutory workers' compensation, $1,000,000 environmental impairment liability.",
    ]
    boilerplate = boilerplate_municipal if inputs.vertical == "municipal" else boilerplate_industrial

    timeline = [
        ("RFP issued", 0),
        ("Mandatory questions due", 7),
        ("Buyer responses posted", 14),
        ("Bids due", 28),
        ("Bid evaluation complete", 42),
        ("Award notice", 49),
        ("Contract execution", 63),
    ]

    nsf_count = prior.get("nsf60_count")
    if nsf_count:
        shortlist_note = (
            f"NSF/ANSI Standard 60 currently lists {nsf_count} certified suppliers for {chem.name}. "
            "We recommend inviting at least 5 to bid; for risk ratings of Moderate-Low or higher, invite 7-10."
        )
    else:
        shortlist_note = "Use the EPA Chemical Suppliers and Manufacturers Locator Tool to identify candidates within freight range."

    return RfpDraft(
        title=title,
        technical_specs=specs,
        resilience_clauses=RESILIENCE_BY_BAND[band],
        evaluation_weights=WEIGHTS_BY_BAND[band],
        boilerplate_terms=boilerplate,
        suggested_timeline=timeline,
        supplier_shortlist_note=shortlist_note,
    )


def render_docx(draft: RfpDraft, inputs: RfpInputs) -> bytes:
    doc = Document()
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)

    doc.add_heading(draft.title, level=0)

    doc.add_heading("1. Scope of Solicitation", level=1)
    p = doc.add_paragraph()
    p.add_run(
        f"{inputs.facility.name} (the \"Buyer\") seeks bids for the supply of "
        f"{inputs.chemical.name} (CAS {inputs.chemical.cas_number or 'see specification'}). "
        f"Estimated annual demand: {inputs.annual_demand_kg:,.0f} kg. Contract term: "
        f"{inputs.contract_term_months} months. Delivery window: {inputs.delivery_window_days} days from order."
    )

    doc.add_heading("2. Technical Specifications", level=1)
    for spec in draft.technical_specs:
        doc.add_paragraph(spec, style="List Bullet")

    doc.add_heading("3. Supply Resilience Requirements", level=1)
    for clause in draft.resilience_clauses:
        doc.add_paragraph(clause, style="List Bullet")

    doc.add_heading("4. Evaluation Criteria", level=1)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Light Grid"
    hdr = table.rows[0].cells
    hdr[0].text = "Criterion"
    hdr[1].text = "Weight"
    for k, v in draft.evaluation_weights.items():
        row = table.add_row().cells
        row[0].text = k.title()
        row[1].text = f"{int(v * 100)}%"

    doc.add_heading("5. General Terms", level=1)
    for t in draft.boilerplate_terms:
        doc.add_paragraph(t, style="List Bullet")

    doc.add_heading("6. Suggested Timeline", level=1)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Light Grid"
    hdr = table.rows[0].cells
    hdr[0].text = "Milestone"
    hdr[1].text = "Day"
    for label, day in draft.suggested_timeline:
        row = table.add_row().cells
        row[0].text = label
        row[1].text = f"Day {day}"

    doc.add_heading("7. Supplier Shortlist Note", level=1)
    doc.add_paragraph(draft.supplier_shortlist_note)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
