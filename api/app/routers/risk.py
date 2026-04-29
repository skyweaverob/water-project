"""Risk Monitor API.

GET  /risk/portfolio    portfolio chemicals + current risk scores per facility
GET  /risk/timeseries   daily portfolio risk scores for charting
GET  /risk/alerts       active alerts (severity != info, unacknowledged)
POST /risk/alerts/{id}/ack
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import resolve_tenant
from app.db import get_session
from app.models import (
    Chemical,
    FacilityProfile,
    PortfolioChemical,
    RiskAlert,
    RiskScore,
    Tenant,
)


router = APIRouter(prefix="/risk", tags=["risk"])


class PortfolioRow(BaseModel):
    chemical_id: str
    chemical_name: str
    product_family: str | None
    risk_band: str | None
    primary_import: str | None
    current_supplier: str | None
    annual_demand_kg: float | None


@router.get("/portfolio", response_model=list[PortfolioRow])
async def get_portfolio(
    tenant: Tenant = Depends(resolve_tenant),
    session: AsyncSession = Depends(get_session),
) -> list[PortfolioRow]:
    stmt = (
        select(PortfolioChemical, Chemical, FacilityProfile)
        .join(Chemical, Chemical.id == PortfolioChemical.chemical_id)
        .join(FacilityProfile, FacilityProfile.id == PortfolioChemical.facility_id)
        .where(FacilityProfile.tenant_id == tenant.id)
        .options(
            selectinload(Chemical.risk_assessments),
            selectinload(Chemical.trade_data),
        )
    )
    rows = (await session.execute(stmt)).all()
    out: list[PortfolioRow] = []
    for pc, chem, _fac in rows:
        ra = chem.risk_assessments[0] if chem.risk_assessments else None
        td = chem.trade_data[0] if chem.trade_data else None
        out.append(
            PortfolioRow(
                chemical_id=str(chem.id),
                chemical_name=chem.name,
                product_family=chem.product_family,
                risk_band=ra.composite_rating if ra else None,
                primary_import=td.primary_import_partner if td else None,
                current_supplier=pc.current_supplier,
                annual_demand_kg=pc.annual_demand_kg,
            )
        )
    out.sort(key=lambda r: _band_order(r.risk_band), reverse=True)
    return out


def _band_order(b: str | None) -> int:
    return {"Low": 0, "Moderate-Low": 1, "Moderate": 2, "Moderate-High": 3, "High": 4}.get(b or "", 0)


class TimeseriesPoint(BaseModel):
    score_date: date
    composite_score: float


@router.get("/timeseries", response_model=list[TimeseriesPoint])
async def get_timeseries(
    days: int = 90,
    facility_id: uuid.UUID | None = None,
    tenant: Tenant = Depends(resolve_tenant),
    session: AsyncSession = Depends(get_session),
) -> list[TimeseriesPoint]:
    """Daily timeseries for the chart.

    Returns one point per date. If ``facility_id`` is given, returns that facility's daily
    rollup directly. Otherwise averages across all facilities for the tenant — that's the
    portfolio score the dashboard shows.
    """
    cutoff = date.today() - timedelta(days=days)
    stmt = (
        select(RiskScore.score_date, func.avg(RiskScore.composite_score).label("score"))
        .where(RiskScore.tenant_id == tenant.id)
        .where(RiskScore.score_date >= cutoff)
        .where(RiskScore.chemical_id.is_(None))      # facility-level rollups only
        .where(RiskScore.facility_id.isnot(None))    # exclude tenant-level (facility=null) rows
        .group_by(RiskScore.score_date)
        .order_by(RiskScore.score_date)
    )
    if facility_id is not None:
        stmt = stmt.where(RiskScore.facility_id == facility_id)
    rows = (await session.execute(stmt)).all()
    return [
        TimeseriesPoint(score_date=d, composite_score=float(s) if s is not None else 0.0)
        for d, s in rows
    ]


class AlertOut(BaseModel):
    id: str
    severity: str
    headline: str
    body: str | None
    triggered_at: date
    acknowledged: bool


@router.get("/alerts", response_model=list[AlertOut])
async def list_alerts(
    tenant: Tenant = Depends(resolve_tenant),
    session: AsyncSession = Depends(get_session),
) -> list[AlertOut]:
    stmt = (
        select(RiskAlert)
        .where(RiskAlert.tenant_id == tenant.id)
        .order_by(RiskAlert.triggered_at.desc())
        .limit(50)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        AlertOut(
            id=str(a.id),
            severity=a.severity,
            headline=a.headline,
            body=a.body,
            triggered_at=a.triggered_at,
            acknowledged=a.acknowledged,
        )
        for a in rows
    ]


@router.post("/alerts/{alert_id}/ack")
async def ack_alert(
    alert_id: uuid.UUID,
    tenant: Tenant = Depends(resolve_tenant),
    session: AsyncSession = Depends(get_session),
) -> dict:
    alert = (
        await session.execute(
            select(RiskAlert)
            .where(RiskAlert.id == alert_id)
            .where(RiskAlert.tenant_id == tenant.id)
        )
    ).scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.acknowledged = True
    await session.commit()
    return {"ok": True}
