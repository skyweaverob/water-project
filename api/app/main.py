import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app import scheduler
from app.config import get_settings
from app.db import SessionLocal, engine
from app.models import Base, FacilityProfile, PortfolioChemical, Tenant, Chemical
from app.routers import bids, chemicals, intelligence, knowledge, rfps, risk, tenants

settings = get_settings()
log = logging.getLogger("aquaprice")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


async def _bootstrap_schema() -> bool:
    """Provision pgvector + tables if missing. Returns True if pgvector is present."""
    async with engine.begin() as conn:
        try:
            await conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
            has_vector = True
        except Exception as exc:  # noqa: BLE001
            log.warning("pgvector unavailable (%s) — Knowledge Q&A will return 503", exc)
            has_vector = False
        await conn.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        await conn.run_sync(Base.metadata.create_all)
    return has_vector


async def _ensure_demo_tenant() -> None:
    """Create a default tenant + facility on first boot so the platform is demoable
    immediately. No-op once any tenant exists."""
    async with SessionLocal() as session:
        existing = (await session.execute(select(Tenant).limit(1))).scalar_one_or_none()
        if existing:
            return

        tenant = Tenant(name="Demo Water District", vertical="municipal", plan="single_facility")
        session.add(tenant)
        await session.flush()
        facility = FacilityProfile(
            tenant_id=tenant.id,
            name="Main Treatment Plant",
            sector="drinking_water",
            flow_mgd=12.0,
            treatment_processes=["coagulation", "filtration", "disinfection"],
            location_state="MA",
            location_city="Springfield",
        )
        session.add(facility)
        await session.flush()
        for name, demand_kg in (
            ("Aluminum Sulfate", 2_500_000.0),
            ("Sodium Hypochlorite", 720_000.0),
            ("Calcium Hydroxide", 480_000.0),
        ):
            chem = (await session.execute(select(Chemical).where(Chemical.name == name))).scalar_one_or_none()
            if chem:
                session.add(PortfolioChemical(facility_id=facility.id, chemical_id=chem.id, annual_demand_kg=demand_kg))
        await session.commit()
        log.info("bootstrap: created demo tenant id=%s", tenant.id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _bootstrap_schema()
    await _ensure_demo_tenant()

    stop = asyncio.Event()
    sched_task = asyncio.create_task(scheduler.start(stop))
    try:
        yield
    finally:
        stop.set()
        await sched_task


app = FastAPI(
    title="Aquaprice API",
    version="0.1.0",
    description="Buy-side procurement intelligence for water treatment chemicals.",
    lifespan=lifespan,
)

# CORS: regex matches any *.up.railway.app or *.vercel.app host plus the explicit origins
# from CORS_ORIGINS. No manual wiring needed for the common deploy patterns.
_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["http://localhost:3000"],
    allow_origin_regex=r"https://.*\.(up\.railway\.app|vercel\.app|onrender\.com|fly\.dev)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


app.include_router(tenants.router)
app.include_router(chemicals.router)
app.include_router(rfps.router)
app.include_router(bids.router)
app.include_router(risk.router)
app.include_router(knowledge.router)
app.include_router(intelligence.router)
