import json
import pytest
from pipeline.ingest import import_file,download,BBOX
from pipeline.validate import build

def test_duplicate_import_and_reproducibility(tmp_path,frame):
    path=tmp_path/"input.csv"; frame.to_csv(path,index=False)
    data=tmp_path/"data"
    one=import_file(path,"MODIS_SP","2023-09-01","2023-09-01",BBOX,data)
    two=import_file(path,"MODIS_SP","2023-09-01","2023-09-01",BBOX,data)
    assert one==two
    assert len(json.loads((data/"raw/manifest.json").read_text()))==1
    assert build(data)==build(data)
    raw=data/"raw"/one["filename"]; raw.write_text("changed")
    with pytest.raises(ValueError,match="checksum"): build(data)

def test_rate_limit_and_chunking(tmp_path,frame,monkeypatch):
    monkeypatch.setenv("FIRMS_MAP_KEY","TEST_ONLY_KEY")
    class Response:
        status_code=200; headers={}
        text=frame.iloc[:0].to_csv(index=False)
        content=text.encode()
        def iter_content(self, size): return iter([self.content])
        def close(self): pass
    class Session:
        def __init__(self): self.calls=[]
        def get(self,url,timeout,stream=False):
            self.calls.append(url)
            response=Response()
            if len(self.calls)==1: response.status_code=429; response.headers={"Retry-After":"1"}
            return response
    session=Session(); sleeps=[]
    # Identical empty responses across chunks need distinct coverage registration;
    # importer intentionally rejects conflicting declarations rather than relabeling.
    results=download("MODIS_SP","2023-09-01","2023-09-06",BBOX,tmp_path,session,sleeps.append)
    assert len(results)==2 and len(session.calls)==3 and sleeps==[1,1]

def test_invalid_source():
    with pytest.raises(ValueError): download("MODIS_NRT","2023-09-01","2023-09-02",BBOX)
