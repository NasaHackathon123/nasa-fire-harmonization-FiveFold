# Backend implementation plan
Scope updated by owner: backend and scientific pipeline only; no frontend.

1. Preserve existing downloader, status check, sample files and .env; secure ignore rules. Health API, dependency setup.
2. Register real files with checksums and explicit coverage. Controlled standard-product API ingestion, retries and five-day chunks.
3. Source-specific cleaning, native confidence, exact duplicates, quarantine, reports.
4. UTM 49S 1 km grid; independent sensor/source/version aggregates and overlap.
5. Monthly coverage, comparable baselines and zero-safe anomalies. Five-day sample cannot establish historical baselines.
6. Exploratory held-out calibration helper, disabled production harmonization.
7. Validated REST endpoints, bounded hotspot pagination, export, quality, methodology.
8. Pipeline and HTTP tests using isolated synthetic fixtures; real sample integration checks.
9. Backend setup/deployment docs and logical PostGIS migration schema.

Frontend explicitly excluded. Historical archive acquisition remains a controlled operator action.
