# Backend deployment and frontend integration

Preserve the current FastAPI implementation during frontend handoff; global backend expansion is separate work. No public deployment is authorized in this stage. Python 3.12 with `backend/requirements.txt` is tested. No PostgreSQL adapter or frontend server is implemented. Run Uvicorn without reload in production; terminate HTTPS at a reverse proxy and set container/process budgets and public request rate limits there.

## Configuration and administration

Server `.env` configuration loads before settings; OS environment values take precedence. `FIRE_ENV_FILE` may select an alternate server-only file. Invalid CORS/admin/positive resource-limit settings fail startup. Restart to apply file changes.

Use `FIRE_CORS_ORIGINS=https://frontend.example` (comma-separated explicit HTTP(S) origins, no wildcard, paths or credentials). CORS allows GET operations and Content-Type. Empty configuration disables cross-origin browser use. It does not authenticate public reads. A same-origin reverse proxy is another integration option. No browser receives `EXPLORER_ADMIN_TOKEN` or `FIRMS_MAP_KEY`.

Keep `EXPLORER_HTTP_INGEST_ENABLED=false`. All POST explorer operations (`/load`, `/availability/refresh`, `/cleanup`) require explicit enablement plus a server-only bearer admin token. Enabling ingestion without a valid token prevents startup. If operationally enabled, restrict these endpoints at the proxy too. Download/refresh also require the server NASA key; do not log NASA request URLs, which include it. Public GET routes never download or refresh NASA data. Availability is cache-only, with `checked_at` exposing age; no cached record means 503.

Run private ingestion/build separately. Original raw inputs, provenance manifests and immutable generations belong on durable storage. Do not bake secrets, caches or datasets into images or Git. The Docker build context currently includes only backend/pipeline source and requirements. Container builds have not been verified in this Windows environment.

## Storage and permissions

`FIRE_DATA_DIR` selects the shared data root. Regional reads require a valid processed CURRENT pointer and generation files. Health/regions/methodology work without analytical data; regional analytics return 503 if unprepared. Explorer reads need separately provisioned cached generations; a regional import does not populate explorer datasets and an explorer load does not build regional summaries.

Explorer `/cached`, `/view` and `/export` open a coordination lock at the data root, even for public GET requests. **Do not assume the entire API data mount can be read-only.** Give API workers narrowly scoped write access to the root coordination lock (the current implementation opens it in append/update mode). Keep raw/processed datasets read-only to API workers where possible. Use a local filesystem with working OS advisory locks; distributed/object-store locking is not implemented. Mutations take exclusive locks; readers use coordinated locks and can serialize on Windows. Contention returns 409. Never delete regional generations while requests may reference them.

A practical Docker layout is a writable `/app/data` root/coordination area with separate read-only `/app/data/raw` and `/app/data/processed` mounts and an explorer directory writable only for explicitly authorized administration. Mounts must provide the already provisioned datasets. `docker build -t fire-backend .` builds the provided image; production deployment and mount ownership must be verified in the target environment. The default container listens on port 8000. No full read-only-mount guarantee is made.

## Budgets and explicit cleanup

| Setting | Default |
| --- | --- |
| FIRE_MAX_FILE_BYTES | 67,108,864 |
| FIRE_MAX_OBSERVATIONS | 1,000,000 |
| FIRE_MAX_CACHE_BYTES | 1,073,741,824 |
| FIRE_CACHE_RETENTION_DAYS | 7 |

All are positive integers. Per-file and cumulative row budgets apply to ingestion/builds; explorer cache writes and exports are bounded. Oversized HTTP requests return 413. Existing oversized datasets are preserved and may encounter query resource limits. Four DuckDB connections per worker each permit 256 MiB memory, two threads and 256 MiB spill; budget deployment-wide resources for worker count.

Cache cleanup is deliberate: local `python -m pipeline.cache` or enabled/admin-authenticated POST `/api/explorer/cleanup`. It removes UUID-named explorer directories older than the configured age based on directory mtime and associated selection pointers. It does not expire availability metadata or delete original raw/processed historical data. Startup never evicts existing data. Cache saturation rejects writes; an operator manages cleanup/storage. Retain raw manifests and checksum-verified originals and back them up separately.

## Scientific and frontend boundaries

Monthly `/calendar`, `/trends`, `/anomalies` share a monthly response; a partial requested month is still one monthly bucket. Never relabel these as daily time series. `explorer/view.daily` is daily only within that cached selection and filters; it is not measured satellite observation opportunity. Keep source/version/stream distinctions and both grid definitions visible. Null values are unavailable, not zero; coverage is operator-declared file completeness. No incident counts, burned area, forecasts or calibrated harmonization are implemented.

Integrate independently with React and TypeScript using the current implementation schema and [Gemini package](../gemini-handoff/INTEGRATION_GUIDE.md). Handle unavailable processed data (503), missing/expired explorer datasets (404), validation (422), disabled/admin auth (403), lock/harmonization conflicts (409), budgets (413) and sanitized server/upstream failures. Exports are CSV despite incomplete media-type documentation for explorer exports in OpenAPI. No new endpoints are promised.

See [handoff verification](gemini-handoff-verification.md) for test results, archive checks and Git-state limitations. No deployment, commit or push has been authorized or performed.

The application target is global fire intelligence. Current local extracts and short cached datasets do not establish worldwide historical coverage. Provision future global archives and APIs separately before enabling corresponding live UI features; no full global archive or operational emergency alert service is claimed.
