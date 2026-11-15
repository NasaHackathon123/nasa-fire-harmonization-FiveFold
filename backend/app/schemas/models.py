from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class Selection(BaseModel):
    region: str = "central-kalimantan"
    start: date = date(2023, 1, 1)
    end: date = date(2023, 12, 31)
    sensor: Literal["all", "MODIS", "VIIRS"] = "all"
    source: Literal["MODIS_SP", "VIIRS_SNPP_SP", "VIIRS_NOAA20_SP", "VIIRS_NOAA21_SP"] | None = None
    confidence: Literal["all", "nominal", "strict"] = "all"
    method: Literal["common-grid", "raw", "harmonized"] = "common-grid"
    metric: Literal["detections", "occupied_cells", "daily_cell_sum"] = "occupied_cells"
    min_frp: float = Field(default=0, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end < self.start:
            raise ValueError("start must be on or before end")
        if (self.end - self.start).days > 366 * 30:
            raise ValueError("Maximum query span is 30 years")
        return self

class Metadata(BaseModel):
    region: str
    start: date
    end: date
    sensor: str
    source: str | None
    confidence: str
    metric: str
    method: str
    processing_version: str
    attribution: str = "NASA FIRMS MODIS Collection 6.1 / VIIRS standard-processing observations"
    warnings: list[str]

class Activity(BaseModel):
    month: str
    source: str
    sensor: str
    version: str | None
    detections: int | None
    occupied_cells: int | None
    daily_cell_sum: int | None
    value: int | None
    coverage_status: Literal["complete", "partial", "unknown", "unavailable"]
    imported_days: int
    selected_days: int
    baseline: float | None = None
    absolute_difference: float | None = None
    percentage_difference: float | None = None
    anomaly_status: str = "insufficient_history"
    reference_years: list[int] = Field(default_factory=list)

class CalendarResponse(BaseModel):
    metadata: Metadata
    records: list[Activity]

class Hotspot(BaseModel):
    latitude: float
    longitude: float
    timestamp_utc: str
    sensor: str
    source_dataset: str
    satellite: str
    instrument: str
    version: str
    confidence_native: str
    confidence_type: str
    frp: float | None
    daynight: str | None
    scan: float | None
    track: float | None
    cell_id: str
    raw_source_id: str
    quality_flags: str

class HotspotResponse(BaseModel):
    metadata: Metadata
    records: list[Hotspot]
    total: int
    limit: int
    offset: int
    truncated: bool

class HealthResponse(BaseModel):
    status: str
    data_ready: bool
    processing_version: str

class Region(BaseModel):
    id: str
    name: str
    bbox: list[float]

class QualityResponse(BaseModel):
    metadata: Metadata
    cleaning_report: dict
    source_inventory: list[dict]
    confidence_comparison: list[dict]
    coverage: list[Activity]

class MethodologyResponse(BaseModel):
    processing_version: str
    method: str
    grid: dict
    metrics: dict
    confidence: dict
    harmonization: dict
    baseline: dict
    limitations: list[str]
    sources: list[str]


class DailyOverlap(BaseModel):
    acq_date: str
    shared_daily_cells: int

class ComparisonResponse(BaseModel):
    metadata: Metadata
    shared_daily_cells: list[DailyOverlap]
    definition: str
