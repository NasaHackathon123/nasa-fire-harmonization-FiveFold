"""Controlled ingestion CLI. Dashboard requests never download NASA data."""
import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import shutil
import time
import pandas as pd
import requests
import os
from .config import DATA, ROOT, SOURCES
from .clean import REQUIRED
from .limits import MAX_FILE_BYTES, MAX_OBSERVATIONS
from .locking import exclusive
import threading
import tempfile
IMPORT_LOCK = threading.RLock()

BBOX = [112., -3., 114., -1.]

def read_csv(path):
    if Path(path).stat().st_size > MAX_FILE_BYTES:
        raise ValueError('Input file exceeds byte budget')
    try:
        # Strict width validation prevents silently shifted malformed records.
        with Path(path).open(encoding="utf-8-sig", newline="") as handle:
            rows = csv.reader(handle, strict=True)
            header = next(rows)
            if len(header) != len(set(header)) or not REQUIRED.issubset(header):
                raise ValueError("Missing or duplicate CSV headers")
            for number, row in enumerate(rows, 2):
                if number - 1 > MAX_OBSERVATIONS:
                    raise ValueError("Input exceeds observation budget")
                if len(row) != len(header):
                    raise ValueError(f"Malformed CSV row {number}")
        return pd.read_csv(path, dtype=str, encoding="utf-8-sig", on_bad_lines="error")
    except (StopIteration, pd.errors.EmptyDataError, pd.errors.ParserError, csv.Error, UnicodeError) as exc:
        raise ValueError("Empty or malformed CSV") from exc

def import_file(path, source, start=None, end=None, bbox=None, data_dir=DATA):
    with IMPORT_LOCK, exclusive(Path(data_dir) / ".ingest.lock"):
        return _import_file(path, source, start, end, bbox, data_dir)


def _import_file(path, source, start=None, end=None, bbox=None, data_dir=DATA):
    if source not in SOURCES:
        raise ValueError("Unsupported source; standard processing is required")
    path = Path(path)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Input file exceeds byte budget")
    raw = data_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path = raw / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    prior = next((item for item in manifest if item["checksum"] == digest and item["source"] == source and item.get("coverage_start") == start and item.get("coverage_end") == end and item.get("bbox") == bbox), None)
    if prior:
        if prior["source"] != source or (start and (prior["coverage_start"] != start or prior["coverage_end"] != end or prior["bbox"] != bbox)):
            raise ValueError("Duplicate file has conflicting provenance; review manifest rather than silently relabeling")
        return prior
    frame = read_csv(path)
    if (start is None) != (end is None) or ((start is not None) != (bbox is not None)):
        raise ValueError("Coverage requires start, end and bbox together")
    if start and date.fromisoformat(start) > date.fromisoformat(end):
        raise ValueError("Coverage start must precede end")
    if start and not frame.empty:
        parsed = pd.to_datetime(frame.acq_date, errors="coerce")
        valid_dates = parsed.dropna().dt.strftime("%Y-%m-%d")
        if ((valid_dates < start) | (valid_dates > end)).any():
            raise ValueError("Observations fall outside declared coverage")
    if bbox is not None:
        validate_bbox(bbox)
    identity = hashlib.sha256((digest + source + str(start) + str(end) + str(bbox)).encode()).hexdigest()
    destination = raw / (digest[:16] + "_" + path.name)
    if path.resolve().parent == raw.resolve():
        destination = path
    item = {"id": identity, "filename": destination.name, "source": source, "checksum": digest, "row_count": len(frame),
            "dataset_versions": sorted(frame.version.dropna().unique().tolist()), "imported_at": datetime.now(timezone.utc).isoformat(),
            "coverage_start": start, "coverage_end": end, "bbox": bbox, "coverage_basis": "operator_declared_import_completeness" if start else "unknown"}
    if sum(i["row_count"] for i in manifest) + len(frame) > MAX_OBSERVATIONS:
        raise ValueError("Registered observations exceed budget")
    if path.resolve() != destination.resolve() and not destination.exists():
        shutil.copy2(path, destination)
    manifest.append(item)
    temporary = manifest_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, indent=2))
    temporary.replace(manifest_path)
    return item

