# Controlled global pilot validation

Run 2026-11-15. **Offline ingestion proof passed; historical/global source completeness is not certified.** This is an additive experiment, not a change to the Python FastAPI application, existing scientific calculations or endpoints.

## Scope and source identity

Reused three original CSV extracts already present in the local worldwide explorer cache downloaded_at 2026-11-14T09:25:51.537242+00:00. Selected UTC date 2026-11-08 and six continent/latitude boxes. No new NASA or mirror observations were downloaded, no keys used, and network methods were blocked in the runner. Local metadata asserts the source identity; independent remote NASA/mirror provenance/completeness verification remains a separate gate.

| Pilot box | west,south,east,north | Selected observations |
| --- | --- | --- |
| western-north-america | [-125, 30, -110, 50] | 272 |
| amazon | [-65, -15, -55, -5] | 338 |
| southern-africa | [20, -25, 35, -10] | 9,018 |
| europe | [0, 45, 30, 60] | 99 |
| australia | [115, -35, 145, -15] | 24,267 |
| boreal-asia | [90, 55, 120, 70] | 50 |

These are rectangular samples, not complete countries/continents. They do not include poles/dateline crossing and are not a seasonally representative historical sample. All six have real selected observations; no sample point or time series was fabricated. Selected latitude coverage spans about -35 to +60 degrees; longitude ranges and exact boxes are specified above.

| Exact source | Native row version | Selected rows | Row stream |
| --- | --- | --- | --- |
| MODIS_NRT | 6.1NRT | 2,460 | near-real-time |
| VIIRS_NOAA20_NRT | 2.0NRT | 15,448 | near-real-time |
| VIIRS_NOAA21_NRT | 2.0NRT | 16,136 | near-real-time |

## Implementation and reproducibility

`experiments/global_pilot.py` contains a bounded, local-only daily ingestion primitive. It calls the existing cleaner unchanged on batches, uses a SQLite exact-record identity set across chunks/files, writes source/stream/collection/date partitions with ZSTD, and atomically publishes an immutable checksum-keyed job manifest. Exact native versions remain in rows; their hashes are safe partition path keys only. No new global equal-area cell or regional scientific metric is assigned. All pilot coverage stays unknown. Original files remain read-only and input checksums are compared before/after.

The CLI accepts explicit local inputs/day/named boxes/output. The measurement runner is `.tools/run_global_pilot.py` (ignored local artifact); a private reproduction chooses the same existing source files/date/boxes and runs the module or runner. Files in `data/global_pilot/` are private generated data excluded from Git/ZIP. SHA-256 hashes, source groups, bounds, limits and actual metrics are in `GLOBAL_PILOT_METRICS.json`; it contains no credential values or sensitive local paths. Fresh clones do not include the original extracts and cannot reproduce the real-data benchmark without separately authorized input provisioning.

The same bounded daily primitive can be scheduled over approved full archive windows later. It is not a production network downloader/catalog or multi-year ingestion job. Restart retries the daily job from immutable input after interrupted staging, while completed jobs are checksum-verified/idempotent. It does not implement per-file byte-offset resume or SP supersession publication.

## Measured results

Hardware/software: Windows, Python 3.12.10, DuckDB 2.0.0, 12 logical CPUs (DuckDB limited to2 threads,256MiB query memory). Local disk characteristics, cold OS cache and hardware contention were not controlled.

| Measurement | Observed |
| --- | --- |
| Original CSV bytes scanned | 51,172,978 |
| Native rows scanned | 610,807 |
| Target UTC-day rows before validation/spatial selection | 131,462 |
| Rejected target-day rows | 0 |
| Selected normalized observations | 34,044 |
| Exact duplicates in this real sample | 0 (dedup tested separately with synthetic duplicates) |
| Parquet files / bytes | 27 / 2,563,505 |
| First measured ingestion | 5.4368 s |
| Repeat/checksum-idempotent job | 0.0912 s |
| Independent native CSV baseline query | 0.8934 s |
| First measured Parquet aggregate | 0.0181 s |
| Six warm aggregate queries, median | 15.96 ms |
| Process peak working set | 182.91 MiB |

Peak working set was read from Windows process memory counters and includes Python/imported libraries, the independent raw-source baseline query, row-multiset comparison and warm queries. It is not peak ingestion-only RAM or a production memory bound. First-measured is not a controlled cold-cache benchmark. The original-CSV query scans more input rows than the selected Parquet job; these timings are not a fair raw-vs-Parquet speedup claim. Twenty-seven small files are a proof artifact, not the final compaction layout.

