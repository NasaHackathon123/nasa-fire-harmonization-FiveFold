"""Sensor-separated daily and monthly gold summaries, never incident counts."""
import pandas as pd
from .clean import filter_confidence
from .config import REGIONS, POLICIES, METHOD
from .spatial import within

def aggregate(frame, keys):
    if frame.empty:
        return pd.DataFrame(columns=keys + ["detections", "occupied_cells", "daily_cell_sum"])
    groups = frame.groupby(keys, dropna=False)
    result = groups.agg(detections=("cell_id", "size"), occupied_cells=("cell_id", "nunique")).reset_index()
    daily = frame.drop_duplicates(keys + ["acq_date", "cell_id"]).groupby(keys).size().rename("daily_cell_sum").reset_index()
    return result.merge(daily, on=keys)

def gold(frame):
    daily, monthly = [], []
    for region, definition in REGIONS.items():
        local = within(frame, definition["bbox"])
        for policy in POLICIES:
            selected = filter_confidence(local, policy)
            selected["month"] = selected.acq_date.str[:7]
            for key, output in [("acq_date", daily), ("month", monthly)]:
                summary = aggregate(selected, ["source_dataset", "sensor", "version", key])
                summary["region"] = region
                summary["confidence_policy"] = policy
                summary["method"] = METHOD
                output.append(summary)
    return pd.concat(daily, ignore_index=True), pd.concat(monthly, ignore_index=True)
