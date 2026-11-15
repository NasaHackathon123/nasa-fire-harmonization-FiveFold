import numpy as np
from pipeline.harmonize import anomaly,evaluate_candidate

def test_baseline_median():
    result=anomaly(30,[10,20,90])
    assert result["baseline"]==20 and result["percentage_difference"]==50

def test_zero_and_missing():
    assert anomaly(10,[0,0,0])["percentage_difference"] is None
    assert anomaly(10,[0,0,0])["absolute_difference"]==10
    assert anomaly(10,[10,None])["status"]=="insufficient_history"
    assert anomaly(None,[1,2,3])["baseline"] is None

def test_calibration_disabled_for_short_history():
    assert evaluate_candidate([2023]*5,[1]*5,[2]*5)["validated"] is False

def test_heldout_evaluation():
    years=np.repeat([2019,2020,2021,2022],12)
    x=np.tile(np.arange(1,13),4); y=2*x+3
    result=evaluate_candidate(years,x,y)
    assert result["held_out_year"]==2022 and result["train_years"]==[2019,2020,2021]
    assert result["mae"]<1e-8 and result["validated"] is False
