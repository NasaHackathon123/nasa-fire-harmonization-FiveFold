# NASA Fire Activity Explorer

The product target is a GLOBAL NASA Fire Activity Explorer for scientific and professional users, with an independent frontend preferably using React and TypeScript. The current FastAPI backend and scientific pipeline are preserved during this handoff; the backend team is expanding global capabilities. There is no frontend or static application mount. `/` and `/static/...` return 404. Connect implemented functionality to existing APIs without changing their calculations. Current OpenAPI is an implementation snapshot, not the final global API contract.

## Local setup

Python 3.12 is tested; Node.js and PostgreSQL are not backend requirements.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Do not overwrite an existing `.env`. Configuration is loaded before startup settings; OS environment variables take precedence. Optional server-only `FIRE_ENV_FILE` selects another environment file. Restart after file changes. Open `http://127.0.0.1:8000/docs`; `/api/health` reports `data_ready` without downloading data. Data-dependent routes return 503 until processed imports are available. A clone and the handoff ZIP do not contain datasets.

## Frontend integration and CORS

Set an explicit frontend origin before backend startup, for example in the server `.env`:

```dotenv
FIRE_CORS_ORIGINS=http://localhost:5173,https://frontend.example
EXPLORER_HTTP_INGEST_ENABLED=false
```

No wildcard, origin URL paths, embedded credentials or invalid ports are accepted. Empty origins disable cross-origin browser access. CORS permits GET operations; browser code must not contain administrative tokens or NASA keys. HTTPS frontends require an HTTPS backend or a same-origin reverse proxy. Only the public API base URL belongs in frontend configuration.

The five-day Kalimantan extract is test data, not representative global coverage. Complete global MODIS years 2001-2025, VIIRS from 2012 where available, additional platforms and recent/NRT service are future goals, not downloaded archives. The handoff distinguishes current capabilities from planned countries/arbitrary geography/global daily-monthly-yearly interfaces.

The handoff package in [gemini-handoff/](gemini-handoff/) contains the actual OpenAPI schema, endpoint contract, sanitized real response examples, scientific limitations and integration requirements. `/api/calendar`, `/api/trends` and `/api/anomalies` return **monthly** records, including partial boundary-month aggregates. Daily aggregates are available in cached explorer `/api/explorer/view`; `/api/comparison` returns daily shared sensor-cell counts. Do not invent daily regional totals from monthly records.

## Public reads and administrator operations

Public GET routes: `/api/health`, `/api/regions`, `/api/calendar`, `/api/trends`, `/api/anomalies`, `/api/hotspots`, `/api/quality`, `/api/comparison`, `/api/methodology`, `/api/export`, `/api/explorer/availability`, `/api/explorer/cached`, `/api/explorer/view`, `/api/explorer/export`. None triggers NASA requests.

Explorer availability serves only the last cached availability record, which may be stale; without it the endpoint returns 503. Cached dataset discovery returns up to 20 datasets. Explorer view/export require an existing dataset identifier, independent of the regional processed store. View supports bounded `limit`/`offset` pagination. `truncated` means records remain after `offset + returned records`; aggregates cover the full filtered dataset.

HTTP download/refresh operations are **disabled by default**. All explorer POST operations (`/load`, `/availability/refresh`, `/cleanup`) require both `EXPLORER_HTTP_INGEST_ENABLED=true` and a valid server-only `EXPLORER_ADMIN_TOKEN` sent as a bearer token. Disabled/missing/incorrect authorization returns 403. These operations are for private administration, not the public frontend. The NASA helper additionally requires the private server `FIRMS_MAP_KEY`. Default public deployments need neither secret.

## Private import and processing

Use separately supplied original NASA CSV files with explicit source provenance:

```powershell
.\.venv\Scripts\python.exe -m pipeline.ingest import --source MODIS_SP --start 2023-09-01 --end 2023-09-05 --bbox '112,-3,114,-1' path/to/modis.csv
.\.venv\Scripts\python.exe -m pipeline.ingest import --source VIIRS_SNPP_SP --start 2023-09-01 --end 2023-09-05 --bbox '112,-3,114,-1' path/to/viirs.csv
.\.venv\Scripts\python.exe -m pipeline.validate
```

Declare start/end/bbox together only when operator knowledge establishes complete extraction for the interval and area; otherwise omit all three and coverage stays unknown. No completeness is inferred from detection dates. Original source files are not rewritten. Registered files have SHA-256 provenance; generation reports contain rejections and duplicate counts. Rebuild after imports. Mixed-version files cannot prove per-collection completeness.

