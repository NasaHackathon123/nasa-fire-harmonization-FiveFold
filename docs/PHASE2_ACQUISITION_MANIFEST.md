# Phase2 exact acquisition manifest - approval required

Manifest: **PHASE2-2026-11-15-v1**. Status: **not approved; zero external requests made**. Machine-readable specification: PHASE2_ACQUISITION_MANIFEST.json. SHA-256: `7ce2a1c5f9c18306a5190aaef92d63468fb43907eecdf3d96a60ee24eebdeb4e`.

## Requested authorization scope

Approve only the listed fixed source/date/bbox cases and allowlisted metadata/mirror objects, with bounded methods/body sizes and no automatic redirects/retries. Approval does not authorize new dates, geographic extents, product substitutions, full-year objects, a global archive backfill, backend/API/frontend/handoff changes or deployment.

### Official NASA observations

All requests are one inclusive UTC day via the existing official Area CSV API. Canonical credential-redacted URL pattern: `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_MAP_KEY}/{SOURCE}/{west,south,east,north}/1/{YYYY-MM-DD}`. Each exact expanded redacted template is listed in JSON. No network request has confirmed current availability. Cached bounds only informed selection; fresh approved metadata must include each exact source/date or that case is skipped without substitution.

| Case | Exact source | UTC day | Bbox west,south,east,north | Selection |
| --- | --- | --- | --- | --- |
| NASA-01 | MODIS_SP | 2023-09-01 | [-65, -15, -55, -5] | amazon |
| NASA-02 | MODIS_SP | 2023-09-01 | [20, -25, 35, -10] | southern-africa |
| NASA-03 | VIIRS_SNPP_SP | 2023-09-01 | [-65, -15, -55, -5] | amazon |
| NASA-04 | VIIRS_SNPP_SP | 2023-09-01 | [20, -25, 35, -10] | southern-africa |
| NASA-05 | VIIRS_NOAA20_SP | 2023-09-01 | [-65, -15, -55, -5] | amazon |
| NASA-06 | VIIRS_NOAA20_SP | 2023-09-01 | [20, -25, 35, -10] | southern-africa |
| NASA-07 | VIIRS_NOAA21_SP | 2023-09-01 | [-65, -15, -55, -5] | amazon |
| NASA-08 | VIIRS_NOAA21_SP | 2023-09-01 | [20, -25, 35, -10] | southern-africa |
| NASA-09 | VIIRS_NOAA21_SP | 2023-03-15 | [-65, -15, -55, -5] | amazon |
| NASA-10 | MODIS_NRT | 2026-11-13 | [115, -35, 145, -15] | australia |
| NASA-11 | MODIS_NRT | 2026-11-13 | [-125, 30, -110, 50] | western-north-america |
| NASA-12 | VIIRS_NOAA20_NRT | 2026-11-13 | [115, -35, 145, -15] | australia |
| NASA-13 | VIIRS_NOAA20_NRT | 2026-11-13 | [-125, 30, -110, 50] | western-north-america |
| NASA-14 | VIIRS_NOAA21_NRT | 2026-11-13 | [115, -35, 145, -15] | australia |
| NASA-15 | VIIRS_NOAA21_NRT | 2026-11-13 | [-125, 30, -110, 50] | western-north-america |
| NASA-16 | MODIS_SP | 2023-09-01 | [90, 55, 120, 70] | boreal-asia |
| NASA-17 | VIIRS_SNPP_SP | 2023-09-01 | [90, 55, 120, 70] | boreal-asia |
| NASA-18 | MODIS_SP | 2023-09-01 | [170, 50, 180, 70] | dateline-east |
| NASA-19 | MODIS_SP | 2023-09-01 | [-180, 50, -170, 70] | dateline-west |
| NASA-20 | VIIRS_NOAA21_SP | 2023-09-01 | [170, 50, 180, 70] | dateline-east |
| NASA-21 | VIIRS_NOAA21_SP | 2023-09-01 | [-180, 50, -170, 70] | dateline-west |
| NASA-22 | VIIRS_NOAA20_NRT | 2026-11-13 | [170, 50, 180, 70] | dateline-east |
| NASA-23 | VIIRS_NOAA20_NRT | 2026-11-13 | [-180, 50, -170, 70] | dateline-west |
| NASA-24 | VIIRS_SNPP_SP | 2022-08-01 | [20, -25, 35, -10] | southern-africa |

