"""Synthetic fixtures are isolated to tests; production uses imported NASA data."""
import pandas as pd
import pytest

@pytest.fixture
def observation():
    return dict(latitude="-2", longitude="113", acq_date="2023-09-01", acq_time="0305", satellite="T", instrument="MODIS", confidence="90", version="6.1", frp="12", scan="1", track="1", daynight="D")

@pytest.fixture
def frame(observation):
    return pd.DataFrame([observation])
