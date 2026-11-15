"""Synthetic regression tests for the isolated offline pilot; never production observations."""
import json
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from experiments.global_pilot import import_day, checksum, stream_for

BOXES={'west':[-125,30,-110,50],'east':[20,-25,35,-10]}


def test_streaming_global_idempotence_and_source_preservation(tmp_path,frame):
    first=frame.copy();first.loc[0,['longitude','latitude']]=['-120','40']
    second=frame.copy();second.loc[0,['longitude','latitude']]=['25','-20']
    second.loc[0,'acq_time']='0005'
    wrong_day=first.copy();wrong_day.loc[0,'acq_date']='2023-09-02'
    viirs=second.copy();viirs.loc[0,['instrument','satellite','confidence','version']]=['VIIRS','N21','h','2.0NRT']
    modis=tmp_path/'modis.csv';pd.concat([first,second,first,wrong_day]).to_csv(modis,index=False)
    other=tmp_path/'viirs.csv';viirs.to_csv(other,index=False)
    original=checksum(modis)
    inputs=[(modis,'MODIS_SP'),(other,'VIIRS_NOAA21_NRT')]
    manifest=import_day(inputs,'2023-09-01',BOXES,tmp_path/'pilot',batch_rows=1)
    assert manifest['selected_rows']==3 and manifest['scanned_rows']==5
    assert manifest['exact_duplicates_removed']==1 and manifest['coverage_status']=='unknown'
    assert import_day(inputs,'2023-09-01',BOXES,tmp_path/'pilot',batch_rows=2)==manifest
    paths=[str(tmp_path/'pilot'/manifest['job']/p['path']) for p in manifest['parts']]
    with duckdb.connect() as db:
        db.execute("SET TimeZone='UTC'")
        rows=db.execute('SELECT source_dataset,version,processing_stream,CAST(timestamp_utc AS VARCHAR),longitude,latitude FROM read_parquet(?, hive_partitioning=false) ORDER BY source_dataset,latitude',[paths]).fetchall()
    assert len(rows)==3
    assert rows[-1][:3]==('VIIRS_NOAA21_NRT','2.0NRT','near-real-time')
    assert any('00:05' in r[3] for r in rows)
    assert checksum(modis)==original
    with pytest.raises(ValueError,match='byte budget'):
        import_day(inputs,'2023-09-01',BOXES,tmp_path/'pilot',max_output_bytes=1)


def test_same_record_in_multiple_files_deduplicates(tmp_path,frame):
    one=tmp_path/'one.csv';two=tmp_path/'two.csv'
    frame.to_csv(one,index=False);frame.to_csv(two,index=False)
    m=import_day([(one,'MODIS_SP'),(two,'MODIS_SP')],'2023-09-01',{'box':[112,-3,114,-1]},tmp_path/'out',batch_rows=1)
    assert m['selected_rows']==1 and m['exact_duplicates_removed']==1


@pytest.mark.parametrize('kw',[{'max_file_bytes':1},{'max_scanned_rows':1},{'max_output_rows':1},{'max_output_bytes':1}])
def test_limits_cleanup_and_originals(tmp_path,frame,kw):
    second=frame.copy();second.loc[0,'acq_time']='0600'
    path=tmp_path/'input.csv';pd.concat([frame,second]).to_csv(path,index=False)
    old=checksum(path)
    with pytest.raises(ValueError,match='budget'):
        import_day([(path,'MODIS_SP')],'2023-09-01',{'box':[112,-3,114,-1]},tmp_path/'out',batch_rows=1,**kw)
    assert checksum(path)==old
    assert not list((tmp_path/'out').glob('.incomplete-*'))
    assert not list((tmp_path/'out').glob('*/manifest.json'))


def test_zero_extract_rejected_coordinates_and_no_fake_coverage(tmp_path,frame):
    path=tmp_path/'input.csv';frame.iloc[:0].to_csv(path,index=False)
    m=import_day([(path,'MODIS_SP')],'2023-09-01',BOXES,tmp_path/'out')
    assert m['selected_rows']==0 and m['coverage_status']=='unknown' and m['parts']==[]
    frame.loc[0,'latitude']='999';frame.to_csv(path,index=False)
    m=import_day([(path,'MODIS_SP')],'2023-09-01',BOXES,tmp_path/'out')
    assert m['selected_rows']==0 and m['rejected_day_rows']==1


def test_integrity_failure_does_not_relabel_complete(tmp_path,frame):
    path=tmp_path/'input.csv';frame.to_csv(path,index=False)
    m=import_day([(path,'MODIS_SP')],'2023-09-01',{'box':[112,-3,114,-1]},tmp_path/'out')
    part=tmp_path/'out'/m['job']/m['parts'][0]['path'];part.write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='integrity'):
        import_day([(path,'MODIS_SP')],'2023-09-01',{'box':[112,-3,114,-1]},tmp_path/'out')


@pytest.mark.parametrize('version,source,expected',[
    ('2.0URT','VIIRS_NOAA21_NRT','ultra-real-time'),('2.0RT','VIIRS_NOAA21_NRT','real-time'),
    ('2.0NRT','VIIRS_NOAA21_NRT','near-real-time'),('6.1','MODIS_SP','standard'),
    ('unknown','MODIS_NRT','unspecified-recent')])
def test_row_level_stream_versions(version,source,expected):
    assert stream_for(version,source)==expected


def test_invalid_input_and_geography(tmp_path,frame):
    path=tmp_path/'input.csv';frame.to_csv(path,index=False)
    for source,boxes in [('UNKNOWN',BOXES),('MODIS_SP',{'cross':[170,-10,-170,10]})]:
        with pytest.raises(ValueError):import_day([(path,source)],'2023-09-01',boxes,tmp_path/'out')
    path.write_text('latitude,latitude\n1,2\n')
    with pytest.raises(ValueError,match='headers'):import_day([(path,'MODIS_SP')],'2023-09-01',BOXES,tmp_path/'out')


def test_streams_are_not_deduplicated_together(tmp_path,frame):
    path=tmp_path/'input.csv';frame.to_csv(path,index=False)
    m=import_day([(path,'MODIS_SP'),(path,'MODIS_NRT')],'2023-09-01',{'box':[112,-3,114,-1]},tmp_path/'out')
    assert m['selected_rows']==2 and m['exact_duplicates_removed']==0


def test_interrupted_job_preserves_prior_output(tmp_path,frame,monkeypatch):
    from pipeline.locking import exclusive
    path=tmp_path/'input.csv';frame.to_csv(path,index=False)
    out=tmp_path/'out'
    m=import_day([(path,'MODIS_SP')],'2023-09-01',{'box':[112,-3,114,-1]},out)
    with exclusive(out/'.pilot.lock'):
        with pytest.raises(ValueError,match='running'):
            import_day([(path,'MODIS_SP')],'2023-09-01',BOXES,out)
    def fail(*a,**k): raise RuntimeError('interrupted write')
    monkeypatch.setattr(pd.DataFrame,'to_parquet',fail)
    with pytest.raises(RuntimeError,match='interrupted'):
        import_day([(path,'MODIS_SP')],'2023-09-01',{'newbox':[110,-4,115,0]},out)
    assert not list(out.glob('.incomplete-*'))
    assert (out/m['job']/'manifest.json').exists()
