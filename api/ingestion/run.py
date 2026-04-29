"""Phase 1 ingestion runner.

Iterates every PDF in EPA_CORPUS_DIR, runs the extraction agent, embeds chunks, and persists
to Postgres. Idempotent — chemicals are upserted on `name`, child rows are replaced.

Usage:
    python -m ingestion.run                 # ingest the full corpus
    python -m ingestion.run --only "Aluminum Sulfate"  # ingest a single chemical
    python -m ingestion.run --dry-run       # extract + print, do not persist
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import delete, select

from app.agents.chunker import chunk_sections
from app.agents.embeddings import embed_texts
from app.agents.extraction import ExtractionResult, extract, serialize_for_review
from app.config import get_settings
from app.db import SessionLocal, engine
from app.models import (
    Application,
    Base,
    Chemical,
    DisruptionEvent,
    FactSheetChunk,
    ManufacturingLocation,
    RiskAssessment,
    SubstituteOrPrecursor,
    TradeData,
)

_settings = get_settings()


def _parse_date(year: int | None) -> date | None:
    if not year:
        return None
    try:
        return date(year, 1, 1)
    except Exception:
        return None


def _clean_name(raw: str) -> str:
    """Strip the standard EPA filename suffix and any trailing artifacts."""
    return (
        raw.replace("_0", "")
        .replace("Supply Chain Profile", "")
        .strip(" -_")
    )


async def persist(result: ExtractionResult, pdf_path: Path) -> None:
    fields = result.fields
    name = fields.get("name") or _clean_name(pdf_path.stem)
    avg_conf = (
        sum(result.confidence.values()) / len(result.confidence) if result.confidence else None
    )

    async with SessionLocal() as session:
        existing = (
            await session.execute(select(Chemical).where(Chemical.name == name))
        ).scalar_one_or_none()

        if existing:
            chemical = existing
        else:
            chemical = Chemical(name=name)
            session.add(chemical)

        chemical.cas_number = fields.get("cas_number")
        chemical.molecular_formula = fields.get("molecular_formula")
        chemical.physical_state = fields.get("physical_state")
        chemical.shelf_life_months = fields.get("shelf_life_months")
        chemical.product_family = fields.get("product_family")
        chemical.water_treatment_use = fields.get("water_treatment_use")
        chemical.is_direct_treatment_chemical = bool(fields.get("is_direct_treatment_chemical"))
        chemical.is_precursor = bool(fields.get("is_precursor"))
        chemical.derivative_chemicals = fields.get("derivative_chemicals") or []
        chemical.pct_consumption_water_sector = fields.get("pct_consumption_water_sector")
        chemical.source_pdf = pdf_path.name
        chemical.extraction_confidence = avg_conf

        await session.flush()

        # Replace child collections via bulk DELETE statements (no lazy-load on async session).
        # Includes substitutes_and_precursors, which has no ORM relationship from Chemical.
        for child_model in (
            Application,
            ManufacturingLocation,
            TradeData,
            RiskAssessment,
            DisruptionEvent,
            SubstituteOrPrecursor,
            FactSheetChunk,
        ):
            await session.execute(
                delete(child_model).where(child_model.chemical_id == chemical.id)
            )
        await session.flush()

        for app in result.applications:
            session.add(
                Application(
                    chemical_id=chemical.id,
                    application_type=app.get("application_type", "other"),
                    description=app.get("description", ""),
                )
            )

        for loc in result.manufacturing_locations:
            session.add(
                ManufacturingLocation(
                    chemical_id=chemical.id,
                    country=loc.get("country"),
                    state=loc.get("state"),
                    facility_count=loc.get("facility_count"),
                    year=loc.get("year"),
                    source=loc.get("source"),
                )
            )

        for td in result.trade_data:
            session.add(
                TradeData(
                    chemical_id=chemical.id,
                    year=td["year"],
                    imports_kg=td.get("imports_kg"),
                    exports_kg=td.get("exports_kg"),
                    primary_import_partner=td.get("primary_import_partner"),
                    primary_export_partner=td.get("primary_export_partner"),
                    hts_code=td.get("hts_code"),
                    general_duty_pct=td.get("general_duty_pct"),
                    china_section_301_duty_pct=td.get("china_section_301_duty_pct"),
                    special_duty_countries=td.get("special_duty_countries") or [],
                )
            )

        ra = result.risk_assessment or {}
        if ra:
            session.add(
                RiskAssessment(
                    chemical_id=chemical.id,
                    assessment_date=_parse_date(ra.get("assessment_year")),
                    criticality=ra.get("criticality"),
                    likelihood=ra.get("likelihood"),
                    vulnerability=ra.get("vulnerability"),
                    composite_rating=ra.get("composite_rating"),
                    criticality_drivers=ra.get("criticality_drivers"),
                    likelihood_drivers=ra.get("likelihood_drivers"),
                    vulnerability_drivers=ra.get("vulnerability_drivers"),
                )
            )

        for ev in result.disruption_events:
            session.add(
                DisruptionEvent(
                    chemical_id=chemical.id,
                    event_date=_parse_date(ev.get("event_year")),
                    event_type=ev.get("event_type"),
                    description=ev.get("description", ""),
                    source_citation=ev.get("source_citation"),
                )
            )

        for sp in result.substitutes_and_precursors:
            session.add(
                SubstituteOrPrecursor(
                    chemical_id=chemical.id,
                    related_chemical_name=sp.get("related_chemical_name"),
                    relationship_type=sp.get("relationship_type", "precursor"),
                    notes=sp.get("notes"),
                )
            )

        chunks = chunk_sections(result.sections)
        if chunks:
            embeddings = await embed_texts([c.text for c in chunks], input_type="document")
            for c, vec in zip(chunks, embeddings, strict=True):
                session.add(
                    FactSheetChunk(
                        chemical_id=chemical.id,
                        page_num=c.page_num,
                        section=c.section,
                        text=c.text,
                        embedding=vec,
                    )
                )

        await session.commit()


async def ingest_pdf(pdf_path: Path, dry_run: bool) -> None:
    print(f"\n=== {pdf_path.name} ===", flush=True)
    result = await extract(pdf_path)
    review = serialize_for_review(result)
    print(review[:1500] + ("..." if len(review) > 1500 else ""))
    if dry_run:
        return
    await persist(result, pdf_path)
    print(f"  ✓ persisted (chunks: {len(result.sections)}, conf: {result.confidence})")


async def bootstrap_schema() -> None:
    async with engine.begin() as conn:
        await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        await conn.run_sync(Base.metadata.create_all)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Substring to match a single PDF filename")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--bootstrap", action="store_true", help="Create tables before ingesting")
    args = parser.parse_args()

    if args.bootstrap and not args.dry_run:
        await bootstrap_schema()

    corpus_dir = Path(_settings.epa_corpus_dir).resolve()
    if not corpus_dir.exists():
        print(f"Corpus directory not found: {corpus_dir}", file=sys.stderr)
        sys.exit(1)

    pdfs = sorted(corpus_dir.glob("*.pdf"))
    if args.only:
        needle = args.only.lower()
        pdfs = [p for p in pdfs if needle in p.name.lower()]
    if not pdfs:
        print("No PDFs matched.", file=sys.stderr)
        sys.exit(1)

    print(f"Ingesting {len(pdfs)} PDF(s) from {corpus_dir}")
    for pdf in pdfs:
        try:
            await ingest_pdf(pdf, args.dry_run)
        except Exception as exc:  # noqa: BLE001 — keep batch going
            print(f"  ✗ FAILED: {pdf.name}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
