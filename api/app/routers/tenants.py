from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import FacilityProfile, Tenant


router = APIRouter(prefix="/tenants", tags=["tenants"])


class TenantCreate(BaseModel):
    name: str
    vertical: str = "municipal"
    plan: str = "single_facility"


class TenantOut(BaseModel):
    id: str
    name: str
    vertical: str
    plan: str

    class Config:
        from_attributes = True


@router.post("", response_model=TenantOut)
async def create_tenant(payload: TenantCreate, session: AsyncSession = Depends(get_session)) -> TenantOut:
    if payload.vertical not in ("municipal", "industrial"):
        raise HTTPException(400, "vertical must be municipal or industrial")
    tenant = Tenant(name=payload.name, vertical=payload.vertical, plan=payload.plan)
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return TenantOut(id=str(tenant.id), name=tenant.name, vertical=tenant.vertical, plan=tenant.plan)


@router.get("", response_model=list[TenantOut])
async def list_tenants(session: AsyncSession = Depends(get_session)) -> list[TenantOut]:
    rows = (await session.execute(select(Tenant).order_by(Tenant.created_at.desc()))).scalars().all()
    return [TenantOut(id=str(t.id), name=t.name, vertical=t.vertical, plan=t.plan) for t in rows]
