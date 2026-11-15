# NASA global source assessment

Reviewed 2026-11-15 using official NASA/NOAA public documentation and the mirror publisher's documentation. No NASA credential was used; no new observation or mirror data was downloaded. Existing cached availability was inspected separately and is explicitly not a fresh authenticated NASA check.

## Authoritative products and temporal scope

NASA's current archive page lists the following bounds. 'Present' is a moving service description, not a promise of complete latest SP data. Archive access supports CSV/JSON/shapefile, requires Earthdata or emailed-code authentication, and is asynchronous. NASA says NRT is replaced as science-quality becomes available, approximately five months later. [NASA archive](https://firms.modaps.eosdis.nasa.gov/download/)

| FIRMS family | Published archive scope | Initial project target |
| --- | --- | --- |
| MODIS C6.1 | 2000-11-01 to present | Calendar years 2001-2025; retain late-2000 separately |
| VIIRS S-NPP 375 m | 2012-01-20 to 2026-11-02 | 2012-2025, with 2012 partial mission year |
| VIIRS NOAA-20 375 m | 2018-04-01 to present | Supported portion of 2018-2025 |
| VIIRS NOAA-21 375 m | 2023-03-01 to present | Supported portion of 2023-2025; verify channel-specific backfill |

Do not confuse a platform launch date with a product record start, or an NRT start with an SP archive start. Older NASA training/mirror docs list NOAA-21 beginning 2024-01-17, while the current archive lists 2023-03-01. That discrepancy is material: verify the actual requested SP files and source inventory before promising 2023 NOAA-21 completeness. [NASA 2025 training example](https://appliedsciences.nasa.gov/sites/default/files/2025-07/FIRMS_Part1_QA_Spanish.pdf)

## Collections and native product identity

MOD14 is MODIS/Terra C6.1, archive set 61; Aqua is a separate platform, not available over the entire Terra record. [MOD14 product](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/MOD14)

VIIRS 375 m products are VNP14IMG (S-NPP), VJ114IMG (NOAA-20/JPSS1), VJ214IMG (NOAA-21/JPSS2), with Collection 2 archive set 5200 on the reviewed product pages. Collection identifier, product revision and FIRMS row version are separate fields: retain the delivered string rather than inferring a constant. [VNP14IMG](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP14IMG), [VJ114IMG](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VJ114IMG), [VJ214IMG](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VJ214IMG)

The Collection 2 guide describes changed upstream inputs/quality handling. Do not treat C1 and C2 as an automatically homogeneous time series. The 375 m active-fire product is not the separate 750 m VIIRS product. [NASA VIIRS C2 user guide](https://www.earthdata.nasa.gov/s3fs-public/2025-06/VIIRS_C2_AF-375m_User_Guide_1.2.pdf)

Native row versions encode processing distinctions. The NRT-family product definition explains collection/RT/URT suffixes; a source ending NRT need not contain only NRT rows. [NOAA-21 FIRMS product attributes](https://modaps.modaps.eosdis.nasa.gov/services/about/products/viirs-land-c2-nrt/vj214imgtdl_nrt.html)

## API and alternative access

The Area API accepts world or west,south,east,north and explicit ISO start date, with documented day_range 1..5. It lists separate SP/NRT IDs for MODIS/SNPP/NOAA20/NOAA21. RT/URT rows are removed as NRT supersedes them or when old; private ingestion must preserve their versions. The documented key budget is 5,000 transactions per 10 minutes, with larger requests potentially costing multiple transactions: a request count alone is not the budget. Availability is discoverable per source and must be refreshed at job planning time, privately. [NASA Area API](https://firms.modaps.eosdis.nasa.gov/api/area/), [availability API](https://firms.modaps.eosdis.nasa.gov/api/data_availability/)

For bulk historical work, prefer a separately approved official archive request or file/granule workflow rather than unbounded Area API loops. The API offers convenient small verification windows. LAADS authenticates downloads with appropriate download tokens and exposes native granules; granule conversion would require a distinct verified adapter, not passing HDF/NetCDF into the CSV cleaner. The old LAADS classic API has retired; use documented current services. [LAADS tools](https://ladsweb.modaps.eosdis.nasa.gov/tools-and-services/)

## Local cached availability snapshot (not independently revalidated)

The existing availability.json was checked_at 2026-11-14T09:25:19.001807+00:00. These are cached reported bounds only, not completeness or current remote API confirmation:

| Source | Cached minimum | Cached maximum |
| --- | --- | --- |
| MODIS_SP | 2000-11-01 | 2026-08-31 |
| VIIRS_SNPP_SP | 2012-01-20 | 2026-07-31 |
| VIIRS_NOAA20_SP | 2018-04-01 | 2026-07-31 |
| VIIRS_NOAA21_SP | 2023-03-01 | 2026-07-31 |
| MODIS_NRT | 2026-09-01 | 2026-11-14 |
| VIIRS_SNPP_NRT | 2026-08-01 | 2026-11-02 |
| VIIRS_NOAA20_NRT | 2026-08-01 | 2026-11-14 |
| VIIRS_NOAA21_NRT | 2024-01-17 | 2026-11-14 |

These bounds show why separate historical/recent modes and source-specific coverage are necessary. Min/max do not prove nonoverlap or complete days across every deployment. This review did not test private authenticated requests or retrieve missing SP windows.

## Discontinuities and observation opportunity

S-NPP delivery cessation is documented for November 2, 2026; the updated NOAA notice sets 15:40 UTC, superseding an earlier 13:00 time. The current NASA archive end date agrees at day resolution. Do not show S-NPP as a live continuing recent feed after that date. Historical products remain distinct. [Updated NOAA notice](https://www.nesdis.noaa.gov/news/update-3-cessation-of-suomi-national-polar-orbiting-partnership-s-npp-data-users-november-02-2026-1540-utc-and-decommissioning-issued-october-30-2026-1400-utc)

NASA records an S-NPP lock-up July 27-August 11, 2022 and many shorter gaps; its reviewed outage page is last updated in 2023 and is not a complete current gap inventory. [S-NPP outage ledger](https://modaps.modaps.eosdis.nasa.gov/services/production/outages_npp.html)

Terra/Aqua drift and operational/data-loss events affect sampling. Earlier planning dates are not proof that data actually ceased then: the reviewed Aqua ledger includes November 2026 events. Preserve source-specific outage records and quality metadata instead of hardcoding a retirement inferred from an old plan. [NASA MODIS drift notes](https://landweb.modaps.eosdis.nasa.gov/knownissue?as=61&sat=Terra&sensor=MODIS), [Aqua outages](https://modaps.modaps.eosdis.nasa.gov/services/production/outages_aqua.html)

## Portolan / Source Cooperative comparison

The mirror publisher describes a public cloud-native FIRMS catalog: year-partitioned GeoParquet, temporal/spatial sorting and a combined source table with a quality column, built from API chunks with restartable fetch/build tooling. Its published data is not authoritative NASA storage. Code/catalog metadata and byte-range-friendly files can simplify access, but schema/provenance transformations must be audited. [Publisher repository README](https://raw.githubusercontent.com/portolan-mirrors/firms-catalog/main/README.md)

The collection documentation claims a large global record, hourly recent appends and NOAA-21 beginning January 2024; figures are publisher claims, not independently measured completeness. It warns about incompatible confidence and source-fleet changes. A combined table is usable only with source/platform/collection/quality preserved; default totals are not calibrated sensor-equivalent activity. The repository's nonoverlap assertion is not our reconciliation policy. [Publisher collection documentation](https://raw.githubusercontent.com/portolan-mirrors/firms-catalog/main/catalog/detections/README.md)

The publisher's article describes yearly Parquet/PMTiles, A5 aggregates, and roughly 3-5-hour actual refresh cadence despite hourly scheduling. Those rendering products are not independently validated research aggregates. Its storage-size/cost claims are not this project's measured footprint or budget. [Publisher implementation account](https://www.portolan-sdi.org/blog/building-portolan-firms)

Direct published catalog/collection metadata fetches were unavailable through the research tool in this session; no mirror observation partition was transferred. Thus exact current object inventory, total rows/bytes, gaps, current watermark and NASA-to-mirror equality remain **unverified**, not complete. The published NOAA-21 start discrepancy is a specific acceptance test, not proof of missing records without inspection. [Source Cooperative catalog](https://source.coop/portolan-mirrors/firms-catalog)

Recommendation: NASA is the provenance authority. Treat the mirror as a candidate transport/cache acceleration source only after matched source/collection/stream/date/bbox row-multiset checks, offshore/dateline samples, schema/type/null checks, partition checksums, gap/watermark inspection and refresh/reconciliation tests. A bounded NASA-vs-mirror SP/NRT pilot is a later acceptance gate; the offline local pilot here cannot pass that gate by itself.