Rationale: same-day SP cross-platform comparisons in South America/Africa; explicit2023 NOAA-21 earlier-history checks; recent MODIS/NOAA20/NOAA21 in Australia/North America; higher-latitude SP; split dateline SP/recent queries; and an S-NPP known-outage negative control. Dateline logical bbox is[170,50,-170,70], represented by[170,50,180,70] and[-180,50,-170,70]. Neither no rows nor both sides matching empty proves no fire or nonempty dateline correctness. No S-NPP NRT request after its documented cessation is proposed.

### NASA metadata -3 requests maximum

One source availability GET plus two key-status GETs (before/after). Exact credential-redacted templates and256KiB response caps are in JSON. MAP_KEY values remain server-side. Absent/invalid credentials stop NASA work without disclosing values. Request count and transaction accounting differ; stop if headroom is unsafe. No admin API endpoint or administrator token is needed.

### Candidate mirror -38 requests maximum

Anonymous public base: `https://data.source.coop/portolan-mirrors/firms-catalog/`.

-3 metadata GETs: `catalog.json`, `detections/collection.json`, `detections/README.md`;256KiB each.
-3 HEADs: `detections/year=2022/detections.parquet`, `detections/year=2023/detections.parquet`, `detections/year=2026/detections.parquet`.
-Up to32 explicit bounded Range GETs total across those three objects; at most2MiB each/64MiB total. Footer and row-group reads count toward the same cap. Capture/pin ETag where available. No whole-year/full-object download.

These are exact allowlisted object URLs, not verified current objects.404/changed paths/redirects do not authorize searching alternative locations. Refuse full-object200 responses to Range requests; changed ETags stop an object. If field/row-group reads cannot complete inside the cap, mark those comparisons unverified and propose a revised manifest. No unconstrained remote DuckDB scans/automatic HTTP extension downloads.

## Request, size and local-resource ceilings

| Category | Expected/planned | Hard ceiling |
| --- | --- | --- |
| NASA observations |24 one-day cases; availability may cause skips |24 requests;2MiB/response;48MiB total |
| NASA metadata |3 |3;256KiB/body |
| Mirror metadata |3 |3;256KiB/body |
| Mirror HEAD |3 |3; no response bodies |
| Mirror data ranges |Adaptive plan, at most32 |32;2MiB/body;64MiB total |
| All external requests |Up to65 |65; no automatic retries/redirects |
| NASA estimated observation transfer |0.25-8MiB |Planning estimate, not a remote measurement |
| Mirror estimated transfer |8-32MiB |Planning estimate;64MiB data cap |
| Total external body transfer |Unknown until approved execution |128MiB cumulative, including failures/partial bodies |
| New local phase2 files |Sources, comparison evidence, derivatives |512MiB; unique run directory; original prior files preserved |
| Ingestion |5000-row batches |1million scanned/100000 output rows per controlled job |
| DuckDB |2threads |256MiB configured analytical memory; measure actual whole-process peak separately |
| Acquisition elapsed time |Bounded sequential work |20minutes, then stop/defer unissued requests |

Estimates are deliberately uncertain; bounds, request counters and measured bytes govern execution. Request-body caps/elapsed time may end a case unverified rather than permitting an unapproved extension.

## Validation and go/no-go criteria

Record immutable successful original response bytes/checksums, credential-free request identities, fresh availability snapshot, response/retrieval clocks, safe HTTP status/ETag/Last-Modified, actual acquisition timestamps/versions/streams and quality/rejection reasons. Compare row multisets and each native field, including duplicate multiplicity, nulls and precision. Separate remote publication lag/missing fields/version differences from normalization defects; never fill gaps or merge SP/recent silently.

Measure normalization/readback throughput, wall/CPU time, peak working set, source/output/temp byte totals, and cold-versus-warm limitations. Do not relabel prior Phase1 results as new official/mirror evidence. No-go for global scale if source identity/native parity/coverage/stream separation is unresolved; conditional go may authorize another bounded evidence-gathering pilot, never historical backfill by implication.

Your explicit approval of this exact manifest is required before **any** external request, including metadata or mirror HEAD/range calls. This gate comes directly from your Phase2 approval-control instruction; no external request was made to prepare it.
