import csv
import io
import json
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from backend.app.schemas.models import Selection, CalendarResponse, HotspotResponse, HealthResponse, Region, QualityResponse, MethodologyResponse, ComparisonResponse
from backend.app.database.repository import Repository, DataUnavailable
from backend.app.services.analytics import metadata, calendar
from pipeline.config import REGIONS, VERSION, METHOD, SOURCES
from pipeline.ingest import validate_bbox

router = APIRouter(prefix="/api")

def selection(params: Annotated[Selection, Query()]):
    if params.region not in REGIONS:
        raise HTTPException(404, "Unknown study region")
    if params.source and params.sensor != "all" and SOURCES[params.source] != params.sensor:
        raise HTTPException(422, "Source does not match selected sensor")
    if params.method == "harmonized":
        raise HTTPException(409, "Harmonized estimates are disabled: insufficient historical validation")
    if params.method == "raw" and params.metric != "detections":
        raise HTTPException(422, "Raw mode supports detections; use common-grid for cell metrics")
    return params

def repository():
    try:
        return Repository()
    except DataUnavailable as exc:
        raise HTTPException(503, str(exc)) from None

Selected = Annotated[Selection, Depends(selection)]
Store = Annotated[Repository, Depends(repository)]

@router.get("/health", response_model=HealthResponse)
def health():
    try:
        Repository()
        ready = True
    except DataUnavailable:
        ready = False
    return {"status": "ok", "data_ready": ready, "processing_version": VERSION}

@router.get("/regions", response_model=list[Region])
def regions():
    return list(REGIONS.values())

@router.get("/calendar", response_model=CalendarResponse)
@router.get("/trends", response_model=CalendarResponse)
@router.get("/anomalies", response_model=CalendarResponse)
def activity(params: Selected, store: Store):
    return {"metadata": metadata(params), "records": calendar(store, params)}

@router.get("/hotspots", response_model=HotspotResponse)
def hotspots(params: Selected, store: Store, limit: int = Query(1000,ge=1,le=5000), offset: int = Query(0,ge=0,le=1000000), bbox: str | None = None):
    bounds = None
    if bbox:
        try:
            bounds = list(map(float,bbox.split(",")))
            validate_bbox(bounds)
        except ValueError:
            raise HTTPException(422, "Invalid west,south,east,north bounding box") from None
    rows,total = store.observations(params,limit,offset,bounds)
    return {"metadata":metadata(params),"records":rows,"total":total,"limit":limit,"offset":offset,"truncated":offset+len(rows)<total}

@router.get("/quality", response_model=QualityResponse)
def quality(params: Selected, store: Store):
    comparisons = []
    for policy in ["all","nominal","strict"]:
        chosen = params.model_copy(update={"confidence":policy})
        _,count = store.observations(chosen,1)
        comparisons.append({"policy":policy,"detections":count})
    inventory = [{k:v for k,v in item.items() if k != "filename"} for item in store.inventory]
    return {"metadata":metadata(params),"cleaning_report":store.report,"source_inventory":inventory,
            "confidence_comparison":comparisons,"coverage":calendar(store,params,False)}

@router.get("/comparison", response_model=ComparisonResponse)
def comparison(params: Selected, store: Store):
    return {"metadata":metadata(params),"shared_daily_cells":store.overlap(params),
            "definition":"Distinct 1 km cells detected by both instrument families on the same UTC day; not simultaneous fires or calibrated equivalence."}

@router.get("/methodology", response_model=MethodologyResponse)
def methodology():
    return {"processing_version":VERSION,"method":METHOD,
        "grid":{"crs":"EPSG:32749","cell_size_m":1000,"origin":"UTM false origin","id":"32749:floor(easting/1000):floor(northing/1000)","boundary":"Cells are half-open [west,east),[south,north); regional bbox includes edge points.","domain":"Initial Kalimantan study boxes only; new regions require projection review."},
        "metrics":{"detections":"Individual satellite observation rows, not wildfire incidents","occupied_cells":"Distinct cells across the selected month or boundary-month interval","daily_cell_sum":"Sum of distinct daily cells; a recurring cell contributes once each day","frp":"Pixel-integrated fire radiative power in MW; not burned area"},
        "confidence":{"all":"All accepted native confidence values","nominal":"MODIS >=30; VIIRS n or h","strict":"MODIS >=80; VIIRS h","warning":"Policies are not equivalent probabilities across instruments"},
        "harmonization":{"enabled":False,"status":"Common grid, separate sources and versions only","calibration":"Nonnegative linear candidate, held-out latest year; never automatically validated; spatial and temporal stability review required"},
        "baseline":{"formula":"(observed - historical median) / historical median * 100","minimum_prior_years":3,"reference":"Previous complete same-calendar months, identical source, collection, region, metric and confidence policy","zero_baseline":"Percentage is null; absolute difference remains available","coverage":"Operator-declared file completeness, no rejected rows; cloud/overpass exposure not available"},
        "limitations":["Five-day samples do not establish a full monthly total or historical baseline","Missing months are null, not zero","Imported complete days do not imply complete clear-sky observations","Grid occupancy does not estimate burned area","No forecasting; no validated sensor equivalence","All thermal anomaly types retained, including potential nonvegetation sources"],
        "sources":["https://firms.modaps.eosdis.nasa.gov/api/area/","https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_MODIS_Firehotspots.html","https://firms.modaps.eosdis.nasa.gov/content/descriptions/FIRMS_VIIRS_Firehotspots.html"]}

@router.get("/export", responses={200:{"content":{"text/csv":{}}}})
def export(params: Selected, store: Store):
    rows = calendar(store,params)
    output = io.StringIO(newline="")
    fields = ["region","start","end","month","source","sensor","version","metric","value","detections","occupied_cells","daily_cell_sum","coverage_status","imported_days","selected_days","baseline","absolute_difference","percentage_difference","anomaly_status","reference_years","confidence","method","processing_version","attribution"]
    writer = csv.DictWriter(output,fieldnames=fields,extrasaction="ignore")
    writer.writeheader()
    meta = metadata(params)
    for row in rows:
        row = {**meta,**row,"reference_years":";".join(map(str,row["reference_years"]))}
        writer.writerow(row)
    return Response(output.getvalue(),media_type="text/csv",headers={"Content-Disposition":'attachment; filename="fire-activity.csv"'})
