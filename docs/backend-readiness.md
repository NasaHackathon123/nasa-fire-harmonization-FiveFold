# Backend remediation readiness — 2026-11-15

Latest verification: [final configuration and pagination correction](final-configuration-correction.md) — 104 tests passed, including live integration. The results below describe the preceding remediation stage.

Scope: targeted backend remediation only. No frontend work or GitHub push. Original NASA CSV inputs and existing processed/cache generations were not rewritten. MODIS and VIIRS remain separate; calibrated harmonization remains disabled. No production observations were invented. Synthetic fixtures exist only in tests.

## Changes by file

| File | Change |
| --- | --- |
| `backend/app/security.py` | HTTP mutation gate: disabled by default; explicit enable flag plus constant-time comparison of a server-only bearer token. Missing, incorrect, and disabled credentials return 403 before NASA/cache activity. |
| `backend/app/routers/explorer.py` | Protect `/load`; cache-only public availability; administrator availability refresh and explicit cleanup; bounded streamed NASA responses, cumulative input-row and disk budgets; atomic metadata/pointer writes; failed generations removed in `finally`; OS mutation lock and shared reader locks; DuckDB filtering and aggregation; bounded marker pagination and export. Existing response structures retained. |
| `pipeline/limits.py` | Configurable input/cache/observation budgets; DuckDB memory 256 MiB, two threads, spill limit 256 MiB per connection; four concurrent connections per worker, with overload returning 503. |
| `pipeline/locking.py` | Nonblocking OS advisory locks released on process exit; protects cache mutations and import/build manifest coordination across workers on a shared local filesystem. |
| `pipeline/ingest.py` | Input byte/row limits before full Pandas parsing; aggregate registered-row budget; serialized atomic manifest changes; streamed downloads; safe interruption errors; temporary download staging removed on failure. Private CLI remains operational. |
| `pipeline/validate.py` | Aggregate build-row/input-byte limits, coordinated locking, and cleanup of failed processed generations; existing CURRENT pointer remains intact until success. |
| `backend/app/database/repository.py` | Bounded DuckDB connection settings; coverage requires exact source, region containment, collection and selected interval. Mixed-version files do not prove completeness for either collection. |
| `backend/app/services/analytics.py` | Evaluate coverage independently for each collection; retain collections filtered down to zero observations; unknown collection cannot generate a collection-specific baseline. Partial-month counts, distinct cells, daily-cell sums and native confidence thresholds retain their definitions. |
| `backend/app/main.py`, `.env.example` | Explicit configurable CORS origins; no wildcard; GET-only browser integration. Server-only settings documented. |
| `pipeline/cache.py` | Private local cache retention CLI, operational with HTTP ingestion disabled. |
| `pipeline/api_artifacts.py` | Reproducibly generate actual app OpenAPI and read-only response captures without NASA downloads. |
| `tests/test_explorer.py`, `tests/test_ingestion.py` | Adapt existing tests to explicit admin authentication and streamed downloads. |
| `tests/test_remediation.py` | Authorization side effects, stale cached availability, byte/row/storage budgets, interrupted download/staging cleanup, retention/migration preservation, OS/thread contention, concurrent reads, pagination and invalid parameters, mixed/separate collection versions, missing/zero extracts, region containment, partial-month policies/metrics, and CORS regression coverage. |

## Public read-only integration

These GET endpoints never initiate NASA downloads or ingest data:

- `/api/health`, `/api/regions`, `/api/methodology`
- `/api/calendar`, `/api/trends`, `/api/anomalies`, `/api/hotspots`, `/api/quality`, `/api/comparison`, `/api/export`
- `/api/explorer/availability`, `/api/explorer/cached`, `/api/explorer/view`, `/api/explorer/export`
- `/openapi.json`, `/docs`, `/redoc` provide API documentation.

Availability returns the last administrator-cached record, including its original `checked_at`; it can be stale. With no cached availability it returns 503. Public requests never refresh it. Data-dependent study endpoints return 503 when processed data is absent. Invalid dataset identifiers return 404. Public reads expose dataset provenance/quality metadata as before.

`/api/hotspots` retains limit 1–5,000 and offset 0–1,000,000. Explorer view adds optional limit 1–10,000 and offset 0–1,000,000; defaults retain the latest 10,000 markers in chronological order. Aggregates cover the entire filtered dataset, independently of pagination. Explorer CSV exports reject more than the configured observation budget with 413 rather than silently truncating. Existing valid cached datasets remain readable regardless of ingestion budgets.

Set `FIRE_CORS_ORIGINS=https://frontend.example,https://staging.example` before server startup. Empty means no cross-origin access. CORS is browser integration configuration; administrator authorization is enforced independently. No administrative token or FIRMS key belongs in browser code.

## Administrator operations and retention

