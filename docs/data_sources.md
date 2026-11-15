# NASA source documentation

Checked November 14, 2026:

- [Area API](https://firms.modaps.eosdis.nasa.gov/api/area/): MODIS_SP, VIIRS_SNPP_SP, VIIRS_NOAA20_SP, VIIRS_NOAA21_SP; 1?5 day requests; bounding box west,south,east,north. NASA documents 5,000 transactions per ten-minute interval; request costs can vary.
- [MODIS attributes](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_MODIS_Firehotspots.html): native numeric confidence, pixel FRP, collection and processing version.
- [VIIRS attributes](https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html): native l/n/h confidence, S-NPP/NOAA satellite identifiers and collection metadata.
- [Archive downloads](https://firms.modaps.eosdis.nasa.gov/download/).

Standard products are required for this historical pipeline. No fallback to NRT occurs. Mission coverage and API archive availability are different; historical requests can fail even for a valid source. Header-only valid CSVs describe an empty extraction, not proof of no fire. Invalid API text is rejected.

The existing samples contain 183 MODIS and 806 VIIRS observations on September 1?5, 2023. Their declared extraction area and dates come from the preserved downloader configuration and the project owner's confirmation. Individual files do not measure satellite observation opportunity.
