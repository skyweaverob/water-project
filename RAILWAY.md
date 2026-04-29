# Railway deploy guide

Step-by-step. Each step is one click in the Railway UI unless noted. Total wall-clock for a
clean deploy: ~25 minutes.

## 1. Provision the four infrastructure services

In a new Railway project, add these services in order. The order matters because later
services consume env vars exposed by earlier ones.

### 1a. Postgres with pgvector

**Do NOT use Railway's stock Postgres template.** It does not ship with the `pgvector`
extension binary, so `CREATE EXTENSION vector` will fail and the API will be unable to
write `fact_sheet_chunks.embedding`.

Instead:

- Add Service → **Deploy from Docker Image**
- Image: `pgvector/pgvector:pg16`
- Service Variables:
  - `POSTGRES_USER` = `postgres`
  - `POSTGRES_PASSWORD` = (generate a strong one)
  - `POSTGRES_DB` = `procurement`
- Public networking: off (Railway internal only).
- Volume: mount `/var/lib/postgresql/data` to a persistent Railway volume.

After it boots, copy the `DATABASE_URL` Railway exposes for the service — you'll wire it
into the api and worker below.

### 1b. Redis

- Add Service → **Database** → Redis (the stock template is fine for Arq).
- Copy the `REDIS_URL` it exposes.

## 2. Deploy the API service

- Add Service → **GitHub Repo** → `skyweaverob/water-project`
- Root directory: `/api`
- Builder: Dockerfile (auto-detected from `api/railway.json`)
- Healthcheck path: `/healthz` (auto-detected)
- Service Variables:
  - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`
  - `REDIS_URL` = `${{Redis.REDIS_URL}}`
  - `ANTHROPIC_API_KEY` = (your Anthropic key)
  - `VOYAGE_API_KEY` = (your Voyage key — required for embeddings/RAG)
  - `SEARCH_PROVIDER` = `brave` (or `tavily` / `exa` / `serpapi`)
  - `SEARCH_API_KEY` = (your search key)
  - `CLAUDE_MODEL_DEFAULT` = `claude-sonnet-4-6`
  - `CLAUDE_MODEL_SYNTHESIS` = `claude-opus-4-7`
  - `CLAUDE_MODEL_EMBED` = `voyage-3`
  - `CORS_ORIGINS` = (set after step 4 — the web service's public URL)

The API container's entrypoint runs `python -m app.scripts.create_all` before starting
uvicorn, so the schema is provisioned on first boot. If pgvector isn't available the
script logs a warning and the API still starts (the Q&A endpoint will fail until the
extension is present, but everything else works).

After the first deploy is green, exec into the container once to seed the demo tenant:

```bash
railway run python -m app.scripts.seed_demo
```

Copy the printed tenant UUID — you'll need it for the web service.

## 3. Deploy the worker service

- Add Service → **GitHub Repo** → same `water-project` repo
- Root directory: `/` (the worker Dockerfile lives at `worker/Dockerfile` and consumes
  `api/` as its source tree, so the build context must be the repo root).
- Builder: Dockerfile, path = `worker/Dockerfile` (auto-detected from `worker/railway.json`).
- Service Variables: same as the API service. The worker has no public network surface.

## 4. Deploy the web service

- Add Service → **GitHub Repo** → same repo
- Root directory: `/web`
- **Build args** (these matter — `NEXT_PUBLIC_*` is inlined at build time, not runtime):
  - `NEXT_PUBLIC_API_BASE_URL` = the API service's public Railway URL (e.g.
    `https://api-production-xxxx.up.railway.app`)
  - `NEXT_PUBLIC_DEMO_TENANT_ID` = the tenant UUID from step 2
  - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` = (when you wire up Clerk)
- Service Variables (runtime, not used by NEXT_PUBLIC vars but useful for server actions):
  - `NEXT_PUBLIC_API_BASE_URL` = same as the build arg
- Public networking: on. Copy the URL.

## 5. Wire CORS

Go back to the API service. Set:

- `CORS_ORIGINS` = the web service's public URL (e.g. `https://web-production-yyyy.up.railway.app`)

The API also accepts any `*.up.railway.app` host via regex, so preview deploys work
without manual CORS updates.

## 6. Ingest the EPA corpus (one-time, ~5 minutes)

The corpus PDFs are committed to the repo at the root, so the worker container has them
at `/app/.` (since `worker/Dockerfile` only copies `api/`, the PDFs are NOT inside the
worker image). Two options:

**Option A — exec on the API service** (recommended, the API image's `WORKDIR` is `/app`
and contains the same code; we'll temporarily mount the corpus):

The corpus PDFs aren't in the API image either by default. Easiest path: `railway run` a
one-off ingestion job from your local machine pointing at the production database.

```bash
# from your local machine, with .env pointing at the Railway DATABASE_URL:
cd api
EPA_CORPUS_DIR="../" python -m ingestion.run --bootstrap
```

**Option B — bake the corpus into the worker image** by editing `worker/Dockerfile` to
`COPY *.pdf /corpus/` and running `EPA_CORPUS_DIR=/corpus python -m ingestion.run` once
on the worker.

## 7. Verify

- `https://<api>/healthz` → `{"status":"ok"}`
- `https://<api>/chemicals` → list of 46 chemicals (after ingestion)
- `https://<web>/design` → design system reference page
- `https://<web>/dashboard` → demo dashboard

## 8. Costs

Rough monthly costs at idle traffic, based on Railway's hobby tier pricing as of April 2026:

| Service | Plan | $/mo |
|---|---|---|
| Postgres (pgvector image, 0.5 GB RAM) | Hobby | ~$5 |
| Redis (256 MB) | Hobby | ~$3 |
| API (0.5 vCPU, 512 MB) | Hobby | ~$5 |
| Worker (0.25 vCPU, 256 MB) | Hobby | ~$3 |
| Web (0.5 vCPU, 512 MB) | Hobby | ~$5 |
| **Total infra** | | **~$21** |

Variable: the search API (your prepaid key), Anthropic (per-token), Voyage (per-token).
The daily worker on a 30-chemical portfolio runs ~150 search queries + ~30 Claude calls;
budget ~$1-2/day in API spend.

## Troubleshooting

- **"create_all failed with 'extension vector does not exist'"** — you used Railway's
  stock Postgres. Replace it with the `pgvector/pgvector:pg16` image as in step 1a.
- **Web app loads but every API call returns 401** — the `NEXT_PUBLIC_DEMO_TENANT_ID`
  build arg is missing or stale. Trigger a fresh deploy of the web service after the
  build arg is set.
- **CORS error in the browser console** — `CORS_ORIGINS` on the API doesn't include the
  web service's exact URL. Either update the env var or rely on the `*.up.railway.app`
  regex match, which works for default Railway domains but not for custom domains.
- **Worker logs "RuntimeError: cron parameter 'day'"** — you're on a stale image. The
  fix landed in this commit; redeploy the worker.
- **Knowledge Q&A returns 500 with `pgvector` errors** — the extension needs to exist
  AND the table needs to be created with the `vector(1024)` column. Run
  `railway run python -m app.scripts.create_all` once after pgvector is installed.