All HTTP POST operations below require **both** `EXPLORER_HTTP_INGEST_ENABLED=true` and `Authorization: Bearer <EXPLORER_ADMIN_TOKEN>`:

- `/api/explorer/availability/refresh`: explicit bounded NASA availability refresh.
- `/api/explorer/load`: bounded NASA dataset download; requires cached availability first.
- `/api/explorer/cleanup`: explicit expiration of explorer generations and associated pointers.

Leave HTTP ingestion disabled for public deployment. Use `python -m pipeline.ingest import ...`, `python -m pipeline.ingest download ...`, and `python -m pipeline.validate` privately. `python -m pipeline.cache` runs local cleanup without enabling HTTP mutations. Do not log NASA URLs: they contain the server-only key. HTTP errors redact network exception details.

Default budgets, read at process startup:

| Setting | Default | Scope |
| --- | --- | --- |
| `FIRE_MAX_FILE_BYTES` | 67,108,864 | Each CSV/input or NASA response |
| `FIRE_MAX_OBSERVATIONS` | 1,000,000 | Input rows per CSV, cumulative explorer load, total registered private-import rows/build, explorer export |
| `FIRE_MAX_CACHE_BYTES` | 1,073,741,824 | Explorer files, including retained raw extracts and metadata; writes rejected before crossing budget |
| `FIRE_CACHE_RETENTION_DAYS` | 7 | Explicit explorer cleanup age based on generation directory modification time |

Startup performs no deletion or format migration. A full cache rejects new writes with 413; cleanup is deliberate, never implicit eviction of valid historical data. Cleanup removes only UUID-named explorer generation directories older than the retention threshold and their pointers. It does not remove original NASA inputs, private raw archives, processed historical generations or availability metadata. Existing caches exceeding a new budget remain readable until an operator performs cleanup. Graceful failures remove new incomplete generations; after a hard process kill, abandoned generations are eligible for explicit retention cleanup.

## Scientific interpretation

Coverage means operator-declared import completeness, not cloud-free coverage or observation opportunity. Completeness for a collection requires a rejected-row-free inventory item containing exactly that collection and a bbox enclosing the reported region. A mixed-collection CSV does not assert which collection covered every day, so it cannot establish complete per-collection coverage. Separate files for a matching collection may contribute disjoint coverage days. Coverage is clipped to the reported interval.

Header-only zero-detection files can assert complete source/region intervals with `version: null`, but do not establish a collection identity or collection-specific historical baseline. Existing version metadata is preserved; none is inferred or fabricated. Missing periods remain null; a completely imported interval with no selected detections reports zero. All three native confidence policies and all three metrics are tested for partial ranges. Partial-month summaries are reconstructed from filtered Parquet observations, and partial calendar months remain ineligible for monthly anomalies.

## Generated handoff artifacts

- `docs/openapi.json`: schema generated directly from `app.openapi()`.
- `docs/api-response-examples.json`: actual GET responses captured from the local processed dataset; no credentials, request Authorization headers or raw filenames are included. These are response examples, not new observations. Error examples use deliberately invalid identifiers.
- `docs/remediation-test-results.txt`: complete final pytest output.

Regenerate schema/examples with `.venv/Scripts/python.exe -m pipeline.api_artifacts`.

## Validation and remaining limits

Final result: **83 passed, 0 failed, 0 skipped, 1 existing deprecation warning in 10.06 seconds**, with `FIRE_LIVE_TEST=1` and `--basetemp .tools/remediation-test-verified -p no:cacheprovider`. Complete output is recorded in `docs/remediation-test-results.txt`. Both registered original NASA inputs were independently checked against their manifest SHA-256 checksums and matched. Full verification enables the live-server integration test against a temporary loopback Uvicorn process and the existing processed data. It does not contact NASA. The default test command skips the live test unless `FIRE_LIVE_TEST=1` and a server is running on `127.0.0.1:8000`.

The initial default pytest run could not access the host temporary directory. All subsequent runs used a workspace-local `--basetemp` and disabled the inaccessible pytest cache. The existing Starlette/httpx deprecation warning remains; dependencies were not upgraded during remediation.

Cache reads use coordinated OS locks (Windows readers can serialize and retry for up to one second); cache mutations and cleanup require exclusive access, returning 409 on contention. Public dataset reads may create a small coordination lock outside the cache; they do not write dataset/cache content or contact NASA. Availability reads do not create a lock. Operational limits remain: per-worker DuckDB limits multiply with worker count; size worker/container memory and disk quotas accordingly. Raw private archives and historical processed generations are intentionally outside automatic explorer retention and require operator storage management. Existing oversized Parquet datasets are preserved; DuckDB may reject expensive reads on memory limits. No load benchmark or live NASA service/credential test was performed. Use a local filesystem supporting OS advisory locks; distributed/object-store locking is not implemented.