## Numerical and integrity validation

An independent DuckDB query reads original CSVs directly, filters the date and boxes and deduplicates exact native rows. Its entire selected row multiset equals the Parquet readback across source, coordinates, UTC timestamp, satellite, instrument, native version, native confidence and valid/nullable FRP. This is stronger than matching just totals. Unique native-record IDs equal output row count; original input checksums match. Per-source count/FRP aggregates match the same preserved records. Repeat import returns the identical manifest. Region counts above are exact for the selected extracts/filters.

CSV/Parquet boundary comparisons use inclusive geographic limits; UTC query sessions are explicitly configured. All output rows remain in the requested day/boxes. No projection outside UTM49S was attempted: the experiment deliberately avoids the regional grid and preserves legacy methods.

Independent upstream source completeness, full-year calendar coverage, SP historical parity, mirror parity, remote HTTP range behavior, equal-area grid areas, country-border semantics, polar/dateline filtering, multi-season throughput and operational NRT freshness were **not verified**. The only completeness demonstrated is that the selected validated local source rows survived the offline transformation. No absent source-day is filled with invented observations or asserted clear-sky zero activity.

## Storage, time, memory and cost scenarios

Measured raw input density: 83.78 bytes/scanned row; pilot normalized Parquet: 75.30 bytes/selected row. Small-file metadata, chosen region/source mix and extra derived/provenance fields affect compression. Use the following hypothetical row counts only for sensitivity; they are not a measured NASA archive row inventory or the mirror publisher's total.

Assume raw density transfers, Parquet density transfers,20% extra Parquet-equivalent aggregates, two complete storage copies, decimal GB, and an illustrative $0.03/GB-month storage rate (an assumption, not a provider quote). Excludes request fees, egress, compute, operations, disk slack, logs and additional retained revisions. See the deployment provider's current region-specific pricing before purchase. [AWS official pricing categories](https://aws.amazon.com/s3/pricing/)

| Hypothetical native rows | Raw GB | Parquet GB | Two-copy modeled GB incl.20% aggregate allowance | Assumed storage/month |
| --- | --- | --- | --- | --- |
| 100,000,000 | 8.38 | 7.53 | 34.83 | $1.04 |
| 500,000,000 | 41.89 | 37.65 | 174.14 | $5.22 |
| 1,000,000,000 | 83.78 | 75.30 | 348.28 | $10.45 |

A simplistic100million scanned-row scaling at this measured row-selection ratio is 14.8 local CPU/wall minutes;1billion is 2.47 hours. This is **not a full-archive ETA**: only 21.5% of scanned rows were cleaned for the target day and 5.6% were written. Global full retention processes/writes many more rows, and network/retries, SP conversion, sorting/compaction, spatial joins, grids and integrity publication are excluded. Do not multiply it into a download plan without a full-retention scale pilot.

Illustrative compute budget at an assumed $0.10/worker-hour is $0.10 times actual provisioned worker hours; the measured local process does not establish cloud vCPU equivalence. An example40worker-hour budget would be $4 before storage/requests/egress, not a forecast that40hours suffices. Public delivery egress can dominate storage and depends on measured traffic. Current evidence supports a bounded prototype, not a production SLA or all-years bill.

## Tests and recommended next gate

Final full suite (existing 104 cases plus 16 new pilot cases) passed: **120 passed, 0 failed, 0 skipped, 1 existing Starlette/httpx warning in 18.74 seconds**. Loopback live integration was enabled and reads existing processed data without NASA requests. Complete output: GLOBAL_TEST_RESULTS.txt. This final run includes the repeat-import byte-budget assertion and all existing live-server integration checks. New isolated-pilot tests cover cross-chunk/file duplicates, source/stream separation, native UTC/coordinate/version retention, zero extracts without invented coverage, malformed/schema/coordinate failures, all resource limits, changed-output integrity detection, failed-write cleanup, concurrent lock rejection and preserving prior complete output. Existing source data and all prior regression tests remain intact.

Proceed to Phase2 of GLOBAL_INGESTION_PLAN.md: separately approved, small official NASA SP/NRT windows compared independently with the mirror, including the NOAA-21 earlier-history discrepancy. Only then run a multi-season full-retention scale/global-grid pilot. No full historical transfer, frontend creation or public deployment has been authorized here.