Private `python -m pipeline.ingest download` remains available when an operator deliberately supplies a key, source, dates and bbox. It performs NASA network requests and is not a frontend startup step. No such download is needed to serve existing data. Sources include standard MODIS and VIIRS SNPP/NOAA20/NOAA21; near-real-time streams are separate explorer products, never silent replacements.

## Resource limits and retention

| Server setting | Default |
| --- | --- |
| `FIRE_MAX_FILE_BYTES` | 67,108,864 bytes per input/NASA response |
| `FIRE_MAX_OBSERVATIONS` | 1,000,000 input/cumulative registered or load rows; explorer export cap |
| `FIRE_MAX_CACHE_BYTES` | 1,073,741,824 bytes in explorer cache |
| `FIRE_CACHE_RETENTION_DAYS` | 7 days, applied only on explicit cleanup |

Limits are positive integers validated at startup. Cache writes beyond budgets return 413. No automatic migration or startup eviction removes valid datasets. Explicit private cleanup: `python -m pipeline.cache`, or authorized POST `/api/explorer/cleanup`. Cleanup expires UUID-named explorer generations by directory modification age and associated pointers; it preserves availability metadata, original raw inputs and processed historical generations. This is a deletion operation: schedule deliberately. No cleanup was performed to prepare the handoff.

HTTP loads accept at most four distinct products and up to seven inclusive days when bbox area exceeds 10,000 square degrees, otherwise 31 days. NASA chunks are at most five days. Matching selection metadata is reused for an hour; existing datasets remain readable until explicitly removed. Failed staging/generations are cleaned safely. OS locks coordinate readers/writers; contention returns 409. Each worker allows four DuckDB connections, each limited to 256 MiB memory, two threads and 256 MiB spill. Container quotas must account for worker count. Raw/private processed storage has separate operator retention.

## Scientific limits

Observations are satellite hotspot detections, not wildfire incidents or burned area. MODIS/VIIRS sources, native collections, confidence policies and processing streams remain distinct. Regional cells use a 1 km EPSG:32749 grid for the two Kalimantan study rectangles. Explorer cells are a 0.1-degree geographic display grid with varying area; the two grids are not interchangeable.

Available regional metrics are detections, occupied_cells, and daily_cell_sum. Native confidence thresholds are MODIS all / >=30 / >=80 and VIIRS all / n-or-h / h. FRP is pixel-integrated MW and `min_frp` is a row filter. Missing values remain null; zero is justified by complete imported coverage. Coverage represents file completeness, not cloud-free or overpass exposure. Partial calendar months are ineligible for monthly anomalies. Baselines require at least three matching complete prior same-calendar months with comparable source/collection; calibrated harmonization and forecasting remain disabled. Zero-detection extracts without a collection cannot supply a collection-specific baseline.

## Verification and repository hygiene

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp .tools/local-tests
```

Tests use isolated synthetic fixtures. To include the existing loopback live-server integration test, run a server on port 8000 and set `FIRE_LIVE_TEST=1` before pytest. Live integration reads existing processed data; it is not a NASA download test. The last dataset-specific smoke test expects the registered five-day September 2023 study extract, so fresh clones require separately provisioned data for that test.

Git exclusions cover `.env`, private/generated data including `data/explorer/`, virtual environments, local test directories, logs and coordination files. Never add secrets or data with force. The source export supplied for this handoff has no `.git` directory; tracked/staged state cannot be certified without the actual repository. The sanitized ZIP contains documents only, with no data files, environments or Git history.

See [deployment](docs/deployment.md), [handoff verification](docs/gemini-handoff-verification.md), and [scientific methodology](docs/methodology.md).

## Global scientific expansion assessment

The earlier global-data prompt has now been reconciled with the frontend handoff. See [requirements](docs/GLOBAL_DATA_REQUIREMENTS.md), [NASA/mirror assessment](docs/NASA_GLOBAL_SOURCE_ASSESSMENT.md), [architecture/module audit](docs/GLOBAL_ARCHITECTURE.md), [phased ingestion plan](docs/GLOBAL_INGESTION_PLAN.md), [proposed API - not implemented](docs/GLOBAL_API_PROPOSAL.md), and [measured pilot validation](docs/GLOBAL_PILOT_VALIDATION.md).

An additive `experiments/global_pilot.py` proves offline, bounded CSV-to-partitioned-Parquet ingestion using existing real local NRT extracts; it is not imported by FastAPI and changes none of the regional scientific algorithms. It does not download data or establish full historical/mirror completeness. Private pilot outputs remain under ignored data/global_pilot and are excluded from the Gemini archive. Global catalog/grids/country/yearly endpoints and archive backfill still require the documented gates before production use.
