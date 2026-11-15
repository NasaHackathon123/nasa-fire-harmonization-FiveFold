# Future global API proposal - NOT IMPLEMENTED

Design proposal only, 2026-11-15. None of the paths below is registered in the application or current openapi.json. The existing 17-operation API remains backward compatible. Gemini must treat missing global functionality as planned/unavailable and must not send requests to these proposed paths until implementation/tests and a new actual schema exist.

## Versioning, scope and common selection

Proposed namespace `/api/global/v1`. Public GETs read published ingested revisions only and never trigger NASA calls. Private ingestion/scheduling stays outside the public read contract. Every response includes dataset_revision, catalog_revision, generated_at, source/collection/stream series keys, requested/effective UTC interval, spatial selection identity, method/version, units, warnings and coverage. Bound query area/time, response bytes and execution time; thresholds are benchmark-gated, not silently inherited from the short-extract endpoint.

Proposed shared query fields: explicit UTC start/end, geometry selector (one of bbox or region_id + boundary_version), exact source/platform/collection/stream, confidence policy and finite nonnegative min_frp. Source/collection defaults must not silently stitch streams/versions. Dateline bbox uses explicit wrap_dateline=true when west>east; otherwise invalid. Latitude is -90..90, longitude -180..180; pole/boundary inclusion policy is versioned. Existing legacy bbox rejection behavior is unchanged.

## Proposed operations

| Proposed operation | Purpose / selection | Proposed response / prerequisites |
| --- | --- | --- |
| GET /api/global/v1/datasets | Discover sources/platforms/collections/streams, spatial extents, ingest readiness and source availability; optional source/stream filters | Catalog series with upstream_available_intervals, ingested_intervals, gaps, quality, source_checked_at and ingestion watermark. No observation records required. theoretical availability != completeness. |
| GET /api/global/v1/regions | Discover country/region IDs, names, hierarchy and supported versions; bounded search/pagination | Boundary catalog with license/provenance, geometry revision, bbox, offshore/border policy; no assumption that current study rectangles are countries. |
| GET /api/global/v1/regions/{region_id}/geometry | Retrieve a bounded/simplified selected geometry by version | GeoJSON/multipolygon with CRS, simplification tolerance and source; exact analytical geometry identity separate from simplified display geometry. |
| GET /api/global/v1/observations | Exact ingested historical/recent row search with common selectors, page_size and revision-bound cursor | Native source observations plus processing/acquisition/provenance fields, coverage, returned, next_cursor and has_more; optional total if computed. Does not fabricate zero data outside coverage. |
| GET /api/global/v1/trends | UTC daily/monthly/yearly buckets, metric=detections/occupied_cells/daily_cell_sum, common selectors and explicit accepted method | Per-source/collection/stream series, null/zero semantics, bucket boundaries/selected_days/import completeness/quality; distinct-cell unions computed at requested resolution. No sum-of-monthly-distinct yearly substitute. |
| GET /api/global/v1/map/cells | Display aggregation for requested bbox/zoom/resolution/time/filters | Cell geometry/id, raw matching counts, exact aggregation method, total scope, truncation/resolution and coverage. Global count not derived from marker sampling. Invalid area/grid method ->422. |
| GET /api/global/v1/map/tiles/{z}/{x}/{y} | Alternative future bounded vector-tile view of the same revision/selection | Map tiles with source-separated counts and an associated metadata contract. Optional alternative to cells, implement only if benchmarks justify it; not a different scientific total. |
| GET /api/global/v1/quality | Selection-scoped import/validation inventory and quality/exposure metadata | Coverage intervals/gaps, input checksums/request identities, rejected/duplicate/flag counts, known platform discontinuities and separately unavailable exposure evidence. Never serialize secret URLs. |
| GET /api/global/v1/comparison | Side-by-side source-specific trends over the same geometry/UTC buckets | Separate uncalibrated series plus comparability warnings and per-source coverage. Do not collapse MODIS/VIIRS into equivalent counts. |
| GET /api/global/v1/recent | Rolling stream snapshot plus bounded native rows | Explicit NRT/RT/URT identity, observation times, source retrieval/check time, expected cadence/staleness, source-specific watermark and quality; not confirmed emergency alerts. Ended missions are not treated as running feeds. |
| POST /api/global/v1/exports | Optional bounded export job for a reproducible already-ingested selection; no NASA fetch | Authenticated/quota-controlled job tied to selection, revision, native/aggregate format, columns, units and coverage; large work returns 202 with job ID. Not today's explorer ingestion admin flow. |
| GET /api/global/v1/exports/{job_id} | Check export status and obtain authorized output metadata | Queued/running/completed/failed/expired, bytes/checksum, expiry, selection/revision and authorized download reference. Access ownership enforced; never expose storage secrets or unrestricted worker paths. |