def validate_bbox(bbox):
    if len(bbox) != 4 or not (-180 <= bbox[0] < bbox[2] <= 180 and -90 <= bbox[1] < bbox[3] <= 90):
        raise ValueError("Expected west,south,east,north within geographic bounds")

def download(source, start, end, bbox, data_dir=DATA, session=None, pause=time.sleep):
    validate_bbox(bbox)
    if source not in SOURCES:
        raise ValueError("Unsupported standard-processing source")
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last:
        raise ValueError("Start must precede end")
    key = os.environ.get("FIRMS_MAP_KEY")
    if not key:
        raise ValueError("FIRMS_MAP_KEY is required")
    client = session or requests.Session()
    results = []
    while first <= last:
        days = min(5, (last - first).days + 1)
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{','.join(map(str,bbox))}/{days}/{first}"
        response = None
        for attempt in range(4):
            try:
                response = client.get(url, timeout=(15, 120), stream=True)
            except requests.RequestException:
                # Never include requests exceptions: NASA URLs contain credentials.
                if attempt == 3:
                    raise ValueError("NASA request failed; check connectivity and credentials") from None
                pause(2 ** attempt)
                continue
            if response.status_code in [429, 500, 502, 503, 504]:
                response.close()
                retry = response.headers.get("Retry-After", "")
                pause(min(600, max(1, int(retry))) if retry.isdigit() else 2 ** attempt)
                continue
            if response.status_code != 200:
                response.close()
                raise ValueError(f"NASA returned HTTP {response.status_code}; source or interval may be unavailable")
            break
        else:
            raise ValueError("NASA retry limit reached; retry ingestion later")
        # Reject non-CSV API error text before it can become a raw data source.
        chunks = []; size = 0
        try:
            for chunk in response.iter_content(65536):
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise ValueError('NASA response exceeds byte budget')
                chunks.append(chunk)
        except requests.RequestException:
            raise ValueError('NASA download interrupted') from None
        finally:
            response.close()
        content = b''.join(chunks)
        header = next(csv.reader(io.StringIO(content.decode('utf-8-sig'))), [])
        if not REQUIRED.issubset(header):
            raise ValueError("NASA returned no valid observation schema; requested source or dates may be unavailable")
        data_dir.mkdir(parents=True, exist_ok=True)
        if len(content) > MAX_FILE_BYTES:
            raise ValueError('NASA response exceeds byte budget')
        digest = hashlib.sha256(content).hexdigest()[:16]
        # Staging is isolated from original NASA inputs and always removed on failure.
        with tempfile.TemporaryDirectory(prefix='.download-', dir=data_dir) as staging:
            path = Path(staging) / f'{source}_{first}_{days}_{digest}.csv'
            path.write_bytes(content)
            results.append(import_file(path, source, str(first), str(first + timedelta(days=days-1)), bbox, data_dir))
        first += timedelta(days=days)
        if first <= last:
            pause(1)
    return results

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["import", "download"]:
        command = sub.add_parser(name)
        command.add_argument("--source", choices=list(SOURCES), required=True)
        command.add_argument("--start")
        command.add_argument("--end")
        command.add_argument("--bbox", type=lambda x: list(map(float, x.split(","))))
        if name == "import":
            command.add_argument("files", nargs="+")
    args = parser.parse_args()
    if args.command == "import":
        for path in args.files:
            result = import_file(path, args.source, args.start, args.end, args.bbox)
            print(json.dumps({"id": result["id"], "rows": result["row_count"]}))
    else:
        if not args.start or not args.end or args.bbox is None:
            parser.error("download requires --start, --end and --bbox")
        print(json.dumps(download(args.source, args.start, args.end, args.bbox)))

if __name__ == "__main__":
    main()
