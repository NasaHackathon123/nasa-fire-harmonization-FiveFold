import pandas as pd
import pytest
from pipeline.clean import clean, filter_confidence
from pipeline.ingest import read_csv

def run(frame,source="MODIS_SP"):
    return clean(frame,source,"test","2023-01-01T00:00:00Z")

def test_valid_and_exact_duplicates(frame):
    good,bad,report=run(pd.concat([frame,frame]))
    assert len(good)==1 and len(bad)==0 and report["duplicate_rows_removed"]==1
    assert good.iloc[0].timestamp_utc.hour==3
    assert good.iloc[0].confidence_native=="90"

@pytest.mark.parametrize("column,value",[("latitude","91"),("longitude","nan"),("acq_date","2023-02-30"),("acq_time","2400"),("confidence","101"),("version","6.1NRT"),("satellite","N")])
def test_invalid_quarantined(frame,column,value):
    frame.loc[0,column]=value
    good,bad,report=run(frame)
    assert good.empty and len(bad)==1 and report["rejected_rows"]==1

def test_missing_required(frame):
    with pytest.raises(ValueError): run(frame.drop(columns="confidence"))

def test_distinct_overpasses_preserved(frame):
    second=frame.copy(); second.loc[0,"acq_time"]="0405"
    assert len(run(pd.concat([frame,second]))[0])==2

def test_viirs_native_policy(frame):
    frame.loc[0,["instrument","satellite","confidence","version"]]=["VIIRS","N","n","2.0"]
    good,_,_=run(frame,"VIIRS_SNPP_SP")
    assert good.iloc[0].confidence_native=="n"
    assert len(filter_confidence(good,"nominal"))==1
    assert filter_confidence(good,"strict").empty
    frame.loc[0,"confidence"]="80"
    assert run(frame,"VIIRS_SNPP_SP")[0].empty

def test_missing_frp_flagged(frame):
    frame.loc[0,"frp"]="inf"
    good,_,report=run(frame)
    assert report["flagged_rows"]==1 and pd.isna(good.iloc[0].frp)

@pytest.mark.parametrize("text",["", "latitude,longitude\n1,2,3\n", 'latitude,latitude\n1,2'])
def test_bad_csv(tmp_path,text):
    path=tmp_path/"bad.csv"; path.write_text(text)
    with pytest.raises(ValueError): read_csv(path)

def test_header_only(tmp_path,frame):
    path=tmp_path/"empty.csv"; frame.iloc[:0].to_csv(path,index=False)
    good,_,report=run(read_csv(path))
    assert good.empty and report["original_rows"]==0
