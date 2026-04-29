from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.bid_extraction import extract_bid, parse_bid_pdf
from app.agents.price_discovery import discover_price
from app.auth import resolve_tenant
from app.db import get_session
from app.models import Bid, BidLineItem, Chemical, FacilityProfile, Rfp, Tenant
from app.services.bid_evaluator import BidExtract, BidLine, evaluate_bids, render_memo_pdf


router = APIRouter(prefix="/bids", tags=["bids"])


class BidLineItemIn(BaseModel):
    description: str
    unit: str
    unit_price: float
    delivered_concentration_pct: float | None = None
    freight_terms: str | None = None


class BidIn(BaseModel):
    rfp_id: str
    supplier_name: str
    supplier_contact_email: str | None = None
    line_items: list[BidLineItemIn]


class BidOut(BaseModel):
    id: str
    supplier_name: str
    is_conforming: bool
    normalized_price_per_kg_active: float | None
    risk_adjusted_score: float | None
    is_recommended: bool


@router.post("", response_model=BidOut)
async def create_bid(
    payload: BidIn,
    tenant: Tenant = Depends(resolve_tenant),
    session: AsyncSession = Depends(get_session),
) -> BidOut:
    rfp = await session.get(Rfp, uuid.UUID(payload.rfp_id))
    if not rfp or rfp.tenant_id != tenant.id:
        raise HTTPException(404, "RFP not found")

    bid = Bid(
        rfp_id=rfp.id,
        supplier_name=payload.supplier_name,
        supplier_contact_email=payload.supplier_contact_email,
    )
    session.add(bid)
    await session.flush()

    for li in payload.line_items:
        session.add(
            BidLineItem(
                bid_id=bid.id,
                description=li.description,
                unit=li.unit,
                unit_price=li.unit_price,
                delivered_concentration_pct=li.delivered_concentration_pct,
                freight_terms=li.freight_terms,
            )
        )

    await session.commit()
    await session.refresh(bid)
    return BidOut(
        id=str(bid.id),
        supplier_name=bid.supplier_name,
        is_conforming=bid.is_conforming,
        normalized_price_per_kg_active=None,
        risk_adjusted_score=None,
        is_recommended=False,
    )


@router.post("/upload", response_model=BidOut)
async def upload_bid(
    rfp_id: str = Form(...),
    file: UploadFile = File(...),
    tenant: Tenant = Depends(resolve_tenant),
    session: AsyncSession = Depends(get_session),
) -> BidOut:
    rfp = await session.get(Rfp, uuid.UUID(rfp_id))
    if not rfp or rfp.tenant_id != tenant.id:
        raise HTTPException(404, "RFP not found")

    contents = await file.read()
    fd, raw_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    tmp_path = Path(raw_path)
    tmp_path.write_bytes(contents)
    filename = file.filename or ""
    try:
        if file.content_type == "application/pdf" or filename.lower().endswith(".pdf"):
            text = parse_bid_pdf(tmp_path)
        else:
            text = contents.decode("utf-8", errors="ignore")
        payload = await extract_bid(text)
    finally:
        tmp_path.unlink(missing_ok=True)

    bid = Bid(rfp_id=rfp.id, supplier_name=payload["supplier_name"])
    session.add(bid)
    await session.flush()
    for li in payload.get("line_items", []):
        session.add(
            BidLineItem(
                bid_id=bid.id,
                description=li["description"],
                unit=li["unit"],
                unit_price=li["unit_price"],
                delivered_concentration_pct=li.get("delivered_concentration_pct"),
                freight_terms=payload.get("freight_terms"),
            )
        )
    await session.commit()
    await session.refresh(bid)

    return BidOut(
        id=str(bid.id),
        supplier_name=bid.supplier_name,
        is_conforming=True,
        normalized_price_per_kg_active=None,
        risk_adjusted_score=None,
        is_recommended=False,
    )


@router.get("/by-rfp/{rfp_id}", response_model=list[BidOut])
async def list_bids_for_rfp(
    rfp_id: uuid.UUID,
    tenant: Tenant = Depends(resolve_tenant),
    session: AsyncSession = Depends(get_session),
) -> list[BidOut]:
    rfp = await session.get(Rfp, rfp_id)
    if not rfp or rfp.tenant_id != tenant.id:
        raise HTTPException(404, "RFP not found")
    bids = (
        await session.execute(
            select(Bid).where(Bid.rfp_id == rfp.id).options(selectinload(Bid.line_items))
        )
    ).scalars().all()

    return [
        BidOut(
            id=str(b.id),
            supplier_name=b.supplier_name,
            is_conforming=b.is_conforming,
            normalized_price_per_kg_active=b.normalized_price_per_kg_active,
            risk_adjusted_score=b.risk_adjusted_score,
            is_recommended=b.is_recommended,
        )
        for b in bids
    ]


