"""Rebuild immutable Parquet generations and atomically switch CURRENT.json."""
import hashlib
import uuid
import shutil
from .limits import MAX_OBSERVATIONS, MAX_FILE_BYTES
from .locking import exclusive
import json
from pathlib import Path
import pandas as pd
from .config import DATA, VERSION, METHOD
from .ingest import read_csv
from .clean import clean
from .spatial import assign_grid
from .aggregate import gold

def build(data_dir=DATA):
    output = data_dir / 'processed' / uuid.uuid4().hex
    try:
        with exclusive(data_dir / ".ingest.lock"):
            return _build(data_dir, output)
    except BaseException:
        if output.exists():
            shutil.rmtree(output)
        raise


def _build(data_dir, output):
    manifest_path = data_dir / "raw" / "manifest.json"
    if not manifest_path.exists():
        raise ValueError("Import sources first using python -m pipeline.ingest")
    manifest = json.loads(manifest_path.read_text())
    if not manifest:
        raise ValueError("No sources registered")
    if sum(item['row_count'] for item in manifest) > MAX_OBSERVATIONS:
        raise ValueError('Build exceeds observation budget')
    generation = output.name
    output.mkdir(parents=True, exist_ok=True)
    accepted, rejected, reports = [], [], []
    for source in manifest:
        path = data_dir / "raw" / source["filename"]
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError('Input file exceeds byte budget')
        if hashlib.sha256(path.read_bytes()).hexdigest() != source["checksum"]:
            raise ValueError("Raw source checksum mismatch; restore original input")
        good, bad, report = clean(read_csv(path), source["source"], source["id"], source["imported_at"])
        accepted.append(good)
        rejected.append(bad)
        reports.append({"source_id": source["id"], "source": source["source"], **report})
    frame = pd.concat(accepted, ignore_index=True)
    # Deduplicate exact native records across overlapping archive files only.
    derived = {"raw_source_id", "ingestion_timestamp", "quality_flags", "processing_version", "timestamp_utc", "confidence_type", "confidence_native"}
    keys = [x for x in frame.columns if x not in derived]
    cross_duplicates = int(frame.duplicated(subset=keys).sum())
    frame = assign_grid(frame.drop_duplicates(subset=keys).reset_index(drop=True))
    daily, monthly = gold(frame)
    frame.to_parquet(output / "clean_observations.parquet", index=False)
    pd.concat(rejected, ignore_index=True).to_parquet(output / "quarantine.parquet", index=False)
    daily.to_parquet(output / "cell_daily_activity.parquet", index=False)
    monthly.to_parquet(output / "monthly_summaries.parquet", index=False)
    frame[["cell_id", "grid_easting", "grid_northing"]].drop_duplicates().to_parquet(output / "grid_cells.parquet", index=False)
    report = {"processing_version": VERSION, "method": METHOD, "accepted_rows": len(frame), "cross_file_duplicates_removed": cross_duplicates, "sources": reports}
    (output / "cleaning_report.json").write_text(json.dumps(report, indent=2))
    (output / "data_sources.json").write_text(json.dumps(manifest, indent=2))
    pointer = data_dir / "processed" / "CURRENT.json"
    temp = pointer.with_suffix(".tmp")
    temp.write_text(json.dumps({"generation": generation}))
    temp.replace(pointer)
    return report

if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
