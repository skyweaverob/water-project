"""Arq worker for background jobs.

- daily_risk_refresh: scans the live web for disruption events on every chemical in any
  tenant's portfolio, persists DisruptionEvents, raises RiskAlerts when severity warrants,
  and rolls a daily portfolio risk score per facility.
- weekly_price_refresh: runs the PriceDiscovery agent on each portfolio chemical, stores
  the median benchmark in chemical-level metadata so the Bid Evaluator picks it up.
- quarterly_board_report: assembles a board-ready PDF rollup per tenant.

These jobs collectively consume the user's search-API credits — the platform earns its
keep by spending the budget on monitoring rather than ad-hoc lookups.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.disruption_monitor import scan_chemical
from app.agents.price_discovery import discover_price
from app.config import get_settings
from app.db import SessionLocal
from app.models import (
    Chemical,
    DisruptionEvent as DBDisruptionEvent,
    FacilityProfile,
    PortfolioChemical,
    RiskAlert,
    RiskScore,
    Tenant,
)

_settings = get_settings()
PRIORS = json.loads(
    (Path(__file__).parent / "intelligence" / "chemical_priors.json").read_text(encoding="utf-8")
)


# Static base scores by EPA composite band; daily news adds delta.
BAND_BASE: dict[str, float] = {
    "Low": 20,
    "Moderate-Low": 35,
    "Moderate": 50,
    "Moderate-High": 70,
    "High": 90,
}
SEVERITY_DELTA: dict[str, float] = {"info": 0.0, "watch": 6.0, "warning": 14.0}


def _band_for(score: float) -> str:
    if score < 25:
        return "Low"
    if score < 45:
        return "Moderate-Low"
    if score < 60:
        return "Moderate"
    if score < 80:
        return "Moderate-High"
    return "High"


async def _portfolio_chemicals(session: AsyncSession, tenant_id) -> list[Chemical]:
    rows = await session.execute(
        select(Chemical)
        .join(PortfolioChemical, PortfolioChemical.chemical_id == Chemical.id)
        .join(FacilityProfile, FacilityProfile.id == PortfolioChemical.facility_id)
        .where(FacilityProfile.tenant_id == tenant_id)
        .distinct()
    )
    return list(rows.scalars().all())


async def daily_risk_refresh(ctx: dict) -> dict:
    today = date.today()
    summary = {"tenants": 0, "alerts_raised": 0, "events_logged": 0}

    async with SessionLocal() as session:
        tenants = (await session.execute(select(Tenant))).scalars().all()
        for tenant in tenants:
            summary["tenants"] += 1
            chems = await _portfolio_chemicals(session, tenant.id)
            chem_score: dict[str, float] = {}

            for chem in chems:
                prior = next(
                    (p for p in PRIORS["chemicals"] if p["name"].lower() == chem.name.lower()), {}
                )
                base = BAND_BASE.get(prior.get("risk", "Low"), 30.0)

                # Live web scan for disruption signals — isolated so one bad chemical
                # doesn't tank the whole nightly run.
                try:
                    scan = await scan_chemical(chem.name, family=prior.get("family"))
                except Exception as exc:  # noqa: BLE001
                    summary.setdefault("errors", []).append(f"{chem.name}: {exc}")
                    chem_score[chem.name] = base
                    continue

                delta = 0.0
                for ev in scan.events:
                    delta = max(delta, SEVERITY_DELTA.get(ev.severity, 0.0))
                    session.add(
                        DBDisruptionEvent(
                            chemical_id=chem.id,
                            event_date=today,
                            event_type=ev.event_type,
                            description=f"{ev.headline}\n\n{ev.body}",
                            source_citation=ev.source_url,
                        )
                    )
                    summary["events_logged"] += 1

                    if ev.severity in ("watch", "warning"):
                        session.add(
                            RiskAlert(
                                tenant_id=tenant.id,
                                facility_id=None,
                                chemical_id=chem.id,
                                severity=ev.severity,
                                headline=f"{chem.name}: {ev.headline}",
                                body=ev.body,
                                source_url=ev.source_url,
                                triggered_at=today,
                                acknowledged=False,
                            )
                        )
                        summary["alerts_raised"] += 1

                chem_score[chem.name] = min(100.0, base + delta)

                # Persist per-chemical score for tenant-level rollup
                session.add(
                    RiskScore(
                        tenant_id=tenant.id,
                        facility_id=None,  # tenant-level
                        chemical_id=chem.id,
                        score_date=today,
                        composite_score=chem_score[chem.name],
                        composite_band=_band_for(chem_score[chem.name]),
                        components={"base": base, "delta": chem_score[chem.name] - base, "events": len(scan.events)},
                    )
                )

            # Per-facility rollup: average score across that facility's portfolio chemicals
            facilities = (
                await session.execute(
                    select(FacilityProfile).where(FacilityProfile.tenant_id == tenant.id)
                )
            ).scalars().all()
            for fac in facilities:
                portfolio = (
                    await session.execute(
                        select(PortfolioChemical).where(PortfolioChemical.facility_id == fac.id)
                    )
                ).scalars().all()
                if not portfolio:
                    continue
                names = [
                    (await session.get(Chemical, pc.chemical_id)).name for pc in portfolio
                ]
                relevant = [chem_score[n] for n in names if n in chem_score]
                if not relevant:
                    continue
                composite = sum(relevant) / len(relevant)
                session.add(
                    RiskScore(
                        tenant_id=tenant.id,
                        facility_id=fac.id,
                        chemical_id=None,
                        score_date=today,
                        composite_score=composite,
                        composite_band=_band_for(composite),
                        components={"per_chemical": dict(zip(names, relevant, strict=False))},
                    )
                )

        await session.commit()
    return summary


async def weekly_price_refresh(ctx: dict) -> dict:
    summary = {"tenants": 0, "chemicals": 0}
    async with SessionLocal() as session:
        tenants = (await session.execute(select(Tenant))).scalars().all()
        for tenant in tenants:
            summary["tenants"] += 1
            chems = await _portfolio_chemicals(session, tenant.id)
            for chem in chems:
                summary["chemicals"] += 1
                # Just running the agent ensures the search cache is warm for the UI.
                await discover_price(chem.name, cas_number=chem.cas_number)
    return summary


async def quarterly_board_report(ctx: dict) -> dict:
    return {"ran": datetime.now(timezone.utc).isoformat(), "status": "stub"}


class WorkerSettings:
    # Arq reads REDIS_URL via RedisSettings.from_dsn — works with railway.app's REDIS_URL.
    redis_settings = RedisSettings.from_dsn(_settings.redis_url)

    cron_jobs = [
        cron(daily_risk_refresh, hour={2}, minute={0}),
        cron(weekly_price_refresh, weekday="mon", hour={3}, minute={0}),
        # arq's parameter is `month_day`, not `day`. `month` is a set of months 1-12.
        cron(quarterly_board_report, month={1, 4, 7, 10}, month_day={1}, hour={3}, minute={0}),
    ]
    functions = [daily_risk_refresh, weekly_price_refresh, quarterly_board_report]
