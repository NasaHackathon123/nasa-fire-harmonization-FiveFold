# Global architecture review and pilot decision

Status: design decision for an isolated pilot, 2026-11-15. Existing FastAPI routes, regional pipeline calculations, raw inputs and processed generations remain unchanged. No global production endpoint is added.

## Simplest initial architecture

Use the existing FastAPI service, a separate single-writer background ingestion command, immutable partitioned Parquet files, DuckDB analytical reads, and a small local job/provenance catalog. Start on durable local storage and adopt S3-compatible immutable object storage for published partitions/backups when deployment needs it. Do not introduce PostGIS, Spark, Kafka or a distributed scheduler before measured workloads require them. SQLite is sufficient for prototype exact-record deduplication/job coordination on a local worker; object-store publication later needs a conditional manifest update or single publisher, not local file-lock assumptions.

Bronze: immutable checksum-addressed original CSV/granule downloads, request scope and source catalog snapshot, no keys or credential-bearing URLs. Silver: source/stream/collection/year/month/date partitions, sorted spatially within useful time chunks, with latitude/longitude bounding statistics and ZSTD compression. Keep native confidence/version/platform/type/quality and provenance. Gold: source/collection/stream/region-or-grid/method/confidence daily, monthly and yearly products with explicit completeness metadata. Precompute default policy aggregates only; arbitrary FRP/source combinations fall back to bounded queries.

Parquet starts without geometry extensions for the pilot because existing requirements support ordinary Parquet directly. Add standards-compliant GeoParquet geometry/CRS and bbox covering metadata for interoperability after round-trip tests; ordinary lon/lat Parquet must not be labeled GeoParquet. Prefer 64-256 MiB compacted files and 64K-256K row groups as benchmark starting points, not measured optima. Daily ingestion fragments are compacted into monthly/size-target files to avoid tiny-file explosion. DuckDB can project/filter Parquet and prune by partition/statistics; verify actual EXPLAIN ANALYZE scan bytes and high-latitude/dateline predicates in the production benchmark. [DuckDB Parquet documentation](https://duckdb.org/docs/2.0/data/parquet/overview)

## Spatial accuracy and indexing

Preserve EPSG:32749/1 km legacy results and their study-domain guard. That projection cannot process the world. Existing 0.1-degree explorer cells remain display cells, never area-normalized scientific cells. For a future versioned equal-area metric, evaluate EASE-Grid 2.0: global/temperate EPSG:6933 with explicit polar treatment using EPSG:6931/6932, a nonoverlapping seam policy, documented origin/resolution and geodesic area validation. The final grid/resolution needs scientific acceptance; do not relabel this as the existing common-grid method. [NSIDC EASE guide](https://nsidc.org/data/user-resources/help-center/guide-ease-grids)

H3 is a strong candidate for map search/aggregation, but its cell areas vary and pentagons differ from hexagons; it is not an exact equal-area grid. Avoid adding a new H3 dependency in this pilot. First benchmark lon/lat statistics plus a versioned coarse spatial order/index; adopt H3 or another DGGS only when it improves query/map workloads. A5/PMTiles mirror layers are visualization candidates, not automatically scientifically equivalent gold products. [H3 official cell statistics](https://h3geo.org/docs/core-library/restable/)

Country/region selection needs a licensed versioned boundary source, border/coast/offshore and disputed-area policy, point-on-boundary ownership, geometry validity checks and dateline-aware predicates. Country archives alone can miss offshore detections and are not a complete global source. Do not substitute study rectangles for countries. Prepared geometry/bbox filtering with batch spatial joins is sufficient initially; introduce PostGIS when repeated concurrent arbitrary polygon queries or editing/versioning workloads are proven to exceed file-based service targets.

Map overview aggregates or tiles must be computed from all matching observations with explicit resolution/method/count provenance. Bounded marker pages are only display samples. Do not send millions of raw points to a browser or infer totals from visible markers. PMTiles suits precomputed immutable layers; dynamic confidence/time/source filters need backend aggregates or verified partition-derived tiles. Cache keys include dataset revision, geometry, time, source, stream, method and policy.

## Audit of existing modules

| Component | Reuse | Required extension / limitation |
| --- | --- | --- |
| pipeline/config.py | Source constants, startup/env precedence and existing region definitions | Add a separate versioned source-availability registry; do not change existing region IDs/defaults. |
| pipeline/ingest.py | Server-only credentials, 5-day NASA windows, retry/input limits, checksum provenance | Current importer has a whole-file Pandas read, aggregate registered-row cap and local manifest. Global job planner must stream, partition, checkpoint, throttle transactions and separate coverage from detected dates. |
| pipeline/clean.py | Native sensor checks, UTC parsing, confidence preservation, flags | Reuse in bounded batches. Register version allowlists/row-level RT/URT/NRT classification separately; it currently broadly accepts supplied NRT versions. |
| pipeline/spatial.py | Legacy EPSG:32749 results and inclusive regional bbox semantics | Explicit longitude 108..114, latitude -80..0 guard; no worldwide use. Add a new versioned global method, not a changed legacy grid. |
| pipeline/aggregate.py | Sensor/source/version grouping and exact distinct-cell definitions | Fixed regions, in-memory concatenation, whole-group distinct sets. Partition-aware daily/month/year reductions must compute distinct unions, not sums of monthly occupied_cells. |
| pipeline/validate.py | Immutable generation publication, CURRENT atomic switch, raw integrity checks | All accepted/rejected frames are accumulated and concatenated; unsuitable for multi-decade archives. Extend via an independent job/partition builder, retaining legacy behavior. |
| repository.py | Parameterized DuckDB, bounded observation pagination, exact boundary-month reconstruction | Fixed study regions/local single generation; add new global repository adapter and immutable revision manifests. Coverage arrays and recursive baseline work need interval catalogs/caching at global scale. |
| routers/api.py | Existing monthly contract, data-unavailable behavior, native provenance | Preserve backward compatibility. New global daily/yearly and geometry APIs require new tested contracts. |
| routers/explorer.py | Read-only cached API, bounded queries, HTTP admin gate and budgets | Short fixed-bbox extracts, in-memory load concatenation and geographic display grid; no global archive/country/date-at-read API. Source_NRT can include RT/URT native versions; current stream label is broad and native version must remain visible. |
| tests/data contracts | Existing 104 regression/integration cases and real-source fixtures | Add separate pilot tests and later global catalog/dateline/pole/country/revision tests; do not relax prior expectations. |

## Review outcome before pilot implementation

Proceed only with an additive offline CSV-to-partitioned-Parquet experiment using the existing local global NRT cache, one UTC date and multiple continent/latitude boxes. Reuse existing cleaner unchanged; implement file/row budgets, disk-backed exact-record deduplication, immutable checksum-keyed output and parameterized query validation. Do not adopt a new scientific grid or expose an API. This tests ingestion mechanics, not historical archive completeness, equal-area metrics or production scalability. The same daily job primitive can later operate repeatedly under an approved archive planner.

NRT-to-SP policy: retain original stream records and publish a new dataset revision with explicit verified date/source coverage preference. Never nearest-neighbor merge observations or assume geolocation-identical duplicates. RT/URT are provisional and preserve row version; SP reconciliation records which intervals were superseded, retaining audit history and reproducible old revisions.

Hardware/time/storage estimates are reported after the measured pilot in GLOBAL_PILOT_VALIDATION.md; no unmeasured full-archive throughput claim is made.
