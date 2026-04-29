# Deploy

The simplest possible production deploy. **Two services, three required env vars.**

```
┌──────────────────┐        ┌──────────────────┐
│  Railway / api   │ ──────▶│  Neon / Postgres │
│  uvicorn + sched │        │  (pgvector)      │
└────────┬─────────┘        └──────────────────┘
         │
         ▼
┌──────────────────┐
│  Railway / web   │
│  Next.js         │
└──────────────────┘
```

That's it. No worker service, no Redis, no manual bootstrap.

## Step 1 — Postgres (free)

Create a [Neon](https://neon.tech) project. Free tier ships with pgvector pre-installed.
Copy the connection string. (Supabase or any pgvector-enabled Postgres works the same way.)

## Step 2 — API service on Railway

1. New project → Deploy from GitHub repo → `skyweaverob/water-project`
2. Root directory: `api`
3. Add three environment variables:

   ```
   DATABASE_URL=<paste from Neon>
   ANTHROPIC_API_KEY=sk-ant-...
   SEARCH_API_KEY=<your key>
   ```

4. Deploy.

The API container's `entrypoint.sh` runs the schema bootstrap and the lifespan handler
auto-creates a demo tenant on first boot. The in-process scheduler runs the daily risk
refresh, weekly price refresh, and quarterly board report — same functionality the
old Arq worker had, no separate service needed.

Verify:
- `https://<api>.up.railway.app/healthz` → `{"status":"ok"}`
- `https://<api>.up.railway.app/tenants` → returns the auto-created demo tenant.

## Step 3 — Web service on Railway

1. Same project → New service → Deploy from same GitHub repo
2. Root directory: `web`
3. Add one **build arg** (Settings → Build → Build Args, NOT runtime env):

   ```
   NEXT_PUBLIC_API_BASE_URL=https://<your-api-service>.up.railway.app
   ```

4. Deploy.

Verify:
- `https://<web>.up.railway.app/design` → design system reference page.
- `https://<web>.up.railway.app/dashboard` → demo dashboard.

That's the deploy.

## Step 4 — Ingest the EPA corpus (one-time, ~5 minutes)

The 46 EPA PDFs are committed at the repo root. From your local machine:

```bash
cd api
DATABASE_URL="<your Neon connection string>" \
ANTHROPIC_API_KEY="sk-ant-..." \
VOYAGE_API_KEY="<voyage key, optional but enables Q&A RAG>" \
EPA_CORPUS_DIR="../" \
python -m ingestion.run
```

After this completes, all 46 chemicals are in `chemicals` and the auto-created demo
tenant's portfolio links to Aluminum Sulfate, Sodium Hypochlorite, and Calcium Hydroxide.

## Free upgrades (5 minutes, all optional)

Add these env vars to the API service to turn on free price/signal layers:

```
VOYAGE_API_KEY=<free at voyageai.com>     # turns on Knowledge Q&A RAG
EIA_API_KEY=<free at eia.gov/opendata>    # daily Henry Hub gas, WTI, refinery
BUSINESSANALYTIQ_MODE=on                  # adds free public price indices
```

## Paid upgrade ($58/mo) — Intratec authoritative pricing

Subscribe to [Intratec Advanced](https://www.intratec.us/solutions/primary-commodity-prices/ultimate)
($699/yr). Add to the API service:

```
INTRATEC_MODE=api
INTRATEC_API_KEY=<...>
```

The price-source resolver auto-promotes Intratec above all other sources for the 19
covered chemicals; everything else (alum, PAC, ferric chloride, etc.) keeps falling
through to businessanalytiq → FRED → search agent.

## Cost

| Service | Provider | Free tier | Paid |
|---|---|---|---|
| Postgres + pgvector | Neon | 0.5 GB free | $19/mo Pro |
| API container | Railway | trial credit | ~$5/mo |
| Web container | Railway | trial credit | ~$5/mo |
| **Infra total** | | **$0** | **~$10/mo** |

Variable: search API (your prepaid key, expires May 10), Anthropic (per-token, ~$1-2/day
for the daily worker on a 30-chemical portfolio), Voyage (per-token, ~$0.10/day).

## Troubleshooting

- **`pgvector extension does not exist`** → you're not on Neon/Supabase/pgvector image. Switch.
- **Browser shows 401 on every API call** → `NEXT_PUBLIC_API_BASE_URL` build arg wasn't set
  before the web service was built. Trigger a fresh deploy of the web service.
- **CORS error** → the regex catches `*.up.railway.app`, `*.vercel.app`, `*.onrender.com`, and
  `*.fly.dev` automatically. For custom domains, set `CORS_ORIGINS=https://yourdomain.com`.
- **Knowledge Q&A returns 503** → set `VOYAGE_API_KEY` and redeploy the API.
- **Daily risk refresh isn't running** → check API logs. The scheduler logs each fire
  with `scheduler: running daily_risk_refresh`. If you see it logged but no rows
  appear, check `errors` in the summary log line.
