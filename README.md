# Aquaprice — Buy-side procurement intelligence for water treatment chemicals

A vertical procurement intelligence platform for municipal utilities and industrial pretreatment
operators. Helps procurement officers and plant superintendents write defensible RFPs, evaluate
bids on real cost per kilogram of active ingredient, and monitor supply chain risk on contracts
for the 46 EPA-profiled water treatment chemicals.

This README covers architecture, local setup, deploying to Railway, ingesting the EPA corpus,
adding chemicals, and configuring vertical (municipal vs. industrial) behavior.

---

## Architecture

```
┌──────────────────────┐        ┌────────────────────────┐
│  web (Next.js 14)    │ ──────▶│  api (FastAPI)         │
│                      │        │  routers + agents +    │
│                      │        │  in-process scheduler  │
└──────────────────────┘        └────────┬───────────────┘
                                         │
                                ┌────────▼────────┐
                                │  Postgres +     │
                                │  pgvector       │
                                └─────────────────┘
```

**Two services + one Postgres.** The api process runs the scheduler in-process
(asyncio tasks for daily risk refresh, weekly price refresh, quarterly board report) —
no Redis or worker container needed.

### Module map

| Module | API surface | Frontend | Status |
|---|---|---|---|
| Knowledge base ingestion | `ingestion/run.py` | — | Phase 1, run once |
| RFP Builder | `/rfps`, `/rfps/{id}/document` | `/rfps`, `/rfps/new` | Generates DOCX |
| Bid Evaluator | `/bids`, `/bids/by-rfp/{id}/evaluate`, `.../memo`, `.../market-benchmark` | `/bids` | Generates PDF memo, live price benchmark |
| Risk Monitor | `/risk/portfolio`, `/risk/timeseries`, `/risk/alerts` | `/risk` | Daily in-process scheduler scans live web |
| Knowledge Q&A | `/knowledge/ask` (NDJSON stream) | `/knowledge` | RAG over EPA fact sheets |
| Intelligence | `/intelligence/price/{name}`, `/suppliers/{name}`, `/disruptions/{name}`, `/signals/...` | embedded | Search-powered agents |
| Design system | — | `/design` | Reference page for every component |
| Marketing | — | `/` | Sign-out home page |

### Search-driven price discovery

The platform uses a single web search API (configurable: Brave / Tavily / Exa / SerpAPI) for two
purposes:

1. **Risk Monitor (daily job)** — searches live news and SEC EDGAR for force-majeure, plant
   closures, antidumping orders, hurricane tracks, and feedstock disruptions for each portfolio
   chemical. Confirmed events become `RiskAlerts`; severity scales the chemical's risk score.

2. **Bid Evaluator (live price benchmark)** — for each RFP, the platform crafts queries from
   the chemical's family-aware template set (USGS MCS for minerals, ICIS spot for chlor-alkali,
   AWWA RFP awards for utilities, etc.), fetches the top results, and asks Claude to extract
   numeric $/kg-active-ingredient prices. The median across high-confidence points becomes the
   "market median" column next to each supplier's normalized price.

The same client also drives `SupplierDiscovery` (NSF/ANSI 60 supplier shortlist) and shows up
in the live Q&A retrieval mix.

Configure with two env vars:

```
SEARCH_PROVIDER=brave   # or tavily | exa | serpapi
SEARCH_API_KEY=...
```

The platform never hard-codes credentials. Provider-specific request shapes are normalized in
[api/app/services/search.py](api/app/services/search.py).

### Price-source resolver

For each chemical, the platform picks the highest-quality available source and falls
through cleanly. Configured in [api/app/services/price_resolver.py](api/app/services/price_resolver.py):

| Tier | Source | Configure | Confidence | Output |
|---|---|---|---|---|
| 1 | **Intratec Primary Commodity Prices** | `INTRATEC_MODE=api`, `INTRATEC_API_KEY=...` ($699/yr Advanced tier) — or `INTRATEC_MODE=csv`, `INTRATEC_CSV_DIR=...` ($299/yr Starter tier) | 0.95 | $/kg active, monthly |
| 2 | **businessanalytiq.com** free public indices | `BUSINESSANALYTIQ_MODE=on` | 0.65 | $/kg active, scraped from public index pages (covers ferric chloride, alum, others Intratec misses) |
| 3 | **FRED PPI series** | always-on, no key | 0.7 | index value (not absolute) |
| 4 | **Search-API price discovery** | reuses `SEARCH_API_KEY` | 0.6 | $/kg active, sourced from utility RFP awards & trade press |
| 5 | **Static EPA prior** | always-on | 0.3 | family + risk band only |

