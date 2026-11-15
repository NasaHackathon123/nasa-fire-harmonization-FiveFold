"""Read-only adapter from explorer generations to the EmberWatch interface."""
import json
from datetime import date, timedelta

import pandas as pd

from pipeline.config import ROOT
from pipeline.limits import connection
from backend.app.routers import explorer

REGIONS = {
    'sea': [95, -11, 141, 24],
    'johor': [99, 0, 105, 7],
    'sumatra': [95, -6, 106, 6],
    'borneo': [108, -5, 120, 8],
}


def refresh_recent():
    """Private in-process refresh; never expose this as an anonymous HTTP route."""
    available = {r['data_id']: r for r in explorer.refresh_availability()['records']}
    sources = ['MODIS_NRT', 'VIIRS_NOAA20_NRT', 'VIIRS_NOAA21_NRT']
    end = min(date.fromisoformat(available[s]['max_date']) for s in sources)
    start = max(end - timedelta(days=6), *(date.fromisoformat(available[s]['min_date']) for s in sources))
    return explorer.load(explorer.LoadRequest(sources=sources, start=start, end=end, bbox=REGIONS['sea']))


@explorer.cache_read
def build_payload():
    candidates = explorer.CACHE.glob('*/metadata.json') if explorer.CACHE.exists() else []
    metadata = [json.loads(p.read_text()) for p in candidates]
    # Only a dataset covering the complete requested box can establish its window.
    eligible = [m for m in metadata if m['bbox'][0] <= 95 and m['bbox'][1] <= -11
                and m['bbox'][2] >= 141 and m['bbox'][3] >= 24]
    if not eligible:
        return {'regions': {}, 'audit': {}, 'message': 'No Southeast Asia dataset is cached. Configure the server NASA key and refresh.'}
    meta = max(eligible, key=lambda m: (m['end'], m['downloaded_at']))
    path = explorer.CACHE / meta['dataset'] / 'observations.parquet'
    with connection() as db:
        frame = db.execute('SELECT * FROM read_parquet(?) WHERE longitude BETWEEN 95 AND 141 AND latitude BETWEEN -11 AND 24', [str(path)]).df()
    payload = {'regions': {}, 'audit': {}, 'message': f"NASA FIRMS cached observations: {meta['start']} to {meta['end']} UTC. Downloaded {meta['downloaded_at']}. Coverage of clear-sky observation opportunities is unknown. Harmonised scores and historical baselines are unavailable."}
    for region, (west, south, east, north) in REGIONS.items():
        subset = frame[frame.longitude.between(west, east) & frame.latitude.between(south, north)].copy()
        days = {}
        for day in pd.date_range(meta['start'], meta['end']):
            key = str(day.date())
            rows = subset[subset.acq_date.astype(str) == key]
            days[key] = dict(data_covered=True, modis=int((rows.sensor == 'MODIS').sum()),
                             viirs=int((rows.sensor == 'VIIRS').sum()), grid=int(rows.cell_id.nunique()),
                             hai=None, baseline_departure_pct=None,
                             mean_frp_mw=None if rows.frp.dropna().empty else round(float(rows.frp.mean()), 2))
        points = []
        for row in subset.sort_values('timestamp_utc', ascending=False).head(10000).to_dict('records'):
            native = str(row['confidence_native'])
            tier = ('high' if float(native) >= 80 else 'nominal' if float(native) >= 30 else 'low') if row['sensor'] == 'MODIS' else {'h': 'high', 'n': 'nominal', 'l': 'low'}.get(native.lower(), 'low')
            points.append(dict(lat=row['latitude'], lng=row['longitude'], sensor=row['sensor'],
                               satellite=row['satellite'], source_product=row['source_dataset'],
                               date=str(row['timestamp_utc']), confidence=native, confidence_class_derived=tier,
                               frp=None if pd.isna(row['frp']) else row['frp'], brightness=None))
        monthly = {}
        for day, values in days.items():
            bucket = monthly.setdefault(day[:7], dict(month=day[:7], modis=0, viirs=0))
            for sensor in ('modis', 'viirs'):
                bucket[sensor] += values[sensor]
        histogram = [int(((subset.frp >= low) & ((subset.frp < high) if high else True)).sum()) for low, high in [(0,10),(10,25),(25,50),(50,100),(100,None)]]
        bundle = dict(overview=dict(modis_detections=int((subset.sensor == 'MODIS').sum()),
            viirs_detections=int((subset.sensor == 'VIIRS').sum()), occupied_cells_0_10deg=int(subset.cell_id.nunique()),
            latest_acquisition_utc=None if subset.empty else str(subset.timestamp_utc.max()), meta={'is_synthetic': False}),
            hotspots={'hotspots': points, 'meta': {'period': {'from': meta['start'], 'to': meta['end']}}},
            calendar_0_10={'days': days})
        bundle['calendar_0.10'] = bundle.pop('calendar_0_10')
        bundle['analytics'] = dict(daily_series_last_90d=[dict(date=d, **v) for d,v in days.items()],
            monthly_sensor_comparison=list(monthly.values()), weekly_anomalies=[],
            frp_distribution=[dict(bin=b, count=c) for b,c in zip(['0–10','10–25','25–50','50–100','100+'], histogram)])
        # Exports contain every regional row, even when the map is capped.
        fields = ['latitude','longitude','timestamp_utc','sensor','source_dataset','satellite','version','confidence_native','frp','cell_id']
        bundle['csv_text'] = subset[fields].to_csv(index=False)
        bundle['map_note'] = f"Showing up to 10,000 newest markers of {len(subset):,} observations. Charts and CSV include all rows."
        payload['regions'][region] = bundle
    reports = meta.get('reports', [])
    totals = {k: sum(r.get(k, 0) for r in reports) for k in ['original_rows','accepted_rows','rejected_rows','duplicate_rows_removed','flagged_rows']}
    payload['audit'] = dict(raw_records_loaded=totals['original_rows'], cleaned_records_retained=totals['accepted_rows'],
        quarantined_records=totals['rejected_rows'], exact_duplicates_not_inserted=totals['duplicate_rows_removed'],
        retained_with_qc_flags=totals['flagged_rows'], silent_discards=0,
        reconciled=totals['original_rows'] == totals['accepted_rows']+totals['rejected_rows']+totals['duplicate_rows_removed'])
    return payload


def render_dashboard(payload):
    html = (ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')
    # Prevent data containing HTML from terminating the inline script element.
    serialized = json.dumps(payload, allow_nan=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    return html.replace('__PAYLOAD_JSON__', serialized)
