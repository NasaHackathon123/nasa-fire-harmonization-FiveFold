from datetime import date
import pandas as pd
from pipeline.config import METHOD, VERSION, SOURCES
from pipeline.harmonize import anomaly

WARNINGS = [
    "Hotspot observations are not verified individual wildfire incidents.",
    "No detection does not establish absence of fire; cloud and overpass coverage are not measured.",
    "Import completeness describes supplied files, not clear-sky observation opportunity.",
    "Raw sensor counts and native confidence filters are not scientifically equivalent.",
]

def metadata(selection):
    return {**selection.model_dump(), "processing_version": VERSION, "method": METHOD if selection.method == "common-grid" else "native-observations-v1", "warnings": WARNINGS}

def calendar(repository, selection, include_anomalies=True):
    summary = repository.summaries(selection)
    sources = [s for s in SOURCES if (selection.sensor == "all" or SOURCES[s] == selection.sensor) and (not selection.source or selection.source == s)]
    # Only the two initial primary families appear when no extension is imported.
    registered = {x["source"] for x in repository.inventory} | {"MODIS_SP", "VIIRS_SNPP_SP"}
    sources = [s for s in sources if s in registered]
    records = []
    for source in sources:
        for month in pd.period_range(selection.start, selection.end, freq="M"):
            month_start, month_end = month.start_time.date(), month.end_time.date()
            begin, finish = max(month_start, selection.start), min(month_end, selection.end)
            days = set(x.date() for x in pd.date_range(begin, finish))
            values = summary[(summary.source_dataset == source) & (summary.month == str(month))]
            # Keep versions separate: changes of collection never silently become one series.
            versions = sorted(set(values.version.dropna().unique()) | {
                v for item in repository.inventory
                if item['source'] == source and repository.covers_region(item, selection.region)
                and item.get('coverage_start') and item['coverage_start'] <= str(finish)
                and item['coverage_end'] >= str(begin)
                for v in item['dataset_versions']
            }) or [None]
            for version in versions:
                known = repository.imported_dates(source, selection.region, version, begin, finish)
                imported = len(days & known)
                row = values[values.version == version] if version is not None else values
                observed = not row.empty
                coverage = "complete" if imported == len(days) else "partial" if imported else "unknown" if observed else "unavailable"
                entry = {"month": str(month), "source": source, "sensor": SOURCES[source], "version": version,
                         "coverage_status": coverage, "imported_days": imported, "selected_days": len(days)}
                for metric in ["detections", "occupied_cells", "daily_cell_sum"]:
                    entry[metric] = int(row[metric].sum()) if observed else 0 if imported == len(days) else None
                entry["value"] = entry[selection.metric]
                entry.update({"baseline": None, "absolute_difference": None, "percentage_difference": None, "anomaly_status": "insufficient_history", "reference_years": []})
                if include_anomalies and coverage == "complete" and begin == month_start and finish == month_end and len(versions) == 1 and version is not None:
                    history_start = min((i.get("coverage_start") for i in repository.inventory if i.get("coverage_start")),default=str(selection.start))
                    prior = selection.model_copy(update={"start": date.fromisoformat(history_start), "end": date(month.year-1,12,31)})
                    if prior.start <= prior.end:
                        history = calendar(repository, prior, include_anomalies=False)
                        candidates = [r for r in history if r["source"] == source and r["month"][5:] == f"{month.month:02}" and r["coverage_status"] == "complete" and r["version"] == version and r["selected_days"] == pd.Period(r["month"]).days_in_month]
                        # Require exactly one matching version in every reference month.
                        candidates = [r for r in candidates if sum(h["month"] == r["month"] and h["source"] == source for h in history) == 1]
                        entry["reference_years"] = [int(r["month"][:4]) for r in candidates]
                        result = anomaly(entry["value"], [r["value"] for r in candidates])
                        entry.update({k:v for k,v in result.items() if k != "status"})
                        entry["anomaly_status"] = result["status"]
                elif coverage != "complete" or begin != month_start or finish != month_end:
                    entry["anomaly_status"] = "incomplete_month"
                records.append(entry)
    return records
