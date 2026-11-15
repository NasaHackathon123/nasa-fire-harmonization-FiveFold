import csv
import io
from datetime import date
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.routers.api import repository
from backend.app.database.repository import Repository
from pipeline.ingest import import_file,BBOX
from pipeline.validate import build

@pytest.fixture
def client(tmp_path,frame):
    path=tmp_path/"source.csv"; frame.to_csv(path,index=False)
    data=tmp_path/"data"
    import_file(path,"MODIS_SP","2023-09-01","2023-09-05",BBOX,data)
    build(data)
    app.dependency_overrides[repository]=lambda:Repository(data)
    yield TestClient(app,raise_server_exceptions=False)
    app.dependency_overrides.clear()

@pytest.mark.parametrize("endpoint",["health","regions","calendar","trends","hotspots","anomalies","quality","methodology","comparison","export"])
def test_routes(client,endpoint):
    response=client.get('/api/'+endpoint)
    assert response.status_code==200, response.text

def test_backend_has_no_frontend_dependency(client):
    assert client.get('/docs').status_code == 200
    assert client.get('/').status_code == 404
    assert client.get('/static/app.js').status_code == 404
    paths = client.get('/openapi.json').json()['paths']
    assert '/api/hotspots' in paths and '/api/explorer/view' in paths

@pytest.mark.parametrize("query,status",[("start=2024-01-01&end=2023-01-01",422),("region=unknown",404),("method=harmonized",409),("sensor=invalid",422),("method=raw",422)])
def test_invalid(client,query,status):
    assert client.get('/api/calendar?'+query).status_code==status

def test_missing_and_partial_calendar(client):
    rows=client.get('/api/calendar?sensor=MODIS').json()["records"]
    assert rows[0]["value"] is None and rows[0]["coverage_status"]=="unavailable"
    sept=rows[8]
    assert sept["detections"]==1 and sept["imported_days"]==5
    assert sept["coverage_status"]=="partial" and sept["baseline"] is None

def test_pagination_bbox_and_export(client):
    result=client.get('/api/hotspots?limit=1').json()
    assert result["total"]==1 and len(result["records"])==1
    assert client.get('/api/hotspots?bbox=0,0,1,1').json()["total"]==0
    assert client.get('/api/hotspots?limit=5001').status_code==422
    assert client.get('/api/hotspots?bbox=bad').status_code==422
    export=client.get('/api/export')
    rows=list(csv.DictReader(io.StringIO(export.text)))
    assert rows and rows[0]["baseline"]=="" and rows[0]["confidence"]=="all"

def test_partial_range(client):
    rows=client.get('/api/calendar?sensor=MODIS&start=2023-09-02&end=2023-09-05').json()["records"]
    assert rows[0]["detections"]==0 and rows[0]["anomaly_status"]=="incomplete_month"


def test_complete_history_baseline(tmp_path,frame):
    data=tmp_path/"history"
    for year in [2019,2020,2021,2022]:
        sample=frame.copy(); sample.loc[0,"acq_date"]=f"{year}-09-01"
        path=tmp_path/f"{year}.csv"; sample.to_csv(path,index=False)
        import_file(path,"MODIS_SP",f"{year}-09-01",f"{year}-09-30",BBOX,data)
    build(data)
    app.dependency_overrides[repository]=lambda:Repository(data)
    try:
        client=TestClient(app)
        rows=client.get('/api/anomalies?sensor=MODIS&start=2022-09-01&end=2022-09-30').json()["records"]
        assert rows[0]["baseline"]==1 and rows[0]["percentage_difference"]==0
        assert rows[0]["reference_years"]==[2019,2020,2021]
    finally:
        app.dependency_overrides.clear()
