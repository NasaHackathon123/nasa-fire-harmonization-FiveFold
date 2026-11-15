# Scientific methodology v1

MODIS and VIIRS observations remain distinct by dataset, collection and instrument. Cleaning validates geographic ranges, UTC date/time, satellite/instrument consistency, confidence and standard-processing versions. Exact native duplicate records are removed; nearby observations and separate overpasses remain. Optional missing/invalid FRP, scan, track or day/night values are flagged. FRP is MW and does not measure burned area.

The original confidence field remains intact. MODIS nominal policy uses >=30 and strict uses >=80. VIIRS nominal retains n/h; strict retains h. These application policies are not equivalent probabilities. `/api/quality` compares counts across policies.

Projected coordinates use UTM zone 49 south, EPSG:32749. The 1,000 m cell identifier is floor(easting/1000), floor(northing/1000), with the CRS embedded. Cells include their lower boundaries and exclude upper boundaries. Study-box queries include boundary coordinates. This is a nominal analysis resolution, not matched sensor footprints. Occupancy cannot recover burned area.

Monthly `occupied_cells` counts unique cells over that interval. `daily_cell_sum` sums each day's unique cells. `detections` counts individual accepted observations. Partial boundary months use exactly the requested days. Shared daily cells indicate that both instrument families detected a cell that UTC day, not simultaneous observation or validated equivalence.

Missing months have null metrics. Explicitly declared complete extractions with no retained detections can yield zero retained observations; this never asserts zero fires. Partial months keep observed counts with explicit coverage metadata. No interpolation or extrapolation fills the five-day sample.

Baselines use the median of at least three earlier complete same-calendar months, with the same source, collection, spatial selection, metric and confidence policy. Selected partial months are ineligible. Zero baseline returns an absolute difference and null percentage. Reference years are returned. File completeness is a necessary but insufficient measure of comparability: cloud cover, overpass opportunity and missed detections remain unknown.

Exploratory calibration fits a nonnegative affine relationship from VIIRS to MODIS, holding out the latest year. At least four years, 24 training months, 12 held-out months and variable predictors are required. MAE, bias and correlation are reported. This helper assumes the caller supplies aligned, comparable monthly observations. Seasonal/subregional stability and exposure review remain outstanding; the API never enables calibrated data automatically.