Plus the [EIA Open Data API](https://www.eia.gov/opendata/) (`EIA_API_KEY=...`) feeding daily
Henry Hub gas, WTI crude, weekly refinery utilization into the Risk Monitor — these drive
ammonia, sulfur, and chloramine pricing more than chemical-specific indices do.

The Bid Evaluator's market-benchmark column tags each row with the source so buyers see
which prices are authoritative (Intratec) vs derived (FRED) vs inferred (search agent).

### Public-data signal sources

In addition to the search API, the Risk Monitor pulls from free authoritative feeds (no key
required) — see [api/app/services/public_signals.py](api/app/services/public_signals.py):

| Source | URL | Use |
|---|---|---|
| FRED PPI series | fred.stlouisfed.org | Chlor-alkali index, Henry Hub, WTI |
| USGS earthquake feed | earthquake.usgs.gov | Mining-region exposure |
| NOAA NHC | nhc.noaa.gov | Active tropical cyclones (Gulf petrochem) |
| SEC EDGAR full-text | efts.sec.gov | Force-majeure 8-Ks |
| EPA ECHO | echo.epa.gov | NPDES violations near producers |
| GDELT 2.0 | api.gdeltproject.org | Free 15-min news cadence |

(Roadmap: Army Corps Lock Performance for barge-transit delays on caustic shipments — not in v1.)

---

## Local setup

```bash
# 1. Clone and copy env
cp .env.example .env
# fill in: ANTHROPIC_API_KEY, VOYAGE_API_KEY, SEARCH_API_KEY, CLERK keys, STRIPE keys

# 2. Bring up postgres
docker compose up -d postgres

# 3. Provision schema (creates pgvector extension + all tables)
cd api
python -m venv .venv && source .venv/bin/activate
pip install .
python -m app.scripts.create_all

# 4. (Optional) Run Phase 1 ingestion against the EPA corpus
EPA_CORPUS_DIR=/abs/path/to/corpus python -m ingestion.run

# 5. Start the API
uvicorn app.main:app --reload --port 8000

# 6. In another shell, start the web app
cd ../web
npm install
npm run dev
```

Visit `http://localhost:3000`.

The design system reference lives at `/design`. Build that first and review before iterating
on feature screens.

---

## Phase 1: ingest the EPA corpus

The 46 EPA Water Treatment Chemical Supply Chain Profiles (December 2022 series) live in
`./` (or wherever you set `EPA_CORPUS_DIR`). The extraction agent in
[api/app/agents/extraction.py](api/app/agents/extraction.py) reads each PDF, calls Claude
with a strict tool-use schema, persists structured fields into seven tables, and embeds
section-tagged chunks into `fact_sheet_chunks` for the Q&A RAG.

```bash
# Ingest a single chemical (smoke-test):
python -m ingestion.run --only "Aluminum Sulfate"

# Dry-run (extract + print, no persist):
python -m ingestion.run --only "Aluminum Sulfate" --dry-run

# Ingest the full corpus:
python -m ingestion.run

# Bootstrap schema first time:
python -m ingestion.run --bootstrap
```

The agent emits a per-field confidence score so you can spot extractions worth reviewing
manually in the database.

After ingestion, the platform also has two static knowledge files that don't depend on the
database — these were compiled from a deep read of the corpus:

- [api/app/intelligence/corpus_intelligence.md](api/app/intelligence/corpus_intelligence.md):
  cross-cutting market patterns (chlor-alkali co-production, Gulf Coast risk, NSF60 supplier
  counts, shelf-life-driven inventory strategy, antidumping cliffs).

- [api/app/intelligence/price_sources.json](api/app/intelligence/price_sources.json):
  registry of every price-discovery source the EPA cited, plus the search-driven queries the
  Risk Monitor and Price Discovery agents use to triangulate live prices.

- [api/app/intelligence/chemical_priors.json](api/app/intelligence/chemical_priors.json):
  per-chemical priors (CAS, family, risk band, NSF60 supplier count, named producers) used
  as a fallback when ingested data is missing or low-confidence.

---

## Adding a new chemical

1. Drop the EPA fact-sheet PDF into your corpus directory.
2. Run ingestion: `python -m ingestion.run --only "<chemical name>"`.
3. (Optional) Add an entry to `chemical_priors.json` for the offline fallback.
4. (Optional) Map the chemical to its AWWA standard in `api/app/services/rfp_builder.py`
   `AWWA_STANDARD` dict so the RFP Builder includes the correct compliance reference.

That's it — the rest of the platform picks up the new chemical automatically.

---

## Verticals: municipal vs. industrial

A single codebase serves two kinds of buyer. Each tenant is configured with `vertical = municipal`
or `vertical = industrial`. The configuration affects:

- RFP boilerplate (governing-body approval and public-records language vs. ESG/Scope-3 and
  environmental-impairment-liability language) — see `boilerplate_municipal` and
  `boilerplate_industrial` in `api/app/services/rfp_builder.py`.
- Award memo format — municipal memos address a procurement committee in plant-superintendent
  voice; industrial memos address corporate procurement and ESG committees.
- Reporting conventions — quarterly board PDFs use AWWA-style language for municipal, ESG
  rollup language for industrial (planned in `scheduler.quarterly_board_report`).

To customize further, populate the `vertical_config` table with terminology overrides and
report-template IDs.

---

## Deploying

See **[DEPLOY.md](DEPLOY.md)** for the full step-by-step. The short version:

1. Create a free [Neon](https://neon.tech) Postgres project (ships with pgvector).
2. Deploy the `api` directory to Railway. Set 3 env vars: `DATABASE_URL`,
   `ANTHROPIC_API_KEY`, `SEARCH_API_KEY`.
3. Deploy the `web` directory to Railway with `NEXT_PUBLIC_API_BASE_URL` as a build arg.

That's it. Schema bootstrap, demo tenant creation, and the daily/weekly/quarterly
scheduled jobs all happen automatically inside the api process.

---

## Pricing & entitlements

Three tiers (see the `/` marketing page):

- **Single facility** — $8K-12K/year, 1 facility, 5 seats.
- **Multi-facility** — $40K-150K/year, up to 25 facilities, unlimited seats.
- **Enterprise** — custom; SSO, audit logs, dedicated SE, custom verticals.

Billing is wired through Stripe (`tenants.plan`, `tenants.stripe_subscription_id`). The
entitlements layer is intentionally thin — the seat and facility caps live on `tenants`
and are enforced at write time in the routers.

---

## What's deliberately not built yet

- Self-serve signup. (Tenants are provisioned via `/tenants` for now.)
- Mobile apps.
- Anything beyond what's demoable to a Tyson environmental manager or a 100 MGD utility
  procurement officer.

---

## Repo layout

```
api/
  app/
    main.py                     FastAPI app + router wiring
    config.py                   Settings (env-driven)
    db.py                       async SQLAlchemy engine
    auth.py                     tenant resolution (Clerk-pluggable)
    models/                     SQLAlchemy ORM
    routers/
      tenants.py
      chemicals.py
      rfps.py                   Module 1 RFP Builder + DOCX download
      bids.py                   Module 2 Bid Evaluator + memo PDF
      risk.py                   Module 3 portfolio, timeseries, alerts
      knowledge.py              Module 4 Q&A streaming
      intelligence.py           live price/supplier/disruption + signals
    agents/
      extraction.py             Phase 1 EPA fact sheet extractor
      chunker.py                section-aware chunking for RAG
      embeddings.py             Voyage embeddings client
      rag.py                    pgvector retrieval + Claude synthesis
      bid_extraction.py         supplier bid PDF extractor
      price_discovery.py        live $/kg market benchmark
      supplier_discovery.py     live NSF60 supplier shortlist
      disruption_monitor.py     live force-majeure / outage scan
      anthropic_client.py
    services/
      rfp_builder.py            risk-band → resilience clauses, weights, DOCX render
      bid_evaluator.py          unit normalization, scoring, PDF memo
      search.py                 multi-provider web search
      public_signals.py         FRED, USGS, NHC, EDGAR, ECHO, GDELT
    intelligence/
      corpus_intelligence.md    cross-cutting market patterns from 46-PDF read
      price_sources.json        price-discovery source registry
      chemical_priors.json      offline per-chemical priors
    scripts/create_all.py       schema provisioner
    scheduler.py                in-process asyncio scheduler (daily/weekly/quarterly jobs)
  ingestion/run.py              Phase 1 runner
  migrations/                   Alembic env + initial revision
  Dockerfile, railway.json, pyproject.toml

web/
  app/
    page.tsx                    marketing home (signed-out)
    design/page.tsx             design-system reference
    dashboard/page.tsx          single-page dashboard
    rfps/page.tsx, new/page.tsx
    bids/page.tsx               Bid Evaluator with live benchmark column
    risk/page.tsx               Portfolio chart + table
    knowledge/page.tsx          streaming Q&A with citations
  components/
    nav.tsx                     translucent top nav
    risk-chart.tsx              Recharts line chart
    ui/                         button, card, input, table, modal, risk-dot, empty-state
  styles/tokens.ts              every design token
  tailwind.config.ts            replaces (not extends) the default theme
  Dockerfile, railway.json, package.json, tsconfig.json

docker-compose.yml              local dev stack
.env.example                    every env var the platform reads
README.md                       you are here
```

---

## License & data

The 46 EPA Water Treatment Chemical Supply Chain Profiles are public-domain U.S. government
work product (EPA 817-F-22 series). The platform's intelligence files derive from a deep
read of those PDFs and are committed to this repo as `corpus_intelligence.md`,
`price_sources.json`, and `chemical_priors.json`. Refresh them when the EPA publishes a new
fact-sheet edition.
