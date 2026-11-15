"""Explicit, bounded NASA requests; isolated cache leaves historical imports intact."""
import csv
import hashlib
import io
import json
import os
import re
import threading
import uuid
import shutil
import time
from functools import wraps
from pipeline.locking import exclusive
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field, model_validator
from pipeline.config import ROOT, DATA, SOURCES
from pipeline.clean import clean, REQUIRED
from pipeline.ingest import validate_bbox, read_csv
from pipeline.limits import MAX_FILE_BYTES, MAX_OBSERVATIONS, MAX_CACHE_BYTES, RETENTION_DAYS, connection
from backend.app.security import require_admin

router = APIRouter(prefix='/api/explorer')
CACHE = DATA / 'explorer'
LOCK = threading.Lock()
PRODUCTS = {**SOURCES, **{k.replace('_SP', '_NRT'): v for k,v in SOURCES.items()}}

def nasa(path):
    key = os.environ.get('FIRMS_MAP_KEY', '').strip()
    if not key:
        raise HTTPException(503, 'NASA download key is missing on the server. Imported data remains usable.')
    try:
        with requests.get('https://firms.modaps.eosdis.nasa.gov/api/' + path.replace('{key}', key), timeout=(15,120), stream=True) as r:
            if r.status_code != 200:
                raise HTTPException(502, f'NASA returned HTTP {r.status_code}')
            chunks = []; size = 0
            for chunk in r.iter_content(65536):
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise HTTPException(413, 'NASA response exceeds input budget')
                chunks.append(chunk)
            return b''.join(chunks)
    except requests.RequestException:
        raise HTTPException(502, 'NASA connection failed. Retry later; cached data is unchanged.') from None

def cache_mutation(function):
    @wraps(function)
    def guarded(*args, **kwargs):
        try:
            with exclusive(CACHE.parent / '.explorer.lock'):
                return function(*args, **kwargs)
        except ValueError as exc:
            if str(exc) == 'Another data operation is running':
                raise HTTPException(409, str(exc)) from None
            raise
    return guarded


def cache_read(function):
    @wraps(function)
    def guarded(*args, **kwargs):
        try:
            with exclusive(CACHE.parent / '.explorer.lock', shared=True):
                return function(*args, **kwargs)
        except ValueError as exc:
            if str(exc) == 'Another data operation is running':
                raise HTTPException(409, 'Cache maintenance is running; retry later') from None
            raise
    return guarded


@router.get('/availability')
def availability():
    # Public reads never contact NASA or create cache files.
    path = CACHE / 'availability.json'
    if path.exists():
        return json.loads(path.read_text())
    raise HTTPException(503, 'Availability not cached; administrator refresh required')


@router.post('/availability/refresh', tags=['Administrator'], dependencies=[Depends(require_admin)])
@cache_mutation
def refresh_availability():
    with LOCK:
        content = nasa('data_availability/csv/{key}/all').decode('utf-8-sig')
        records = [{k:r[k] for k in ('data_id','min_date','max_date')} for r in csv.DictReader(io.StringIO(content)) if r.get('data_id') in PRODUCTS]
        if not records:
            raise HTTPException(502, 'NASA returned no availability records')
        saved = {'checked_at':datetime.now(timezone.utc).isoformat(),'records':records}
        CACHE.mkdir(parents=True, exist_ok=True)
        if cache_bytes() + len(json.dumps(saved).encode()) > MAX_CACHE_BYTES:
            raise HTTPException(413, 'Cache budget exceeded')
        atomic_json(CACHE / 'availability.json', saved)
        return saved


class CacheFile(io.FileIO):
    """Reject writes before they exceed the explorer cache's byte budget."""
    def write(self, data):
        if cache_bytes() + len(data) > MAX_CACHE_BYTES:
            raise HTTPException(413, 'Cache budget exceeded')
        return super().write(data)


def atomic_json(path, value):
    temporary = path.with_suffix('.tmp')
    try:
        with CacheFile(temporary, 'wb') as handle:
            handle.write(json.dumps(value).encode())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def cache_bytes():
    return sum(p.stat().st_size for p in CACHE.rglob('*') if p.is_file()) if CACHE.exists() else 0


@router.post('/cleanup', tags=['Administrator'], dependencies=[Depends(require_admin)])
@cache_mutation
def cleanup():
    # Only explicit cleanup expires datasets; startup never removes legacy data.
    if not LOCK.acquire(blocking=False):
        raise HTTPException(409, 'Another cache operation is running')
    try:
        removed = []
        cutoff = time.time() - RETENTION_DAYS * 86400
        for folder in CACHE.iterdir() if CACHE.exists() else []:
            if folder.is_dir() and re.fullmatch('[a-f0-9]{32}', folder.name) and folder.stat().st_mtime < cutoff:
                shutil.rmtree(folder)
                removed.append(folder.name)
        for pointer in CACHE.glob('*.json'):
            if pointer.name != 'availability.json' and json.loads(pointer.read_text()).get('dataset') in removed:
                pointer.unlink()
        return {'removed': removed, 'retention_days': RETENTION_DAYS}
    finally:
        LOCK.release()

