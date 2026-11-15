"""File-backed repository: business logic does not depend on API routes.
Each instance pins one immutable generation; parameterized DuckDB queries bound reads.
"""
from datetime import timedelta
import json
from pathlib import Path
from pipeline.limits import connection
import pandas as pd
from pipeline.config import DATA, REGIONS, SOURCES

class DataUnavailable(Exception):
    pass

class Repository:
    def __init__(self, data_dir=DATA):
        pointer = Path(data_dir) / "processed" / "CURRENT.json"
        if not pointer.exists():
            raise DataUnavailable("No processed data; run the ingestion and pipeline commands")
        generation = json.loads(pointer.read_text())["generation"]
        if not generation.isalnum():
            raise DataUnavailable("Invalid processed-data generation")
        self.path = Path(data_dir) / "processed" / generation
        if not (self.path / "clean_observations.parquet").exists():
            raise DataUnavailable("Processed data is incomplete; rebuild the pipeline")
        self.inventory = json.loads((self.path / "data_sources.json").read_text())
        self.report = json.loads((self.path / "cleaning_report.json").read_text())

    def query(self, sql, parameters):
        with connection() as db:
            return db.execute(sql, parameters).df()

    def filters(self, selection, bbox=None):
        west, south, east, north = REGIONS[selection.region]["bbox"]
        if bbox:
            west, south, east, north = max(west,bbox[0]), max(south,bbox[1]), min(east,bbox[2]), min(north,bbox[3])
        where = "longitude BETWEEN ? AND ? AND latitude BETWEEN ? AND ? AND acq_date BETWEEN ? AND ?"
        args = [west,east,south,north,str(selection.start),str(selection.end)]
        if selection.sensor != "all":
            where += " AND sensor = ?"
            args.append(selection.sensor)
        if selection.source:
            where += " AND source_dataset = ?"
            args.append(selection.source)
        if selection.min_frp > 0:
            where += " AND frp >= ?"
            args.append(selection.min_frp)
        if selection.confidence != "all":
            where += " AND ((sensor='MODIS' AND TRY_CAST(confidence_native AS DOUBLE)>=?) OR (sensor='VIIRS' AND lower(confidence_native) IN (" + ("'h'" if selection.confidence == "strict" else "'n','h'") + ")))"
            args.append(80 if selection.confidence == "strict" else 30)
        return where, args

    def observations(self, selection, limit=1000, offset=0, bbox=None):
        where, args = self.filters(selection, bbox)
        file = str(self.path / "clean_observations.parquet")
        total = int(self.query("SELECT count(*) AS n FROM read_parquet(?) WHERE " + where,[file,*args]).iloc[0].n)
        fields = "latitude,longitude,CAST(timestamp_utc AS VARCHAR) AS timestamp_utc,sensor,source_dataset,satellite,instrument,version,confidence_native,confidence_type,frp,daynight,scan,track,cell_id,raw_source_id,quality_flags"
        rows = self.query("SELECT " + fields + " FROM read_parquet(?) WHERE " + where + " ORDER BY timestamp_utc,source_dataset,latitude,longitude,raw_source_id LIMIT ? OFFSET ?", [file,*args,limit,offset])
        return json.loads(rows.to_json(orient="records")), total

    def summaries(self, selection):
        # Precomputed summaries are valid for whole calendar months. For boundary
        # months, recalculate exactly the selected days from Parquet in DuckDB.
        file = str(self.path / "monthly_summaries.parquet")
        clauses = "region=? AND confidence_policy=? AND month BETWEEN ? AND ?"
        args = [selection.region, selection.confidence, str(selection.start)[:7], str(selection.end)[:7]]
        if selection.sensor != "all":
            clauses += " AND sensor=?"
            args.append(selection.sensor)
        if selection.source:
            clauses += " AND source_dataset=?"
            args.append(selection.source)
        result = self.query("SELECT * FROM read_parquet(?) WHERE " + clauses, [file,*args])
        where, values = self.filters(selection)
        partial_months = []
        if selection.start.day != 1:
            partial_months.append(str(selection.start)[:7])
        if selection.end.day != pd.Period(str(selection.end)[:7]).days_in_month:
            partial_months.append(str(selection.end)[:7])
        if selection.min_frp > 0:
            partial_months = list(pd.period_range(selection.start, selection.end, freq="M").astype(str))
        if partial_months:
            raw = str(self.path / "clean_observations.parquet")
            replacement = self.query("SELECT source_dataset,sensor,version,substr(acq_date,1,7) AS month,count(*) AS detections,count(DISTINCT cell_id) AS occupied_cells,count(DISTINCT acq_date || ':' || cell_id) AS daily_cell_sum FROM read_parquet(?) WHERE " + where + " GROUP BY source_dataset,sensor,version,month", [raw,*values])
            result = pd.concat([result[~result.month.isin(partial_months)],replacement[replacement.month.isin(partial_months)]],ignore_index=True)
        return result

    @staticmethod
    def covers_region(item, region):
        box = item.get('bbox')
        west, south, east, north = REGIONS[region]['bbox']
        return bool(box and box[0] <= west and box[1] <= south and box[2] >= east and box[3] >= north)

    def imported_dates(self, source, region, version=None, start=None, end=None):
        west,south,east,north = REGIONS[region]["bbox"]
        dates = set()
        for item in self.inventory:
            # A mixed-version file cannot establish per-collection completeness.
            if item.get('dataset_versions', []) != ([] if version is None else [version]):
                continue
            box = item.get("bbox")
            if item["source"] != source or not item.get("coverage_start") or not box:
                continue
            if not (box[0] <= west and box[1] <= south and box[2] >= east and box[3] >= north):
                continue
            # Rejected records make the file unsuitable for complete-month baselines.
            report = next((r for r in self.report["sources"] if r["source_id"] == item["id"]), {})
            if report.get("rejected_rows", 1):
                continue
            begin = max(item['coverage_start'], str(start)) if start else item['coverage_start']
            finish = min(item['coverage_end'], str(end)) if end else item['coverage_end']
            if begin <= finish:
                dates.update(x.date() for x in pd.date_range(begin, finish))
        return dates

    def overlap(self, selection):
        where,args = self.filters(selection)
        file = str(self.path / "clean_observations.parquet")
        # Daily pairing avoids claiming two sensors observed a cell simultaneously.
        return self.query("SELECT acq_date,count(*) AS shared_daily_cells FROM (SELECT acq_date,cell_id FROM read_parquet(?) WHERE " + where + " GROUP BY acq_date,cell_id HAVING count(DISTINCT sensor)=2) GROUP BY acq_date ORDER BY acq_date", [file,*args]).to_dict(orient="records")
