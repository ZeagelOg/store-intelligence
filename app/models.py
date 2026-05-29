"""
models.py — Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class EventIn(BaseModel):
    event_id: Optional[uuid.UUID] = None
    event_type: str
    store_id: str
    camera_id: str
    visitor_id: str
    timestamp: datetime
    zone_id: Optional[str] = None
    dwell_ms: int = 0
    is_staff: bool = False
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EventBatchIn(BaseModel):
    events: List[EventIn] = Field(..., max_length=500)


class EventIngestResult(BaseModel):
    accepted: int
    rejected: int
    duplicates: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class ZoneDwellMetric(BaseModel):
    zone_id: str
    zone_name: Optional[str] = None
    avg_dwell_ms: float
    visit_count: int


class StoreMetrics(BaseModel):
    store_id: str
    period_start: datetime
    period_end: datetime
    unique_visitors: int
    total_entries: int
    total_exits: int
    conversion_rate: float
    total_transactions: int
    avg_basket_value: Optional[float] = None
    avg_dwell_by_zone: List[ZoneDwellMetric] = Field(default_factory=list)
    current_queue_depth: int = 0
    abandonment_rate: float = 0.0


class FunnelStage(BaseModel):
    stage: str
    count: int
    drop_off_pct: float


class StoreFunnel(BaseModel):
    store_id: str
    period_start: datetime
    period_end: datetime
    stages: List[FunnelStage]
    overall_conversion_rate: float


class ZoneHeat(BaseModel):
    zone_id: str
    zone_name: Optional[str] = None
    visit_count: int
    avg_dwell_ms: float
    heat_score: float
    data_confidence: Optional[str] = None


class StoreHeatmap(BaseModel):
    store_id: str
    period_start: datetime
    period_end: datetime
    zones: List[ZoneHeat]


class Anomaly(BaseModel):
    anomaly_id: str
    anomaly_type: str
    severity: str
    detected_at: datetime
    store_id: str
    description: str
    current_value: float
    baseline_value: Optional[float] = None
    suggested_action: str


class StoreAnomalies(BaseModel):
    store_id: str
    anomalies: List[Anomaly]
    checked_at: datetime


class StoreHealth(BaseModel):
    store_id: str
    last_event_at: Optional[datetime] = None
    status: str = "OK"
    warning: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    database: Dict[str, Any]
    stores: List[StoreHealth] = Field(default_factory=list)
    uptime_seconds: float
