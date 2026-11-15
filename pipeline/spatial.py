"""Metric 1 km grid for the study area, UTM zone 49 south (EPSG:32749)."""
import numpy as np
from pyproj import Transformer

CRS = "EPSG:32749"
TRANSFORM = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)

def assign_grid(frame):
    if not (frame.longitude.between(108, 114) & frame.latitude.between(-80, 0)).all():
        raise ValueError("Grid supports UTM zone 49 south only; review projection before processing other regions")
    result = frame.copy()
    x, y = TRANSFORM.transform(result.longitude.to_numpy(), result.latitude.to_numpy())
    east = np.floor(np.asarray(x) / 1000).astype("int64")
    north = np.floor(np.asarray(y) / 1000).astype("int64")
    result["grid_easting"] = east
    result["grid_northing"] = north
    result["cell_id"] = [f"32749:{a}:{b}" for a, b in zip(east, north)]
    return result

def within(frame, bbox):
    west, south, east, north = bbox
    return frame[frame.longitude.between(west, east) & frame.latitude.between(south, north)].copy()
