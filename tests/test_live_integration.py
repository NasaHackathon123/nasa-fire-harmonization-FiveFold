import os
import pytest
pytestmark = pytest.mark.skipif(os.environ.get("FIRE_LIVE_TEST") != "1", reason="Requires locally running server; set FIRE_LIVE_TEST=1")
import httpx

def test_live_backend():
    with httpx.Client(base_url='http://127.0.0.1:8000') as c:
        assert c.get('/api/health').status_code == 200
        assert c.get('/docs').status_code == 200
        q={'start':'2023-09-01','end':'2023-09-05','limit':5000}
        records=c.get('/api/hotspots',params=q).json()['records']
        assert len(records)==989
        assert all(112<=r['longitude']<=114 and -3<=r['latitude']<=-1 for r in records)
        for sensor,n in [('MODIS',183),('VIIRS',806)]:
            result=c.get('/api/hotspots',params={**q,'sensor':sensor}).json()
            assert result['total']==n
            assert all(r['sensor']==sensor for r in result['records'])
        filtered=c.get('/api/hotspots',params={**q,'min_frp':50}).json()
        assert filtered['total']==sum(r['frp'] is not None and r['frp']>=50 for r in records)
        west=c.get('/api/hotspots',params={**q,'region':'central-kalimantan-west'}).json()
        assert west['total']==sum(r['longitude']<=113 for r in records)
        assert c.get('/api/hotspots',params={**q,'start':'2026-01-01','end':'2026-12-31'}).json()['total']==0
        assert c.get('/api/export',params=q).status_code==200
        for path in ['/api/health','/api/quality','/api/methodology']:
            response=c.get(path)
            assert response.status_code==200
            assert 'FIRMS_MAP_KEY' not in response.text
