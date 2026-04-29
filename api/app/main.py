from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import bids, chemicals, intelligence, knowledge, rfps, risk, tenants

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Aquaprice API",
    version="0.1.0",
    description="Buy-side procurement intelligence for water treatment chemicals.",
    lifespan=lifespan,
)

# CORS: comma-separated exact origins via CORS_ORIGINS, plus a regex for *.up.railway.app
# preview URLs so the frontend service can call the API across deploy environments.
_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"https://.*\.up\.railway\.app",
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