class LoadRequest(BaseModel):
    sources: list[str] = Field(min_length=1,max_length=4)
    start: date
    end: date
    bbox: list[float] = Field(default_factory=lambda:[-180,-90,180,90])

    @model_validator(mode='after')
    def valid(self):
        validate_bbox(self.bbox)
        if len(set(self.sources))!=len(self.sources) or any(s not in PRODUCTS for s in self.sources):
            raise ValueError('Select distinct supported NASA products')
        if any(s.replace('_NRT','_SP') in self.sources for s in self.sources if s.endswith('_NRT')):
            raise ValueError('Select one processing stream per instrument/platform')
        days=(self.end-self.start).days+1
        large=(self.bbox[2]-self.bbox[0])*(self.bbox[3]-self.bbox[1])>10000
        if days<1 or days>(7 if large else 31):
            raise ValueError('Choose up to 7 days globally or 31 days for a smaller region')
        return self

@router.post('/load', tags=['Administrator'], description='Disabled by default. Server-side administrator operation only.', dependencies=[Depends(require_admin)])
@cache_mutation
def load(selection: LoadRequest):
    if not LOCK.acquire(blocking=False):
        raise HTTPException(409,'Another NASA download is running; please wait.')
    folder = None
    activated = False
    try:
        known={r['data_id']:r for r in availability()['records']}
        for source in selection.sources:
            r=known.get(source)
            if not r or str(selection.start)<r['min_date'] or str(selection.end)>r['max_date']:
                raise HTTPException(422,f'{source}: dates outside NASA availability. Select dates in the displayed range.')
        signature=hashlib.sha256(selection.model_dump_json().encode()).hexdigest()
        pointer=CACHE / (signature+'.json')
        if pointer.exists():
            meta=json.loads(pointer.read_text())
            if (datetime.now(timezone.utc)-datetime.fromisoformat(meta['downloaded_at'])).total_seconds()<3600:
                return meta
        if cache_bytes() >= MAX_CACHE_BYTES:
            raise HTTPException(413, 'Cache budget exhausted; run administrator cleanup')
        processed = 0
        frames=[]; reports=[]; generation=uuid.uuid4().hex
        folder=CACHE/generation; folder.mkdir(parents=True)
        for source in selection.sources:
            current=selection.start
            while current<=selection.end:
                days=min(5,(selection.end-current).days+1)
                bbox=','.join(map(str,selection.bbox))
                content=nasa(f'area/csv/{{key}}/{source}/{bbox}/{days}/{current}')
                if len(content) > MAX_FILE_BYTES or cache_bytes() + len(content) > MAX_CACHE_BYTES:
                    raise HTTPException(413, 'Input or cache budget exceeded')
                header=next(csv.reader(io.StringIO(content.decode('utf-8-sig'))),[])
                if not REQUIRED.issubset(header):
                    raise HTTPException(502,'NASA returned no valid CSV schema. No new dataset was activated.')
                raw=folder/f'{source}_{current}.csv'
                with CacheFile(raw, 'wb') as handle:
                    handle.write(content)
                frame=read_csv(raw)
                processed += len(frame)
                if processed > MAX_OBSERVATIONS:
                    raise HTTPException(413, 'Observation budget exceeded')
                good,bad,report=clean(frame,source.replace('_NRT','_SP'),hashlib.sha256(content).hexdigest(),datetime.now(timezone.utc).isoformat(),near_real_time=source.endswith('_NRT'))
                west,south,east,north=selection.bbox
                if not good.empty and not (good.longitude.between(west,east) & good.latitude.between(south,north) & good.acq_date.between(str(current),str(current+timedelta(days=days-1)))).all():
                    raise HTTPException(502,'NASA rows fall outside the requested area or dates; dataset was not activated.')
                good['source_dataset']=source
                good['processing_stream']='near-real-time' if source.endswith('_NRT') else 'standard'
                # Explicit display grid, not equal-area, calibrated activity or burned area.
                lon=np.minimum(np.floor((good.longitude+180)*10).astype(int),3599)
                lat=np.minimum(np.floor((good.latitude+90)*10).astype(int),1799)
                good['cell_id']=['geo01:'+str(x)+':'+str(y) for x,y in zip(lon,lat)]
                frames.append(good)
                reports.append({'source':source,**report})
                current+=timedelta(days=days)
        frame=pd.concat(frames,ignore_index=True)
        with CacheFile(folder/'observations.parquet', 'wb') as handle:
            frame.to_parquet(handle,index=False)
        meta={**selection.model_dump(mode='json'),'dataset':generation,'downloaded_at':datetime.now(timezone.utc).isoformat(),'rows':len(frame),'reports':reports,'grid':'0.1 degree geographic display cells; cell area varies with latitude','attribution':'NASA FIRMS; native confidence and processing streams preserved'}
        if cache_bytes() > MAX_CACHE_BYTES:
            raise HTTPException(413, 'Cache budget exceeded')
        if cache_bytes() + 2 * len(json.dumps(meta).encode()) > MAX_CACHE_BYTES:
            raise HTTPException(413, 'Cache budget exceeded')
        atomic_json(folder/'metadata.json', meta)
        atomic_json(pointer, meta)
        activated = True
        return meta
    finally:
        if folder is not None and not activated:
            shutil.rmtree(folder)
        LOCK.release()

def dataset_query(dataset, sensor, confidence, min_frp):
    if not re.fullmatch('[a-f0-9]{32}',dataset):
        raise HTTPException(404,'Unknown dataset')
    folder=CACHE/dataset
    if not (folder/'metadata.json').exists():
        raise HTTPException(404,'Dataset not available; load a selection first')
    meta=json.loads((folder/'metadata.json').read_text())
    where = 'frp >= ?' if min_frp > 0 else 'TRUE'
    args = [str(folder/'observations.parquet')]
    if min_frp > 0: args.append(min_frp)
    if sensor != 'all':
        where += ' AND sensor=?'
        args.append(sensor)
    if confidence != 'all':
        where += " AND ((sensor='MODIS' AND TRY_CAST(confidence_native AS DOUBLE)>=?) OR (sensor='VIIRS' AND lower(confidence_native) IN (" + ("'h'" if confidence == 'strict' else "'n','h'") + ")))"
        args.append(80 if confidence == 'strict' else 30)
    return ' FROM read_parquet(?) WHERE ' + where, args, meta


def records(frame):
    return json.loads(frame.to_json(orient='records',date_format='iso'))

@router.get('/cached')
@cache_read
def cached():
    paths=sorted(CACHE.glob('*/metadata.json'),key=lambda p:p.stat().st_mtime,reverse=True) if CACHE.exists() else []
    return [json.loads(p.read_text()) for p in paths[:20]]

@router.get('/view')
@cache_read
def view(dataset:str,limit:int=Query(10000,ge=1,le=10000),offset:int=Query(0,ge=0,le=1000000),sensor:Literal['all','MODIS','VIIRS']='all',confidence:Literal['all','nominal','strict']='all',min_frp:float=Query(0,ge=0,allow_inf_nan=False)):
    sql,args,meta=dataset_query(dataset,sensor,confidence,min_frp)
    with connection() as db:
        stats=db.execute("SELECT count(*), count(*) FILTER (WHERE sensor='MODIS'), count(*) FILTER (WHERE sensor='VIIRS'), count(DISTINCT cell_id), CAST(max(timestamp_utc) AS VARCHAR)"+sql,args).fetchone()
        daily_rows=db.execute("SELECT acq_date,count(*) FILTER (WHERE sensor='MODIS'),count(*) FILTER (WHERE sensor='VIIRS'),count(DISTINCT cell_id),avg(frp)"+sql+' GROUP BY acq_date',args).fetchall()
        by_day={str(r[0]):r for r in daily_rows}
        daily=[]
        for day in pd.date_range(meta['start'],meta['end']):
            key=str(day.date()); r=by_day.get(key,(key,0,0,0,None))
            daily.append(dict(date=key,modis=r[1],viirs=r[2],grid=r[3],frp=r[4]))
        fields='latitude,longitude,CAST(timestamp_utc AS VARCHAR) AS timestamp_utc,sensor,source_dataset,satellite,version,confidence_native,confidence_type,frp,cell_id,processing_stream'
        markers=db.execute('SELECT * FROM (SELECT '+fields+sql+' ORDER BY timestamp_utc DESC,source_dataset,latitude,longitude LIMIT ? OFFSET ?) ORDER BY timestamp_utc',[*args,limit,offset]).df()
        histogram=db.execute('SELECT '+','.join(f'count(*) FILTER (WHERE frp >= {low}'+(f' AND frp < {high}' if high else '')+')' for low,high in [(0,10),(10,25),(25,50),(50,100),(100,None)])+sql,args).fetchone()
    markers['timestamp_utc'] = pd.to_datetime(markers.timestamp_utc, utc=True)
    return {'metadata':meta,'records':records(markers),'total':stats[0],'truncated':offset+len(markers)<stats[0],'daily':daily,'histogram':list(histogram),'summary':{'modis':stats[1],'viirs':stats[2],'grid':stats[3],'latest':None if stats[4] is None else str(pd.Timestamp(stats[4]))}}


@router.get('/export')
@cache_read
def export(dataset:str,sensor:Literal['all','MODIS','VIIRS']='all',confidence:Literal['all','nominal','strict']='all',min_frp:float=Query(0,ge=0,allow_inf_nan=False)):
    sql,args,meta=dataset_query(dataset,sensor,confidence,min_frp)
    with connection() as db:
        count=db.execute('SELECT count(*)'+sql,args).fetchone()[0]
        if count > MAX_OBSERVATIONS:
            raise HTTPException(413, 'Export exceeds observation budget; narrow filters')
        fields='latitude,longitude,acq_date,acq_time,sensor,source_dataset,satellite,version,confidence_native,confidence_type,frp,cell_id,processing_stream'
        frame=db.execute('SELECT '+fields+sql+' ORDER BY timestamp_utc LIMIT ?',[*args,MAX_OBSERVATIONS]).df()
    return Response(frame.to_csv(index=False),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="nasa-observations.csv"'})
