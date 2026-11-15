import json
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.routers import explorer
from pipeline.clean import clean

def test_selection_limits():
    for args in [dict(start='2023-01-01',end='2023-01-08'),dict(start='2023-01-02',end='2023-01-01')]:
        with pytest.raises(ValueError):
            explorer.LoadRequest(sources=['MODIS_SP'],**args)
    with pytest.raises(ValueError):
        explorer.LoadRequest(sources=['MODIS_SP','MODIS_NRT'],start='2023-01-01',end='2023-01-01')

def test_nrt_explicit_and_native(frame):
    frame.loc[0,'version']='6.1NRT'
    standard,_,_=clean(frame,'MODIS_SP','test','test')
    assert standard.empty
    recent,_,_=clean(frame,'MODIS_SP','test','test',near_real_time=True)
    assert recent.iloc[0].version=='6.1NRT'
    assert recent.iloc[0].confidence_native=='90'

def test_global_download_aggregate_export(tmp_path,frame,monkeypatch):
    monkeypatch.setenv('EXPLORER_HTTP_INGEST_ENABLED','true')
    monkeypatch.setenv('EXPLORER_ADMIN_TOKEN','test-admin')
    monkeypatch.setattr(explorer,'CACHE',tmp_path)
    monkeypatch.setattr(explorer,'availability',lambda:{'records':[{'data_id':'MODIS_SP','min_date':'2000-01-01','max_date':'2026-01-01'}]})
    frame.loc[0,'longitude']='-70'
    frame.loc[0,'latitude']='40'
    monkeypatch.setattr(explorer,'nasa',lambda path:frame.to_csv(index=False).encode())
    c=TestClient(app, headers={"Authorization":"Bearer test-admin"})
    payload={'sources':['MODIS_SP'],'start':'2023-09-01','end':'2023-09-01'}
    result=c.post('/api/explorer/load',json=payload)
    assert result.status_code==200,result.text
    identifier=result.json()['dataset']
    assert c.post('/api/explorer/load',json=payload).json()['dataset']==identifier
    data=c.get('/api/explorer/view',params={'dataset':identifier}).json()
    assert data['total']==1 and data['summary']['modis']==1
    assert data['records'][0]['longitude']==-70
    assert data['records'][0]['cell_id'].startswith('geo01:')
    assert data['daily'][0]['modis']==1 and sum(data['histogram'])==1
    assert c.get('/api/explorer/view',params={'dataset':identifier,'min_frp':20}).json()['total']==0
    assert c.get('/api/explorer/view',params={'dataset':identifier,'sensor':'VIIRS'}).json()['total']==0
    exported=c.get('/api/explorer/export',params={'dataset':identifier})
    assert exported.status_code==200 and 'confidence_native' in exported.text
    assert 'ingestion_timestamp' not in exported.text
    assert c.get('/api/explorer/view?dataset=../../.env').status_code==404
    assert c.post('/api/explorer/load',json={**payload,'start':'1999-01-01','end':'1999-01-01'}).status_code==422
