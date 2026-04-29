from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import resolve_tenant
from app.db import get_session
from app.models import Chemical, FacilityProfile, Rfp, Tenant
from app.services.rfp_builder import RfpInputs, build_draft, render_docx


router = APIRouter(prefix="/rfps", tags=["rfps"])


class FacilityCreate(BaseModel):
    name: str
    sector: str  # drinking_water | wastewater | industrial_pretreatment
    flow_mgd: float | None = None
    treatment_processes: list[str] | None = None
    location_state: str | None = None
    location_city: str | None = None


class FacilityOut(FacilityCreate):
    id: str


class RfpCreate(BaseModel):
    facility_id: str
    chemical_id: str
    quantity_kg_annual: float
    contract_term_months: int = 24
    delivery_window_days: int = 14
    bid_due_in_days: int = 28


class RfpOut(BaseModel):
    id: str
    title: str
    status: str
    chemical_name: str
    facility_name: str
    quantity_kg_annual: float | None
    bid_due_date: date | None
    evaluation_weights: dict | None
    resilience_clauses: list | None


@router.post("/facilities", response_model=FacilityOut)
async def create_facility(
    payload: FacilityCreate,
    tenant: Tenant = Depends(resolve_tenant),
    session: AsyncSession = Depends(get_session),
) -> FacilityOut:
    fac = FacilityProfile(
        tenant_id=tenant.id,
        name=payload.name,
        sector=payload.sector,
        flow_mgd=payload.flow_mgd,
        treatment_processes=payload.treatment_processes,
        location_state=payload.location_state,
        location_city=payload.location_city,
    )
    session.add(fac)
    await session.commit()
    await session.refresh(fac)
    return FacilityOut(id=str(fac.id), **payload.model_dump())


@router.get("/facilities", response_model=list[FacilityOut])
async def list_facilities(
    tenant: Tenant = Depends(resolve_tenant),
    session: AsyncSession = Depends(get_session),
) -> list[FacilityOut]:
    rows = (
        await session.execute(select(FacilityProfile).where(FacilityProfile.tenant_id == tenant.id))
    ).scalars().all()
    return [
        FacilityOut(
            id=str(r.id),
            name=r.name,
            sector=r.sector,
            flow_mgd=r.flow_mgd,
            treatment_processes=r.treatment_processes,
            location_state=r.location_state,
            location_city=r.location_city,
        )
        for r in rows
    ]


@router.post("", response_model=RfpOut)
async def create_rfp(
    payload: RfpCreate,
    tenant: Tenant = Depends(resolve_tenant),
    session: AsyncSession = Depends(get_session),
) -> RfpOut:
    try:
        fac_uuid = uuid.UUID(payload.facility_id)
        chem_uuid = uuid.UUID(payload.chemical_id)
    except ValueError:
        raise HTTPException(400, "facility_id and chemical_id must be valid UUIDs")

    fac = await session.get(FacilityProfile, fac_uuid)
    if not fac or fac.tenant_id != tenant.id:
        raise HTTPException(404, "Facility not found")
    chem = (
        await session.execute(
            select(Chemical)
            .where(Chemical.id == chem_uuid)
            .options(selectinload(Chemical.risk_assessments))
        )
    ).scalar_one_or_none()
    if not chem:
        raise HTTPException(404, "Chemical not found")

    risk_rating = chem.risk_assessments[0].composite_rating if chem.risk_assessments else None

    inputs = RfpInputs(
        facility=fac,
        chemical=chem,
        annual_demand_kg=payload.quantity_kg_annual,
        contract_term_months=payload.contract_term_months,
        delivery_window_days=payload.delivery_window_days,
        vertical=tenant.vertical,
    )
    draft = build_draft(inputs, risk_rating)

    rfp = Rfp(
        tenant_id=tenant.id,
        facility_id=fac.id,
        chemical_id=chem.id,
        title=draft.title,
        status="draft",
        quantity_kg_annual=payload.quantity_kg_annual,
        contract_term_months=payload.contract_term_months,
        delivery_window_days=payload.delivery_window_days,
        spec_purity_standard="NSF/ANSI 60" if fac.sector == "drinking_water" else None,
        resilience_clauses={"clauses": draft.resilience_clauses},
        evaluation_weights=draft.evaluation_weights,
        boilerplate_terms="\n\n".join(draft.boilerplate_terms),
        bid_due_date=date.today() + timedelta(days=payload.bid_due_in_days),
    )
    session.add(rfp)
    await session.commit()
    await session.refresh(rfp)

    return RfpOut(
        id=str(rfp.id),
        title=rfp.title,
        status=rfp.status,
        chemical_name=chem.name,
        facility_name=fac.name,
        quantity_kg_annual=rfp.quantity_kg_annual,
        bid_due_date=rfp.bid_due_date,
        evaluation_weights=rfp.evaluation_weights,
        resilience_clauses=draft.resilience_clauses,
    )


@router.get("/{rfp_id}/document")
async def download_docx(
    rfp_id: uuid.UUID,
    tenant: Tenant = Depends(resolve_tenant),
    session: AsyncSession = Depends(get_session),
) -> Response:
    rfp = (
        await session.execute(
            select(Rfp).where(Rfp.id == rfp_id).where(Rfp.tenant_id == tenant.id)
        )
    ).scalar_one_or_none()
    if not rfp:
        raise HTTPException(404, "RFP not found")

    fac = await session.get(FacilityProfile, rfp.facility_id)
    chem = (
        await session.execute(
            select(Chemical)
            .where(Chemical.id == rfp.chemical_id)
            .options(selectinload(Chemical.risk_assessments))
        )
    ).scalar_one_or_none()
    if not fac or not chem:
        raise HTTPException(404, "Facility or chemical not found")
    risk_rating = chem.risk_assessments[0].composite_rating if chem.risk_assessments else None

    inputs = RfpInputs(
        facility=fac,
        chemical=chem,
        annual_demand_kg=rfp.quantity_kg_annual or 0,
        contract_term_months=rfp.contract_term_months or 24,
        delivery_window_days=rfp.delivery_window_days or 14,
        vertical=tenant.vertical,
    )
    draft = build_draft(inputs, risk_rating)
    blob = render_docx(draft, inputs)
    return Response(
        content=blob,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{rfp.title}.docx"'},
    )


@router.get("", response_model=list[RfpOut])
async def list_rfps(
    tenant: Tenant = Depends(resolve_tenant),
    session: AsyncSession = Depends(get_session),
) -> list[RfpOut]:
    stmt = select(Rfp).where(Rfp.tenant_id == tenant.id).order_by(Rfp.created_at.desc())
    rfps = (await session.execute(stmt)).scalars().all()

    out: list[RfpOut] = []
    for rfp in rfps:
        chem = await session.get(Chemical, rfp.chemical_id)
        fac = await session.get(FacilityProfile, rfp.facility_id)
        out.append(
            RfpOut(
                id=str(rfp.id),
                title=rfp.title,
                status=rfp.status,
                chemical_name=chem.name if chem else "",
                facility_name=fac.name if fac else "",
                quantity_kg_annual=rfp.quantity_kg_annual,
                bid_due_date=rfp.bid_due_date,
                evaluation_weights=rfp.evaluation_weights,
                resilience_clauses=(rfp.resilience_clauses or {}).get("clauses"),
            )
        )
    return out
