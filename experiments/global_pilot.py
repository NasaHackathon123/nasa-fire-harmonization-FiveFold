"""Offline global ingestion experiment; not imported by FastAPI. No network client."""
import csv
from contextlib import closing
import hashlib
import json
import shutil
import sqlite3
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from pipeline.clean import clean, REQUIRED
from pipeline.config import SOURCES
from pipeline.ingest import validate_bbox
from pipeline.locking import exclusive

METHOD = 'global-offline-native-partitions-pilot-v1'
PRODUCTS = {*SOURCES, *(s.replace('_SP','_NRT') for s in SOURCES)}


def checksum(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def stream_for(version, source):
    for suffix, stream in [('URT','ultra-real-time'), ('NRT','near-real-time'), ('RT','real-time')]:
        if str(version).upper().endswith(suffix):
            return stream
    return 'standard' if source.endswith('_SP') else 'unspecified-recent'


def import_day(inputs, day, boxes, output, *, batch_rows=5000,
               max_file_bytes=64*1024*1024, max_scanned_rows=1_000_000,
               max_output_rows=100_000, max_output_bytes=512*1024*1024):
    """One restartable daily job. inputs=[(Path, exact source ID)]; boxes={name:bbox}.

    Coverage remains unknown: a local CSV's absence of rows is not exposure evidence.
    Original files are read only. Exact native duplicates are removed per source,
    never across platforms/streams/versions. No global scientific grid is assigned.
    """
    day = date.fromisoformat(str(day)).isoformat()
    output = Path(output)
    if not inputs or not boxes or batch_rows < 1 or min(max_file_bytes,max_scanned_rows,max_output_rows,max_output_bytes) < 1:
        raise ValueError('Positive budgets, inputs and geographic boxes are required')
    for name, box in boxes.items():
        if not name or not isinstance(name,str): raise ValueError('Named boxes required')
        validate_bbox(box)  # Dateline-crossing selections must be split explicitly.
    provenance=[]
    for path, source in inputs:
        path=Path(path)
        if source not in PRODUCTS: raise ValueError('Unsupported exact source')
        if path.stat().st_size > max_file_bytes: raise ValueError('Input byte budget exceeded')
        provenance.append({'source':source,'sha256':checksum(path),'bytes':path.stat().st_size})
    spec={'method':METHOD,'day':day,'boxes':boxes,'inputs':provenance}
    identity=hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest()
    output.mkdir(parents=True,exist_ok=True)
    with exclusive(output/'.pilot.lock'):
        destination=output/identity
        if (destination/'manifest.json').exists():
            saved=json.loads((destination/'manifest.json').read_text())
            if saved['selected_rows'] > max_output_rows or saved['scanned_rows'] > max_scanned_rows:
                raise ValueError('Existing job exceeds requested row budget')
            if sum(p.stat().st_size for p in destination.rglob('*') if p.is_file()) > max_output_bytes:
                raise ValueError('Existing job exceeds requested output byte budget')
            for entry in saved['parts']:
                if checksum(destination/entry['path']) != entry['sha256']:
                    raise ValueError('Pilot output integrity failure')
            return saved
        staging=Path(tempfile.mkdtemp(prefix='.incomplete-',dir=output))
        try:
            selected=0; scanned=0; selected_day=0; rejected=0; duplicates=0
            parts=[]; batch_count=0
            imported_at=datetime.now(timezone.utc).isoformat()
            with closing(sqlite3.connect(staging/'dedup.sqlite')) as dedup:
                dedup.execute('CREATE TABLE seen (id TEXT PRIMARY KEY)')
                for (path,source),origin in zip(inputs,provenance):
                    with Path(path).open(encoding='utf-8-sig',newline='') as handle:
                        reader=csv.DictReader(handle,strict=True)
                        if not reader.fieldnames or len(reader.fieldnames)!=len(set(reader.fieldnames)) or not REQUIRED.issubset(reader.fieldnames):
                            raise ValueError('Missing or duplicate CSV headers')
                        buffer=[]
                        def flush(rows):
                            nonlocal selected,rejected,duplicates,batch_count
                            if not rows: return
                            raw=pd.DataFrame(rows,dtype=str)
                            raw['native_record_id']=[hashlib.sha256(json.dumps([source,r],sort_keys=True,separators=(',',':')).encode()).hexdigest() for r in rows]
                            good,bad,report=clean(raw,source.replace('_NRT','_SP'),origin['sha256'],imported_at,near_real_time=source.endswith('_NRT'))
                            rejected += len(bad)
                            duplicates += report['duplicate_rows_removed']
                            mask=pd.Series(False,index=good.index)
                            for west,south,east,north in boxes.values():
                                mask |= good.longitude.between(west,east) & good.latitude.between(south,north)
                            good=good[mask].copy()
                            keep=[]
                            for record_id in good.native_record_id:
                                cursor=dedup.execute('INSERT OR IGNORE INTO seen VALUES (?)',[record_id])
                                keep.append(cursor.rowcount==1)
                            duplicates += len(good)-sum(keep)
                            good=good.loc[keep].copy()
                            if good.empty:return
                            selected += len(good)
                            if selected>max_output_rows: raise ValueError('Output row budget exceeded')
                            good['source_dataset']=source
                            good['processing_stream']=[stream_for(v,source) for v in good.version]
                            # Exact collection and stream partitions; path hashes prevent source version path injection.
                            for (version,stream), group in good.groupby(['version','processing_stream']):
                                collection=hashlib.sha256(str(version).encode()).hexdigest()[:16]
                                folder=staging/f'source={source}'/f'stream={stream}'/f'collection={collection}'/f'year={day[:4]}'/f'month={day[5:7]}'/f'day={day[8:]}'
                                folder.mkdir(parents=True,exist_ok=True)
                                part=folder/f'part-{batch_count:06d}.parquet'
                                group.sort_values(['latitude','longitude','timestamp_utc']).to_parquet(part,index=False,compression='zstd',row_group_size=batch_rows)
                                parts.append({'path':part.relative_to(staging).as_posix(),'sha256':checksum(part),'rows':len(group),'version':str(version),'stream':stream,'source':source})
                                batch_count+=1
                            if sum(p.stat().st_size for p in staging.rglob('*') if p.is_file()) > max_output_bytes:
                                raise ValueError('Output byte budget exceeded')
                        for row in reader:
                            scanned+=1
                            if scanned>max_scanned_rows:raise ValueError('Scanned row budget exceeded')
                            if None in row or any(v is None for v in row.values()): raise ValueError('Malformed CSV width')
                            if row['acq_date'] != day:continue
                            selected_day+=1
                            buffer.append(row)
                            if len(buffer)>=batch_rows:flush(buffer);buffer=[]
                        flush(buffer)
                    if checksum(path)!=origin['sha256']:raise ValueError('Input changed during ingestion')
                    dedup.commit()
            (staging/'dedup.sqlite').unlink()
            result={**spec,'job':identity,'selected_rows':selected,'scanned_rows':scanned,
                    'date_rows_before_validation':selected_day,'rejected_day_rows':rejected,
                    'exact_duplicates_removed':duplicates,'parts':parts,'ingested_at':imported_at,
                    'coverage_status':'unknown','coverage_basis':'local extract; no independently verified NASA inventory/exposure',
                    'parquet_bytes':sum((staging/p['path']).stat().st_size for p in parts)}
            (staging/'manifest.json').write_text(json.dumps(result,indent=2))
            if sum(p.stat().st_size for p in staging.rglob('*') if p.is_file()) > max_output_bytes:
                raise ValueError('Output byte budget exceeded')
            staging.rename(destination)
            return result
        finally:
            if staging.exists():shutil.rmtree(staging)


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',action='append',nargs=2,metavar=('CSV','SOURCE'),required=True)
    parser.add_argument('--day',required=True)
    parser.add_argument('--boxes',type=Path,required=True,help='JSON object mapping region names to bboxes')
    parser.add_argument('--output',type=Path,default=Path('data/global_pilot'))
    args=parser.parse_args()
    result=import_day([(Path(p),s) for p,s in args.input],args.day,json.loads(args.boxes.read_text()),args.output)
    print(json.dumps({k:result[k] for k in ('job','selected_rows','scanned_rows','coverage_status','parquet_bytes')}))

if __name__=='__main__':main()