@router.post("/by-rfp/{rfp_id}/evaluate", response_model=list[BidOut])
async def evaluate_rfp_bids(
    rfp_id: uuid.UUID,
    tenant: Tenant = Depends(resolve_tenant),
    session: AsyncSession = Depends(get_session),
) -> list[BidOut]:
    rfp = (
        await session.execute(
            select(Rfp).where(Rfp.id == rfp_id).where(Rfp.tenant_id == tenant.id)
        )
    ).scalar_one_or_none()
    if not rfp:
        raise HTTPException(404, "RFP not found")

    chem = (
        await session.execute(
            select(Chemical)
            .where(Chemical.id == rfp.chemical_id)
            .options(selectinload(Chemical.risk_assessments))
        )
    ).scalar_one()
    risk_band = chem.risk_assessments[0].composite_rating if chem.risk_assessments else "Low"

    bids = (
        await session.execute(
            select(Bid).where(Bid.rfp_id == rfp.id).options(selectinload(Bid.line_items))
        )
    ).scalars().all()

    extracts = [
        BidExtract(
            supplier_name=b.supplier_name,
            line_items=[
                BidLine(
                    description=li.description,
                    unit=li.unit,
                    unit_price=li.unit_price,
                    delivered_concentration_pct=li.delivered_concentration_pct,
                )
                for li in b.line_items
            ],
        )
        for b in bids
    ]

    weights = rfp.evaluation_weights or {"price": 0.5, "technical": 0.2, "resilience": 0.2, "references": 0.1}
    scored = evaluate_bids(extracts, weights, risk_band, default_concentration=rfp.spec_concentration_pct)

    # Persist normalized prices and ranks
    by_name = {b.supplier_name: b for b in bids}
    # Only mark a recommendation when the top bid is actually conforming (score > 0).
    best_supplier = scored[0][0].supplier_name if scored and scored[0][1] > 0 else None
    for normalized, score in scored:
        bid = by_name.get(normalized.supplier_name)
        if not bid:
            continue
        bid.normalized_price_per_kg_active = (
            normalized.normalized_price_per_kg_active
            if normalized.is_conforming
            else None
        )
        bid.is_conforming = normalized.is_conforming
        bid.nonconformance_notes = "\n".join(normalized.nonconformance_notes) or None
        bid.risk_adjusted_score = score
        bid.is_recommended = bid.supplier_name == best_supplier
    await session.commit()

    return [
        BidOut(
            id=str(b.id),
            supplier_name=b.supplier_name,
            is_conforming=b.is_conforming,
            normalized_price_per_kg_active=b.normalized_price_per_kg_active,
            risk_adjusted_score=b.risk_adjusted_score,
            is_recommended=b.is_recommended,
        )
        for b in bids
    ]


class MarketBenchmarkOut(BaseModel):
    chemical: str
    median_usd_per_kg_active: float
    sample_size: int


@router.get("/by-rfp/{rfp_id}/market-benchmark", response_model=MarketBenchmarkOut)
async def market_benchmark(
    rfp_id: uuid.UUID,
    tenant: Tenant = Depends(resolve_tenant),
    session: AsyncSession = Depends(get_session),
) -> MarketBenchmarkOut:
    """Live web-search-driven price benchmark for the RFP's chemical. The Bid Evaluator UI
    renders this as a column next to each supplier's normalized price so the buyer
    immediately sees who is above / below market."""
    rfp = await session.get(Rfp, rfp_id)
    if not rfp or rfp.tenant_id != tenant.id:
        raise HTTPException(404, "RFP not found")
    chem = await session.get(Chemical, rfp.chemical_id)
    if not chem:
        raise HTTPException(404, "Chemical not found")
    benchmark = await discover_price(chem.name, cas_number=chem.cas_number)
    return MarketBenchmarkOut(
        chemical=chem.name,
        median_usd_per_kg_active=benchmark.median_usd_per_kg,
        sample_size=benchmark.sample_size,
    )


@router.get("/by-rfp/{rfp_id}/memo")
async def generate_memo(
    rfp_id: uuid.UUID,
    tenant: Tenant = Depends(resolve_tenant),
    session: AsyncSession = Depends(get_session),
) -> Response:
    rfp = (
        await session.execute(
            select(Rfp)
            .where(Rfp.id == rfp_id)
            .where(Rfp.tenant_id == tenant.id)
            .options(selectinload(Rfp.bids).selectinload(Bid.line_items))
        )
    ).scalar_one_or_none()
    if not rfp:
        raise HTTPException(404, "RFP not found")

    chem = (
        await session.execute(
            select(Chemical)
            .where(Chemical.id == rfp.chemical_id)
            .options(selectinload(Chemical.risk_assessments))
        )
    ).scalar_one_or_none()
    if not chem:
        raise HTTPException(404, "Chemical not found")
    risk_band = chem.risk_assessments[0].composite_rating if chem.risk_assessments else "Low"

    extracts = [
        BidExtract(
            supplier_name=b.supplier_name,
            line_items=[
                BidLine(
                    description=li.description,
                    unit=li.unit,
                    unit_price=li.unit_price,
                    delivered_concentration_pct=li.delivered_concentration_pct,
                )
                for li in b.line_items
            ],
        )
        for b in rfp.bids
    ]
    weights = rfp.evaluation_weights or {"price": 0.5, "technical": 0.2, "resilience": 0.2, "references": 0.1}
    scored = evaluate_bids(extracts, weights, risk_band, default_concentration=rfp.spec_concentration_pct)

    fac = await session.get(FacilityProfile, rfp.facility_id)
    citation = (
        f"EPA Water Treatment Chemical Supply Chain Profile — {chem.name} (December 2022, EPA 817-F-22)."
    )
    pdf = render_memo_pdf(
        rfp_title=rfp.title,
        chemical_name=chem.name,
        facility_name=fac.name if fac else "",
        risk_band=risk_band,
        weights=weights,
        scored=scored,
        epa_citation=citation,
        memo_format="municipal" if tenant.vertical == "municipal" else "corporate",
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{rfp.title} — Award Memo.pdf"'},
    )
