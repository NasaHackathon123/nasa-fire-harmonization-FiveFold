"""Exploratory calibration with chronological held-out evaluation; never auto-published."""
import numpy as np
from scipy.optimize import nnls

def evaluate_candidate(years, viirs, modis):
    years, x, y = np.asarray(years), np.asarray(viirs, float), np.asarray(modis, float)
    if len(years) != len(x) or len(x) != len(y) or not np.isfinite(x).all() or not np.isfinite(y).all() or (x < 0).any() or (y < 0).any():
        raise ValueError("Aligned finite nonnegative observations are required")
    unique = np.unique(years)
    if len(unique) < 4:
        return {"status": "insufficient_history", "validated": False, "reason": "At least four overlapping years required"}
    test = years == unique[-1]
    train = ~test
    if train.sum() < 24 or test.sum() < 12 or np.std(x[train]) == 0:
        return {"status": "insufficient_history", "validated": False, "reason": "Need 24 training months, 12 held-out months and variable predictors"}
    design = np.column_stack([x, np.ones(len(x))])
    coefficients, _ = nnls(design[train], y[train])
    predicted = design[test] @ coefficients
    error = predicted - y[test]
    correlation = float(np.corrcoef(predicted, y[test])[0, 1]) if np.std(predicted) > 0 and np.std(y[test]) > 0 else None
    return {"status": "exploratory_only", "validated": False, "train_years": unique[:-1].tolist(), "held_out_year": int(unique[-1]),
            "slope": float(coefficients[0]), "intercept": float(coefficients[1]), "mae": float(np.abs(error).mean()), "bias": float(error.mean()),
            "seasonal_correlation": correlation, "reason": "Subregion stability, coverage and independent scientific review remain required"}

def anomaly(observed, reference_values, minimum_years=3):
    valid = [float(x) for x in reference_values if x is not None and np.isfinite(x)]
    if observed is None or len(valid) < minimum_years:
        return {"baseline": None, "absolute_difference": None, "percentage_difference": None, "status": "insufficient_history"}
    baseline = float(np.median(valid))
    return {"baseline": baseline, "absolute_difference": float(observed - baseline),
            "percentage_difference": None if baseline == 0 else float((observed - baseline) / baseline * 100),
            "status": "zero_baseline" if baseline == 0 else "available"}
