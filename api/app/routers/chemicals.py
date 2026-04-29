import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models import Chemical

router = APIRouter(prefix="/chemicals", tags=["chemicals"])


class ChemicalSummary(BaseModel):
    id: str
    name: str
    cas_number: str | None
    product_family: str | None
    risk_rating: str | None
    is_direct_treatment_chemical: bool
    pct_consumption_water_sector: float | None


class ChemicalDetail(ChemicalSummary):
    molecular_formula: str | None
    physical_state: str | None
    shelf_life_months: int | None
    water_treatment_use: str | None
    derivative_chemicals: list[str] | None
    extraction_confidence: float | None
    criticality: str | None
    likelihood: str | None
    vulnerability: str | None


@router.get("", response_model=list[ChemicalSummary])
async def list_chemicals(session: AsyncSession = Depends(get_session)) -> list[ChemicalSummary]:
    stmt = select(Chemical).options(selectinload(Chemical.risk_assessments)).order_by(Chemical.name)
    rows = (await session.execute(stmt)).scalars().all()
    return [_to_summary(c) for c in rows]


@router.get("/{chemical_id}", response_model=ChemicalDetail)
async def get_chemical(
    chemical_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> ChemicalDetail:
    stmt = (
        select(Chemical)
        .where(Chemical.id == chemical_id)
        .options(selectinload(Chemical.risk_assessments))
    )
    c = (await session.execute(stmt)).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Chemical not found")
    ra = c.risk_assessments[0] if c.risk_assessments else None
    return ChemicalDetail(
        id=str(c.id),
        name=c.name,
        cas_number=c.cas_number,
        product_family=c.product_family,
        risk_rating=ra.composite_rating if ra else None,
        is_direct_treatment_chemical=c.is_direct_treatment_chemical,
        pct_consumption_water_sector=c.pct_consumption_water_sector,
        molecular_formula=c.molecular_formula,
        physical_state=c.physical_state,
        shelf_life_months=c.shelf_life_months,
        water_treatment_use=c.water_treatment_use,
        derivative_chemicals=c.derivative_chemicals,
        extraction_confidence=c.extraction_confidence,
        criticality=ra.criticality if ra else None,
        likelihood=ra.likelihood if ra else None,
        vulnerability=ra.vulnerability if ra else None,
    )


def _to_summary(c: Chemical) -> ChemicalSummary:
    ra = c.risk_assessments[0] if c.risk_assessments else None
    return ChemicalSummary(
        id=str(c.id),
        name=c.name,
        cas_number=c.cas_number,
        product_family=c.product_family,
        risk_rating=ra.composite_rating if ra else None,
        is_direct_treatment_chemical=c.is_direct_treatment_chemical,
        pct_consumption_water_sector=c.pct_consumption_water_sector,
    )
