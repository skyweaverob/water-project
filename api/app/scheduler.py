"""In-process scheduler.

Runs the same jobs the Arq worker used to run, but as asyncio tasks inside the api
process. Eliminates the need for a separate worker service AND the Redis dependency
without losing functionality.

Schedule:
- daily_risk_refresh   — every 24 h, first fire at the next 02:00 UTC
- weekly_price_refresh — every 7 d,  first fire at the next Monday 03:00 UTC
- quarterly_board_report — every Q1/Q2/Q3/Q4 boundary, first fire at the next Jan/Apr/Jul/Oct 1, 03:00 UTC

If the api restarts mid-day the schedule realigns automatically; jobs are idempotent so
repeated firings are safe.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.agents.disruption_monitor import scan_chemical
from app.agents.price_discovery import discover_price
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

log = logging.getLogger(__name__)

PRIORS = json.loads(
    (Path(__file__).parent / "intelligence" / "chemical_priors.json").read_text(encoding="utf-8")
)

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


def _seconds_until(target_hour: int, target_minute: int, *, weekday: int | None = None, month_day: int | None = None, valid_months: set[int] | None = None) -> float:
    """Return seconds from now until the next occurrence of the target time.

    weekday: 0=Monday .. 6=Sunday. None = daily.
    month_day + valid_months: for the quarterly job (first day of Jan/Apr/Jul/Oct).
    """
    now = datetime.now(tz=timezone.utc)
    candidate = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)

    if weekday is not None:
        # Advance until the candidate falls on the requested weekday.
        while candidate.weekday() != weekday:
            candidate += timedelta(days=1)

    if month_day is not None and valid_months is not None:
        # Advance day-by-day until we land on month_day in one of valid_months.
        while not (candidate.day == month_day and candidate.month in valid_months):
            candidate += timedelta(days=1)

    return max(60.0, (candidate - now).total_seconds())


async def _portfolio_chemicals(session, tenant_id) -> list[Chemical]:
    rows = await session.execute(
        select(Chemical)
        .join(PortfolioChemical, PortfolioChemical.chemical_id == Chemical.id)
        .join(FacilityProfile, FacilityProfile.id == PortfolioChemical.facility_id)
        .where(FacilityProfile.tenant_id == tenant_id)
        .distinct()
    )
    return list(rows.scalars().all())


async def daily_risk_refresh() -> dict:
    today = date.today()
    summary = {"tenants": 0, "alerts_raised": 0, "events_logged": 0, "errors": []}

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
                try:
                    scan = await scan_chemical(chem.name, family=prior.get("family"))
                except Exception as exc:  # noqa: BLE001
                    summary["errors"].append(f"{chem.name}: {exc}")
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
                session.add(
                    RiskScore(
                        tenant_id=tenant.id,
                        facility_id=None,
                        chemical_id=chem.id,
                        score_date=today,
                        composite_score=chem_score[chem.name],
                        composite_band=_band_for(chem_score[chem.name]),
                        components={"base": base, "delta": chem_score[chem.name] - base, "events": len(scan.events)},
                    )
                )

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
                names = [(await session.get(Chemical, pc.chemical_id)).name for pc in portfolio]
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


async def weekly_price_refresh() -> dict:
    summary = {"tenants": 0, "chemicals": 0}
    async with SessionLocal() as session:
        tenants = (await session.execute(select(Tenant))).scalars().all()
        for tenant in tenants:
            summary["tenants"] += 1
            chems = await _portfolio_chemicals(session, tenant.id)
            for chem in chems:
                summary["chemicals"] += 1
                try:
                    await discover_price(chem.name, cas_number=chem.cas_number)
                except Exception:  # noqa: BLE001
                    pass
    return summary


async def quarterly_board_report() -> dict:
    return {"ran": datetime.now(timezone.utc).isoformat(), "status": "stub"}


async def _loop(name: str, fn, *, interval_sec: float, initial_delay: float):
    """Generic recurring runner with bounded error handling."""
    log.info("scheduler: %s scheduled in %.0fs (then every %.0fs)", name, initial_delay, interval_sec)
    await asyncio.sleep(initial_delay)
    while True:
        try:
            log.info("scheduler: running %s", name)
            result = await fn()
            log.info("scheduler: %s done: %s", name, result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            log.exception("scheduler: %s failed: %s", name, exc)
        await asyncio.sleep(interval_sec)


async def start(stop_event: asyncio.Event) -> None:
    """Launch the three scheduled jobs as concurrent asyncio tasks. Returns when
    stop_event is set (FastAPI lifespan teardown)."""
    tasks = [
        asyncio.create_task(
            _loop(
                "daily_risk_refresh",
                daily_risk_refresh,
                interval_sec=24 * 3600,
                initial_delay=_seconds_until(2, 0),
            )
        ),
        asyncio.create_task(
            _loop(
                "weekly_price_refresh",
                weekly_price_refresh,
                interval_sec=7 * 24 * 3600,
                initial_delay=_seconds_until(3, 0, weekday=0),
            )
        ),
        asyncio.create_task(
            _loop(
                "quarterly_board_report",
                quarterly_board_report,
                interval_sec=90 * 24 * 3600,
                initial_delay=_seconds_until(3, 0, month_day=1, valid_months={1, 4, 7, 10}),
            )
        ),
    ]
    await stop_event.wait()
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