This is a path proposal to guide backend review, not authorization for frontend code to assume any route works. Keep current/future adapters separate. A smaller first release may implement catalog + observations + trends + quality + existing-style CSV export before adding tiles or export jobs.

## Proposed response semantics

```typescript
type Coverage = {
  source: string; platform: string; collection: string | null;
  processing_stream: string; start: string; end: string;
  import_status: 'complete' | 'partial' | 'unknown' | 'unavailable';
  exposure_status: 'measured' | 'unmeasured';
  imported_intervals: {start:string;end:string}[];
  missing_intervals: {start:string;end:string;reason:string}[];
  basis: string; catalog_revision: string;
};
type Bucket = {
  start: string; end_exclusive: string; resolution: 'day'|'month'|'year';
  selected_interval_partial: boolean; metric: string; method: string;
  value: number | null; units: string; coverage: Coverage;
};
type ObservationPage<T> = {
  dataset_revision: string; records: T[]; returned: number;
  next_cursor: string | null; has_more: boolean; total: number | null;
  coverage: Coverage[]; warnings: string[];
};
```

These are proposed types, not production responses. Preserve native observation columns including acquisition date/time/UTC timestamp, satellite/source, instrument, exact row version, collection, native confidence/type, FRP/units, scan/track/daynight, optional native fire type, raw-source checksum, stable record identity and quality flags. Null means unknown/unavailable; known empty imported buckets may be zero but exposure remains separately unmeasured. Do not label combined raw source totals harmonized.

Cursor identity includes immutable dataset revision, filter hash and ordering key with a unique deterministic row tie-break. Detect expired/changed revisions rather than silently switching data mid-pagination. Bound markers (initial design max5000/page) and any cell/byte payload; metric totals come from exact aggregate queries independently of marker limits. Query timeouts/size constraints return explicit bounded errors, not silent thinning.

## Errors and security acceptance

Proposed errors retain existing detail compatibility and can add documented machine-readable code/request_id in this new namespace. Cover invalid selectors/method/geometry (422), unavailable source/region/revision (404), stale cursor/revision or lock (409), bounded request/selection/export limits (413), authentication/authorization (401/403 for privileged work), rate limits (429), missing data/capacity (503) and sanitized internal errors (500). A catalog can report unavailable data successfully; a failed query must not be presented as an empty successful zero.

Do not pass FIRMS_MAP_KEY or admin credentials through these APIs. Exports select already-ingested data; no public endpoint triggers remote ingestion. Use explicit origin policy, sensitive-request redaction, per-worker budgets and immutable object references. Country/boundary licensing and redistribution terms are prerequisites. No new authentication promise is made for the current application.

Acceptance before frontend enablement: implemented actual OpenAPI and contract tests, source/geometry/date/stream coverage tests, dateline/polar/border tests, empty/null/zero checks, cursor/revision stability, resource/concurrency tests, native record/aggregate numerical parity, and measured response/latency budgets on representative data. Production historical/anomaly claims require the independent completeness gates in GLOBAL_INGESTION_PLAN.md.
