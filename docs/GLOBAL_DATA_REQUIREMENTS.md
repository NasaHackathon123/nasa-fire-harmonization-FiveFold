# Global scientific data requirements

Status: assessed 2026-11-15; product requirements, not a claim of archive ingestion. The supplied prompt preceded the final frontend/global clarification. Accordingly preserve the current backend and treat the six-file Gemini package as a current API snapshot plus future capability requirements. This stage adds only an isolated offline ingestion experiment, its tests and research documents.

## Scope and scientific boundaries

Target users are scientists/researchers, climate/environment analysts, firefighters, emergency-response professionals and public agencies. The application is a global observation explorer, not a validated emergency dispatch, evacuation or tactical decision system. Satellite hotspot detections are not verified incidents; no burned area is calculated from counts. No observations are fabricated, no confidence scales are equated, no calibrated harmonization is enabled, and recent detections are not confirmed emergency alerts.

Initial archive target: MODIS 2001-2025 complete calendar-year requested scope, retaining earlier available records separately; VIIRS S-NPP 2012-2025 with partial mission-start year explicitly labeled; NOAA-20/NOAA-21 only their actual product availability. A target year is not a completeness assertion. Keep platform/collection/stream separate and show changes in sensor fleet and overpass timing. 2026 is year-to-date, never a completed annual record, and source-specific SP/NRT/RT/URT availability differs.

A separate rolling recent dataset must expose acquisition timestamps, source ingestion time, upstream observation watermark, processing version/stream, freshness and quality. Do not label download time as observation time or infer service freshness from a single newest detection.

## Coverage policy and acceptance

Maintain distinct layers: (1) upstream product temporal availability, (2) successful extraction/ingestion extent and file completeness, (3) data quality/rejection/gap ledger, (4) actual observation opportunity if supplied by authoritative ancillary/granule products. Hotspot CSVs alone do not establish clear-sky or overpass exposure. Store coverage intervals independently of observations, including empty authoritative extracts, rejected periods and known outages. No detected rows does not establish a complete zero.

Completeness keys include exact product/platform, native collection, stream, spatial request/mask, UTC interval, source inventory revision and validation method. Mixed-version files do not assign collection-specific complete dates. Unknown collection or provenance cannot support comparable-history baselines. Existing legacy policy remains unchanged. In the offline pilot coverage is unknown, even when all local bytes/rows pass validation.

Accept a historical source/date/area partition only after checksums/byte counts, strict schema/coordinate/time/source checks, original-versus-normalized row comparison, retry/idempotency validation, and independent source inventory/request verification. Numerical row equivalence is necessary but not upstream completeness. Mission outages remain unavailable exposure periods and are not filled with synthetic zeros. Bounds min/max are not evidence that all intervening dates are complete.

SP and recent streams retain immutable originals. Publish explicit revisioned supersession intervals after SP validation rather than silently mutating NRT rows. RT/URT appearing through an NRT-family endpoint retain native row version and true provisional identity. No nearest-neighbor cross-stream deletion or calibrated sensor merging.

## Required global functionality

- Actual global availability/catalog with sources, collection/stream, acquisition range, ingestion range, spatial extent, gap/quality status and revision.
- Versioned country/region geometries and arbitrary bbox filtering, with offshore/border/dateline/polar rules.
- Native source/platform/confidence/FRP/date filters, bounded observation paging, and counts/tiles whose scope is explicit.
- Scientifically defined UTC daily/monthly/yearly summaries and separate sensor comparisons; yearly occupied cells require a union, not the sum of monthly counts.
- Global equal-area metric only under a new accepted method/version; current regional 1 km and geographic display grids remain unchanged and not interchangeable.
- Reproducible scientific exports tied to immutable revision, query, provenance and coverage; asynchronous bounded jobs only if size requires them.
- Restartable private ingestion with quotas, secret redaction, byte/row/storage limits, transactional publication, audit history, staged-file cleanup and supervised scheduling.

## Preserved implementation and gaps

Existing two-region monthly API, raw source files, native cleaner, confidence policies, security gates, CORS configuration and current OpenAPI remain intact. Current cached global observations cover only limited selected periods. The prior five-day regional sample is not a worldwide dataset. No current endpoint supplies country catalogs, unrestricted historical global queries or global yearly statistics. See GLOBAL_ARCHITECTURE.md module audit and GLOBAL_API_PROPOSAL.md for separate planned contracts.

## Delivery gates

1. Source/coverage review documented with dated official references and mirror discrepancy checks.
2. Controlled offline pilot and original-source row equivalence pass; clearly document unavailable SP, mirror and exposure evidence.
3. Independent bounded NASA/mirror comparison and a multi-season/multi-product scale pilot before committing to global storage/grids or publishing completeness claims.
4. Explicit user approval before any multi-year global transfer; production frontend/API features enable only after their corresponding data and endpoint acceptance tests.

No historical bulk download, public deployment, frontend creation or GitHub push is part of this work.
