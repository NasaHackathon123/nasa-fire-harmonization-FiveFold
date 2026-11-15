"""Source-aware validation. Original columns survive alongside derived fields."""
import pandas as pd
import numpy as np
from .config import SOURCES, VERSION

REQUIRED = {"latitude", "longitude", "acq_date", "acq_time", "satellite", "instrument", "confidence", "version"}

def clean(frame, source, raw_id, ingested_at, *, near_real_time=False):
    if source not in SOURCES:
        raise ValueError("Unsupported standard-processing source")
    missing = REQUIRED - set(frame.columns)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
    frame = frame.copy().reset_index(drop=True)
    original = len(frame)
    missing_counts = {k: int(v) for k, v in frame.isna().sum().items()}
    duplicates = frame.duplicated(keep="first")
    duplicate_count = int(duplicates.sum())
    frame = frame.loc[~duplicates].copy()
    reasons = pd.Series("", index=frame.index, dtype="str")
    def reject(mask, reason):
        nonlocal reasons
        reasons = reasons + mask.fillna(True).map({True: reason + ";", False: ""})
    for col, low, high in [("latitude", -90, 90), ("longitude", -180, 180)]:
        values = pd.to_numeric(frame[col], errors="coerce")
        reject(~values.between(low, high), "invalid_" + col)
        frame[col] = values
    time = frame.acq_time.astype("str").str.strip().str.zfill(4)
    date = frame.acq_date.astype("str")
    timestamp = pd.to_datetime(date + " " + time, format="%Y-%m-%d %H%M", errors="coerce", utc=True)
    reject(timestamp.isna() | ~time.str.fullmatch(r"[0-9]{4}") | ~date.str.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}"), "invalid_timestamp")
    frame["timestamp_utc"] = timestamp
    frame["confidence_native"] = frame.confidence
    sensor = SOURCES[source]
    if sensor == "MODIS":
        native = pd.to_numeric(frame.confidence, errors="coerce")
        reject(~native.between(0, 100), "invalid_modis_confidence")
        frame["confidence_type"] = "native_numeric_0_100"
        reject(frame.instrument.str.upper() != "MODIS", "instrument_mismatch")
        reject(~frame.satellite.str.upper().isin(["T", "A", "TERRA", "AQUA"]), "satellite_mismatch")
    else:
        reject(~frame.confidence.str.lower().isin(["l", "n", "h"]), "invalid_viirs_confidence")
        frame["confidence_type"] = "native_category_l_n_h"
        reject(frame.instrument.str.upper() != "VIIRS", "instrument_mismatch")
        expected = {"VIIRS_SNPP_SP": ["N", "SUOMI-NPP", "SNPP"], "VIIRS_NOAA20_SP": ["N20", "NOAA-20"], "VIIRS_NOAA21_SP": ["N21", "NOAA-21"]}[source]
        reject(~frame.satellite.str.upper().isin(expected), "satellite_mismatch")
    reject(frame.version.isna() if near_real_time else frame.version.isna() | frame.version.str.contains("NRT|URT|RT", case=False, na=True), "non_standard_or_missing_version")
    frame["quality_flags"] = ""
    for col in ["frp", "scan", "track"]:
        if col not in frame:
            frame[col] = float("nan")
        values = pd.to_numeric(frame[col], errors="coerce")
        bad = ~np.isfinite(values) | (values < 0)
        frame.loc[bad, "quality_flags"] += "missing_or_invalid_" + col + ";"
        frame[col] = values.mask(bad)
    if "daynight" not in frame:
        frame["daynight"] = ""
    frame.loc[~frame.daynight.isin(["D", "N"]), "quality_flags"] += "unknown_daynight;"
    frame["sensor"] = sensor
    frame["source_dataset"] = source
    frame["raw_source_id"] = raw_id
    frame["ingestion_timestamp"] = ingested_at
    frame["processing_version"] = VERSION
    frame["acq_date"] = timestamp.dt.strftime("%Y-%m-%d")
    frame["acq_time"] = time
    frame["rejection_reasons"] = reasons
    accepted = frame[reasons == ""].drop(columns="rejection_reasons").copy()
    rejected = frame[reasons != ""].copy()
    report = {"original_rows": original, "accepted_rows": len(accepted), "rejected_rows": len(rejected), "duplicate_rows_removed": duplicate_count,
              "flagged_rows": int((accepted.quality_flags != "").sum()), "missing_values": missing_counts,
              "rejection_reasons": reasons[reasons != ""].value_counts().to_dict()}
    return accepted, rejected, report

def filter_confidence(frame, policy):
    if policy not in ["all", "nominal", "strict"]:
        raise ValueError("Unknown confidence policy")
    if policy == "all":
        return frame.copy()
    modis = frame.sensor == "MODIS"
    numerical = pd.to_numeric(frame.confidence_native, errors="coerce")
    mask = (modis & (numerical >= (80 if policy == "strict" else 30))) | (~modis & frame.confidence_native.str.lower().isin(["h"] if policy == "strict" else ["n", "h"]))
    return frame[mask].copy()
