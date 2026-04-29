"""Lightweight tenant resolution.

Production deployments should swap this for a real Clerk JWT verifier. For now we trust an
`X-Tenant-Id` header in development. When the header is missing AND there is exactly one
tenant in the database, we resolve to that tenant — this makes the demo flow work without
requiring `NEXT_PUBLIC_DEMO_TENANT_ID` to be set on the web service.
"""
from __future__ import annotations

import uuid
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Tenant


async def resolve_tenant(
    x_tenant_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> Tenant:
    if not x_tenant_id:
        # Demo fallback: if the database holds exactly one tenant, use it. Multi-tenant
        # deployments must set X-Tenant-Id (via Clerk JWT in production).
        rows = (await session.execute(select(Tenant).limit(2))).scalars().all()
        if len(rows) == 1:
            return rows[0]
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Tenant-Id. Set NEXT_PUBLIC_DEMO_TENANT_ID or pass the header explicitly.",
        )
    try:
        tenant_uuid = uuid.UUID(x_tenant_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid tenant id") from exc
    tenant = (await session.execute(select(Tenant).where(Tenant.id == tenant_uuid))).scalar_one_or_none()
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant
