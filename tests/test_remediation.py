"""Regression tests use synthetic fixtures only; no live NASA requests."""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
import requests
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.routers import explorer
from backend.app.database.repository import Repository
from backend.app.schemas.models import Selection
from backend.app.services.analytics import calendar
from pipeline import ingest, validate

PAYLOAD = {'sources':['MODIS_SP'], 'start':'2023-09-01', 'end':'2023-09-01'}


@pytest.fixture
def admin(tmp_path, monkeypatch, frame):
    monkeypatch.setenv('EXPLORER_HTTP_INGEST_ENABLED', 'true')
    monkeypatch.setenv('EXPLORER_ADMIN_TOKEN', 'test-only')
    monkeypatch.setattr(explorer, 'CACHE', tmp_path)
    monkeypatch.setattr(explorer, 'availability', lambda: {'records':[{'data_id':'MODIS_SP','min_date':'2020-01-01','max_date':'2026-01-01'}]})
    monkeypatch.setattr(explorer, 'nasa', lambda _: frame.to_csv(index=False).encode())
    return TestClient(app, headers={'Authorization':'Bearer test-only'})


@pytest.mark.parametrize('enabled,token', [(False,None),(True,None),(True,'wrong')])
def test_unauthorized_has_no_side_effects(tmp_path, monkeypatch, enabled, token):
    monkeypatch.setattr(explorer,'CACHE',tmp_path/'cache')
    monkeypatch.setenv('EXPLORER_HTTP_INGEST_ENABLED', str(enabled).lower())
    monkeypatch.setenv('EXPLORER_ADMIN_TOKEN','test-only')
    def forbidden(*args, **kwargs): pytest.fail('NASA must not be contacted')
    monkeypatch.setattr(explorer,'nasa',forbidden)
    monkeypatch.setattr(explorer.requests,'get',forbidden)
    client=TestClient(app, headers={'Authorization':'Bearer '+token} if token else {})
    for endpoint in ['load','availability/refresh','cleanup']:
        assert client.post('/api/explorer/'+endpoint,json=PAYLOAD).status_code==403
    for _ in range(20):
        assert client.get('/api/explorer/availability').status_code==503
    assert not (tmp_path/'cache').exists()


def test_availability_read_only(tmp_path,monkeypatch):
    monkeypatch.setattr(explorer,'CACHE',tmp_path)
    saved={'checked_at':'2000-01-01T00:00:00+00:00','records':[]}
    path=tmp_path/'availability.json'; path.write_text(json.dumps(saved))
    monkeypatch.setattr(explorer,'nasa',lambda _: pytest.fail('network'))
    before=path.stat().st_mtime_ns
    assert TestClient(app).get('/api/explorer/availability').json()==saved
    assert path.stat().st_mtime_ns==before


@pytest.mark.parametrize('budget', ['MAX_FILE_BYTES','MAX_OBSERVATIONS','MAX_CACHE_BYTES'])
def test_budget_failure_removes_incomplete(admin,monkeypatch,budget,tmp_path):
    monkeypatch.setattr(explorer,budget,1 if budget!='MAX_OBSERVATIONS' else 0)
    assert admin.post('/api/explorer/load',json=PAYLOAD).status_code==413
    assert list(tmp_path.iterdir())==[]


def test_interrupted_download_preserves_old_cache(admin,monkeypatch,tmp_path):
    old=admin.post('/api/explorer/load',json=PAYLOAD).json()['dataset']
    def interrupted(_): raise explorer.HTTPException(502,'Download interrupted')
    monkeypatch.setattr(explorer,'nasa',interrupted)
    changed={**PAYLOAD,'end':'2023-09-02'}
    assert admin.post('/api/explorer/load',json=changed).status_code==502
    assert [p.name for p in tmp_path.iterdir() if p.is_dir()]==[old]
    assert admin.get('/api/explorer/view',params={'dataset':old}).status_code==200


def test_concurrent_load_rejected(admin,monkeypatch):
    explorer.LOCK.acquire()
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _: admin.post('/api/explorer/load',json=PAYLOAD).status_code,range(2)))
        assert results==[409,409]
    finally:
        explorer.LOCK.release()


def test_retention_explicit_preserves_valid_cache(admin,tmp_path):
    identifier=admin.post('/api/explorer/load',json=PAYLOAD).json()['dataset']
    assert admin.post('/api/explorer/cleanup').json()['removed']==[]
    folder=tmp_path/identifier
    past=time.time()-8*86400; os.utime(folder,(past,past))
    assert admin.post('/api/explorer/cleanup').json()['removed']==[identifier]
    assert not folder.exists()
    assert not list(tmp_path.glob('*.json'))


@pytest.mark.parametrize('confidence,expected',[('all',2),('nominal',1),('strict',1)])
@pytest.mark.parametrize('metric',['detections','occupied_cells','daily_cell_sum'])
def test_partial_month_policies(tmp_path,frame,confidence,expected,metric):
    import pandas as pd
    second=frame.copy(); second.loc[0,'confidence']='10'; second.loc[0,'acq_date']='2023-09-02'; second.loc[0,'longitude']='113.1'
    path=tmp_path/'input.csv'; pd.concat([frame,second]).to_csv(path,index=False)
    data=tmp_path/'data'
    ingest.import_file(path,'MODIS_SP','2023-09-01','2023-09-03',ingest.BBOX,data)
    validate.build(data)
    rows=calendar(Repository(data),Selection(sensor='MODIS',start=date(2023,9,1),end=date(2023,9,2),confidence=confidence,metric=metric))
    assert rows[0]['value']==expected
    assert rows[0]['coverage_status']=='complete'
    assert rows[0]['anomaly_status']=='incomplete_month'


def test_versions_do_not_pool_coverage(tmp_path,frame):
    data=tmp_path/'data'
    for version,start,end in [('6.1','2023-09-01','2023-09-15'),('6.2','2023-09-16','2023-09-30')]:
        sample=frame.copy(); sample.loc[0,'version']=version; sample.loc[0,'acq_date']=start
        path=tmp_path/(version+'.csv'); sample.to_csv(path,index=False)
        ingest.import_file(path,'MODIS_SP',start,end,ingest.BBOX,data)
    validate.build(data)
    rows=calendar(Repository(data),Selection(sensor='MODIS',start=date(2023,9,1),end=date(2023,9,30)))
    assert len(rows)==2
    assert all(r['coverage_status']=='partial' and r['imported_days']==15 for r in rows)


def test_zero_extract_and_region_coverage(tmp_path,frame):
    data=tmp_path/'data'; path=tmp_path/'empty.csv'; frame.iloc[:0].to_csv(path,index=False)
    ingest.import_file(path,'MODIS_SP','2023-09-01','2023-09-30',[112,-3,113,-1],data)
    validate.build(data)
    repo=Repository(data)
    selection=Selection(sensor='MODIS',start=date(2023,9,1),end=date(2023,9,30))
    assert calendar(repo,selection)[0]['value'] is None
    west=calendar(repo,selection.model_copy(update={'region':'central-kalimantan-west'}))[0]
    assert west['value']==0 and west['coverage_status']=='complete'


def test_private_file_and_build_limits(tmp_path,frame,monkeypatch):
    path=tmp_path/'input.csv'; frame.to_csv(path,index=False)
    monkeypatch.setattr(ingest,'MAX_FILE_BYTES',1)
    with pytest.raises(ValueError,match='byte budget'): ingest.import_file(path,'MODIS_SP',data_dir=tmp_path/'data')
    monkeypatch.setattr(ingest,'MAX_FILE_BYTES',100000)
    ingest.import_file(path,'MODIS_SP',data_dir=tmp_path/'data')
    monkeypatch.setattr(validate,'MAX_OBSERVATIONS',0)
    with pytest.raises(ValueError,match='budget'): validate.build(tmp_path/'data')
    assert not list((tmp_path/'data'/'processed').glob('*'))


def test_stream_interruption_writes_nothing(tmp_path,monkeypatch):
    monkeypatch.setenv('FIRMS_MAP_KEY','test-only')
    class Reply:
        status_code=200
        closed=False
        def iter_content(self,size):
            yield b'partial'
            raise requests.ConnectionError('secret URL must not escape')
        def close(self): self.closed=True
    reply=Reply()
    class Session:
        def get(self,*args,**kwargs): return reply
    with pytest.raises(ValueError,match='interrupted'):
        ingest.download('MODIS_SP','2023-09-01','2023-09-01',ingest.BBOX,tmp_path,Session())
    assert reply.closed and not list(tmp_path.iterdir())


def test_mixed_file_cannot_prove_collection_completeness(tmp_path,frame):
    import pandas as pd
    second=frame.copy(); second.loc[0,'version']='6.2'
    path=tmp_path/'mixed.csv'; pd.concat([frame,second]).to_csv(path,index=False)
    data=tmp_path/'data'
    ingest.import_file(path,'MODIS_SP','2023-09-01','2023-09-30',ingest.BBOX,data)
    validate.build(data)
    rows=calendar(Repository(data),Selection(sensor='MODIS',start=date(2023,9,1),end=date(2023,9,30)))
    assert len(rows)==2 and all(r['imported_days']==0 and r['coverage_status']=='unknown' for r in rows)


def test_collection_filtered_to_zero_is_retained(tmp_path,frame):
    data=tmp_path/'data'
    for version,confidence in [('6.1','90'),('6.2','10')]:
        sample=frame.copy(); sample.loc[0,'version']=version; sample.loc[0,'confidence']=confidence
        path=tmp_path/(version+'.csv'); sample.to_csv(path,index=False)
        ingest.import_file(path,'MODIS_SP','2023-09-01','2023-09-30',ingest.BBOX,data)
    validate.build(data)
    rows=calendar(Repository(data),Selection(sensor='MODIS',confidence='strict',start=date(2023,9,1),end=date(2023,9,30)))
    assert [(r['version'],r['value']) for r in rows]==[('6.1',1),('6.2',0)]


def test_explorer_pagination_and_parameter_validation(admin):
    identifier=admin.post('/api/explorer/load',json=PAYLOAD).json()['dataset']
    for params in [{'limit':10001},{'offset':-1},{'offset':1000001},{'confidence':'bad'},{'min_frp':'nan'}]:
        assert admin.get('/api/explorer/view',params={'dataset':identifier,**params}).status_code==422
    result=admin.get('/api/explorer/view',params={'dataset':identifier,'offset':1}).json()
    assert result['records']==[] and result['total']==1 and result['summary']['modis']==1


def test_os_lock_contention(admin,tmp_path):
    from pipeline.locking import exclusive
    with exclusive(tmp_path.parent/'.explorer.lock'):
        assert admin.post('/api/explorer/load',json=PAYLOAD).status_code==409


def test_cors_exact_origin(monkeypatch):
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    # Verify the actual application's configured middleware with an isolated copy.
    configured=next(m for m in app.user_middleware if m.cls is CORSMiddleware)
    assert '*' not in configured.kwargs['allow_origins']
    assert configured.kwargs['allow_methods']==['GET']
    isolated=FastAPI()
    isolated.add_middleware(CORSMiddleware,**{**configured.kwargs,'allow_origins':['https://frontend.example']})
    client=TestClient(isolated)
    for origin,expected in [('https://frontend.example',200),('https://other.example',400)]:
        reply=client.options('/api/regions',headers={'Origin':origin,'Access-Control-Request-Method':'GET'})
        assert reply.status_code==expected


def test_public_view_uses_no_pandas_file_read(admin,monkeypatch):
    identifier=admin.post('/api/explorer/load',json=PAYLOAD).json()['dataset']
    monkeypatch.setattr(explorer.pd,'read_parquet',lambda *a,**k:pytest.fail('whole-file Pandas read'))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:admin.get('/api/explorer/view',params={'dataset':identifier}).status_code,range(2)))
    assert results==[200,200]


def test_download_response_byte_limit(tmp_path,monkeypatch):
    monkeypatch.setenv('FIRMS_MAP_KEY','test-only')
    monkeypatch.setattr(ingest,'MAX_FILE_BYTES',1)
    class Reply:
        status_code=200
        closed=False
        def iter_content(self,size): yield b'too large'
        def close(self): self.closed=True
    reply=Reply()
    class Session:
        def get(self,*args,**kwargs): return reply
    with pytest.raises(ValueError,match='byte budget'):
        ingest.download('MODIS_SP','2023-09-01','2023-09-01',ingest.BBOX,tmp_path,Session())
    assert reply.closed and not list(tmp_path.iterdir())


def test_failed_private_import_removes_staging(tmp_path,frame,monkeypatch):
    monkeypatch.setenv('FIRMS_MAP_KEY','test-only')
    class Reply:
        status_code=200
        def iter_content(self,size): yield frame.to_csv(index=False).encode()
        def close(self): pass
    class Session:
        def get(self,*args,**kwargs): return Reply()
    def fail(*args,**kwargs): raise ValueError('interrupted import')
    monkeypatch.setattr(ingest,'import_file',fail)
    with pytest.raises(ValueError,match='interrupted import'):
        ingest.download('MODIS_SP','2023-09-01','2023-09-01',ingest.BBOX,tmp_path,Session())
    assert not list(tmp_path.iterdir())


def test_cache_writer_enforces_storage_budget(tmp_path,monkeypatch):
    monkeypatch.setattr(explorer,'CACHE',tmp_path)
    monkeypatch.setattr(explorer,'MAX_CACHE_BYTES',4)
    with explorer.CacheFile(tmp_path/'chunk','wb') as handle:
        handle.write(b'1234')
        with pytest.raises(explorer.HTTPException): handle.write(b'5')
    assert explorer.cache_bytes()==4


def test_cleanup_cannot_delete_active_reader(admin,tmp_path):
    from pipeline.locking import exclusive
    identifier=admin.post('/api/explorer/load',json=PAYLOAD).json()['dataset']
    past=time.time()-8*86400; os.utime(tmp_path/identifier,(past,past))
    with exclusive(tmp_path.parent/'.explorer.lock', shared=True):
        assert admin.post('/api/explorer/cleanup').status_code==409
        assert (tmp_path/identifier).exists()
