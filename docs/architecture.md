# Backend architecture

NASA CSV / controlled API -> immutable bronze files + manifest -> source-aware cleaning -> metric grid -> versioned Parquet generation -> DuckDB repository -> FastAPI.

`pipeline/ingest.py` handles source registration and retrieval; `clean.py` validates native values; `spatial.py` assigns cells; `aggregate.py` computes daily/monthly metrics; `harmonize.py` contains explicitly exploratory calibration and anomaly math; `validate.py` orchestrates a rebuild. Original scripts remain intact.

API routes delegate storage queries to `backend/app/database/repository.py` and scientific response assembly to `services/analytics.py`. Pydantic models document selection and outputs. Each request pins a generation selected by an atomic CURRENT.json pointer. New builds create new generation directories; existing requests keep their prior snapshot. Single-writer ingestion is required.

## Logical storage mapping

| Logical entity | Local representation |
| --- | --- |
| data_sources | raw/manifest.json and generation/data_sources.json |
| raw_observations | original raw CSVs |
| clean_observations | generation/clean_observations.parquet |
| rejected observations | generation/quarantine.parquet |
| grid_cells | generation/grid_cells.parquet |
| cell_daily_activity | generation/cell_daily_activity.parquet (source-level daily counts); cell/date membership derived from clean observations |
| monthly_summaries | generation/monthly_summaries.parquet |
| harmonization_models | no production model; exploratory function output only |
| harmonized_activity | unavailable by design |

All generation paths are under data/processed. Silver and gold are colocated per generation to avoid publishing mismatched versions. Source-level daily files contain counts; individual cell memberships stay in cleaned rows without a large duplicate dataset.

A future PostGIS adapter should implement the same repository operations. The SQL migration draft includes spatial GiST indexes and source/time indexes. It has not been executed against PostgreSQL.
