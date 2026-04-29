"""Demo seed: provisions a tenant, a facility, and a portfolio of three chemicals so the
platform is demoable end-to-end without manual data entry.

Usage:
    python -m app.scripts.seed_demo

Prerequisite: run `python -m app.scripts.create_all` and (optionally) ingest the EPA corpus.
"""
import asyncio

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Chemical, FacilityProfile, PortfolioChemical, Tenant


async def run() -> None:
    async with SessionLocal() as session:
        existing = (
            await session.execute(select(Tenant).where(Tenant.name == "Springfield Water District"))
        ).scalar_one_or_none()
        if existing:
            print(f"Demo tenant already exists: {existing.id}")
            return

        tenant = Tenant(name="Springfield Water District", vertical="municipal", plan="single_facility")
        session.add(tenant)
        await session.flush()

        facility = FacilityProfile(
            tenant_id=tenant.id,
            name="Springfield Water Treatment Plant",
            sector="drinking_water",
            flow_mgd=12.4,
            treatment_processes=["coagulation", "sedimentation", "filtration", "disinfection"],
            location_state="MA",
            location_city="Springfield",
        )
        session.add(facility)
        await session.flush()

        # Map the demo portfolio to chemicals already ingested. Skip cleanly if absent.
        for name, demand_kg in (
            ("Aluminum Sulfate", 2_500_000.0),
            ("Sodium Hypochlorite", 720_000.0),
            ("Calcium Hydroxide", 480_000.0),
        ):
            chem = (
                await session.execute(select(Chemical).where(Chemical.name == name))
            ).scalar_one_or_none()
            if not chem:
                print(f"  · skipped {name} (not yet ingested)")
                continue
            session.add(
                PortfolioChemical(
                    facility_id=facility.id,
                    chemical_id=chem.id,
                    annual_demand_kg=demand_kg,
                )
            )

        await session.commit()
        print(f"Demo tenant created: {tenant.id}")
        print(f"  Set NEXT_PUBLIC_DEMO_TENANT_ID={tenant.id} in web/.env.local")


if __name__ == "__main__":
    asyncio.run(run())
