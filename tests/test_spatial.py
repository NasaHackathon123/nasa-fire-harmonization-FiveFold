import pandas as pd
import pytest
from pipeline.spatial import assign_grid
from pipeline.aggregate import aggregate

def test_grid_known_origin_and_repeat():
    rows=pd.DataFrame({"longitude":[111.,111.],"latitude":[0.,0.]})
    grid=assign_grid(rows)
    assert grid.cell_id.tolist()==["32749:500:10000"]*2

def test_projection_guard():
    with pytest.raises(ValueError): assign_grid(pd.DataFrame({"longitude":[0.],"latitude":[0.]}))

def test_month_distinct_vs_daily_sum():
    frame=pd.DataFrame({"month":["2023-09"]*3,"acq_date":["2023-09-01","2023-09-01","2023-09-02"],"cell_id":["a","a","a"]})
    row=aggregate(frame,["month"]).iloc[0]
    assert (row.detections,row.occupied_cells,row.daily_cell_sum)==(3,1,2)
