# Backend validation record ? November 14, 2026

Backend-only scope. No frontend created.

## Executed results

- 45 pytest tests passed in 8.43 seconds. One Starlette HTTPX TestClient deprecation warning; no failures.
- Real pipeline: 183 MODIS + 806 VIIRS = 989 accepted observations; zero rejected, flagged or duplicate rows.
- September MODIS version 61.03: 131 distinct cells, 156 summed daily cells.
- September VIIRS version 2: 327 distinct cells, 469 summed daily cells.
- Both sources show 5/30 imported days, partial coverage, and unavailable baseline/anomaly. Unimported months remain null.
- Temporary Uvicorn server: health and OpenAPI HTTP 200; server terminated after verification.
- NASA read-only key-status endpoint: HTTP 200 with transaction metadata. Live archive downloads were not exercised.

## Stage assessment

| Stage | Main files | Actual validation | Limitations / next action |
| --- | --- | --- | --- |
| Foundation | backend/app/main.py, schemas, requirements, .gitignore | health and live HTTP passed | Git unavailable in shell; no commits |
| Ingestion | pipeline/ingest.py | real imports, duplicate protection, retries and chunk tests passed | live archive download remains untested |
| Cleaning | pipeline/clean.py, validate.py | invalid dates/coordinates/confidence, duplicates, empty/malformed files, checksum and repeatability tests passed | regional in-memory processing; large-scale streaming remains future work |
| Spatial | spatial.py, aggregate.py | grid origin/domain and aggregation tests passed | UTM 49S and rectangular study boundaries only |
| History | services/analytics.py, harmonize.py | median, zero baseline, complete historical API fixture, partial/missing month tests passed | production sample contains five days only |
| Harmonization | pipeline/harmonize.py | insufficient-history and held-out tests passed | exploratory candidate; no validated production model, spatial stability review outstanding |
| API | routers/api.py, database/repository.py | required routes, pagination, bbox, invalid selections and CSV passed | public deployment requires origin/auth/rate-limit decisions |
| Quality/export | quality, methodology, export endpoints | HTTP and export assertions passed | extraction completeness does not measure satellite observation opportunity |
| Integration | tests and real sample run | 45 tests and real-data API checks passed | frontend excluded by owner |
| Deployment | Dockerfile, docs/deployment.md, postgis.sql | files prepared | Docker and PostGIS NOT executed; no public deployment |

Existing scripts and .env were preserved. Synthetic observations are isolated to tests. Science assumptions: nominal 1 km grid, source-specific confidence thresholds, same-source/version historical medians, operator-declared import completeness. No calibrated equivalence or forecasting is claimed.

Next: import complete 2023 regional archives, then comparable prior years; independently evaluate exposure, seasonal and subregion stability before enabling calibrated results.
