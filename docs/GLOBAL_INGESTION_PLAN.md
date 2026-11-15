# Global ingestion plan and phased acceptance

Status: proposed archive program plus implemented isolated offline pilot. No approved multi-year transfer is assumed. Existing private CLI, backend routes, source files and regional generations remain unchanged.

## Source planning and provenance

Before any network job, privately refresh the source availability catalog, identify exact product/collection/stream, query source outage/quality notes and snapshot requested bounds. Archive requests require the actual source-specific approved transport/authentication. Do not infer satellite start/end from a static full-year UI range. NASA remains authoritative; mirror transport needs a separate matched-window validation gate.

Create a deterministic job key from source/platform/collection/stream, UTC window, geographic request and transform version. Store safe source identity and request scope, byte counts/checksums, upstream identifiers/revisions, retrieval and acquisition clocks, validation results and coverage basis. Never store or log credential-bearing NASA request URLs. Keep original compressed/source files immutable and checksummed; output revisions reference them.

## Ingestion state machine

planned -> fetching -> fetched/checksummed -> validating -> normalized -> independently_verified -> published; failure/cancel states retain safe audit/checkpoints. Download into quota-limited temporary storage; enforce actual streamed bytes and row budgets, retries/Retry-After and transaction accounting before publication. Checksum every completed object; a resumed job must not trust file existence alone. A bounded daily worker can be rerun under a later archive planner; a full scan/ETL of decades in a single DataFrame is forbidden.

Read in bounded record batches. Preserve source/row version/native values and apply existing sensor cleaner where compatible. Strictly validate widths, coordinates, UTC dates/times, platform match and version/stream identity. Write source/stream/collection/date partitions with deterministic record identity. Deduplicate exact native duplicate observations only within the same source/stream identity; keep possible same-location independent detections. Disk-backed dedup state can be partition-scoped; compaction must deduplicate across overlapping fetch windows too. Commit an immutable manifest only after row/count/value checks. Atomically publish local generation or conditionally publish object-store revision from a single writer. A hard-killed staging directory is not a published success; resume/restart it after reconciliation and apply an explicit orphan policy.

NRT/RT/URT stay separate from SP. As an SP interval becomes independently validated, create a new revision with explicit supersession relations/date coverage and preserved old originals. Replacements may change geolocation/attributes; do not deduplicate by rounded space/time or silently overwrite. Outages and source-scope changes remain in coverage history.

## Current offline pilot

`experiments/global_pilot.py` is a separate, non-network module, never imported by FastAPI. It reuses `pipeline.clean.clean` unchanged, batches native CSV rows (default5000), uses disk-backed exact-record deduplication, and publishes checksum-keyed source/row-stream/hashed-collection/year/month/day Parquet partitions with an immutable manifest. Collection hashing is only a safe storage path component: exact native version is retained in every row/manifest.

A bounded invocation accepts local `--input CSV SOURCE` pairs, one `--day`, a JSON file of named `--boxes`, and `--output data/global_pilot`. No NASA key or network client is used. Example argument shape, not a source download:

```text
python -m experiments.global_pilot --input <local-extract.csv> MODIS_NRT --day 2026-11-08 --boxes <named-boxes.json> --output data/global_pilot
```

Outputs are ignored private data, not part of the Gemini ZIP. Current default ceilings: each input64MiB, total1million scanned rows,100000 output rows,512MiB staged output. Output bytes are checked at bounded batch/publication checkpoints, not a filesystem hard quota; SQLite journals and a batch write can transiently exceed that ceiling. Use a filesystem/container quota before production. Restart is whole-job idempotent after a failure, not an intra-file byte-offset checkpoint. Existing complete jobs revalidate output checksums. Successful empty jobs keep unknown coverage, never fabricate complete zero-exposure periods.

This is the same daily/batch normalization primitive suitable for a later approved scheduler, but not a production global downloader, geometry/grid/catalog server or a complete checkpoint/supersession implementation. Archive SP transport, GeoParquet geometry, equal-area metrics, country masks, remote range-query performance and publication on object storage are not yet validated.

## Approval gates and acceptance criteria

| Phase | Dependencies / scope | Acceptance and risks |
| --- | --- | --- |
| 0: source and architecture review | Dated official NASA/NOAA references; mirror schema/coverage claims; unchanged backend audit | Deliver six requested research docs; flag NOAA-21 channel discrepancy, S-NPP cessation, unknown authenticated/current mirror inventory. Complete here. |
| 1: local bounded ingestion proof | Existing genuine local worldwide NRT CSVs, one day, six geographic boxes | Native row multiset parity, strict source/UTC/geography/version, checksum-preserved originals, repeatable output, resource/failure tests, honest unknown coverage and measured local timings. Complete here; not historical SP certification. |
| 2: independent transport/completeness pilot | Separately approved small official NASA SP/NRT extracts and matched mirror windows, including 2023 NOAA-21, offshore/dateline/high-latitude cases | Compare source inventories, original rows and all relevant native fields; verify empty windows, known outage samples, RT/URT handling and SP supersession. Current mirror/live metadata gaps must be closed; no full historical approval implied. |
| 3: scale and spatial-method pilot | Multi-season/multi-product representative bounded samples, one accepted global equal-area method and versioned boundaries | Measure scan bytes/RSS/ETL/query/country/tiles and null/zero coverage, validate seam/poles/cell areas and distinct-union monthly/yearly totals, test object-store revision/concurrency/resume. Set actual SLOs and cost envelope. |
| 4: approved historical backfill | Explicit user approval for transfer/storage/time budget, verified transport/catalog and monitoring | Source-specific queued windows for target2001-2025/2012-2025 records; immutable originals; verified partitions/gaps before publishing completeness; restartable workers and sampling against NASA. No automatic decade-scale job starts here. |
| 5: production global APIs/recent reconciliation | Accepted dataset revisions, exposure/coverage policy, implemented tested new contract | Preserve 17 legacy operations; add real global schema/adapters, quota-safe exports/map aggregates and stream-specific freshness. Frontend enables capabilities only as each endpoint/data gate passes. Separate production/public deployment approval. |

Operational risks: mission cessation and sampling drift; SP lag and changing API availability; incomplete mirror history/reprocessing; cloud/overpass exposure missing; RAM/disk/egress amplification and tiny partitions; source/collection conflation; country-border/offshore semantics; object-store consistency/locks; and treating NRT as emergency alerts. Acceptance evidence, rather than a world basemap or successful small query, controls readiness claims.
