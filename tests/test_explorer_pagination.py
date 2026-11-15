"""Pagination regression fixtures are synthetic and written only in tmp_path."""
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.routers import explorer


@pytest.mark.parametrize('offset,count,truncated', [
    (0,2,True), (2,2,True), (4,1,False), (5,0,False), (10,0,False),
])
def test_page_has_more_records(tmp_path, monkeypatch, offset, count, truncated):
    identifier = 'a' * 32
    folder = tmp_path / identifier
    folder.mkdir()
    (folder/'metadata.json').write_text(json.dumps({'start':'2023-09-01','end':'2023-09-01'}))
    pd.DataFrame({
        'latitude':[-2.] * 5, 'longitude':[113.] * 5,
        'timestamp_utc':pd.date_range('2023-09-01', periods=5, freq='h', tz='UTC'),
        'sensor':['MODIS'] * 5, 'source_dataset':['MODIS_SP'] * 5,
        'satellite':['T'] * 5, 'version':['6.1'] * 5,
        'confidence_native':['90'] * 5, 'confidence_type':['native_numeric_0_100'] * 5,
        'frp':[12.] * 5, 'cell_id':['geo01:2930:880'] * 5,
        'processing_stream':['standard'] * 5, 'acq_date':['2023-09-01'] * 5,
    }).to_parquet(folder/'observations.parquet', index=False)
    monkeypatch.setattr(explorer, 'CACHE', tmp_path)
    response = TestClient(app).get('/api/explorer/view', params={
        'dataset':identifier, 'limit':2, 'offset':offset,
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body['records']) == count
    assert body['truncated'] is truncated
    assert body['total'] == body['summary']['modis'] == 5
    assert sum(body['histogram']) == 5
