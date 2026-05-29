"""
emit.py — Event schema and emitter for the detection pipeline.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel, Field, field_validator


VALID_EVENT_TYPES = {
    "ENTRY", "EXIT", "ZONE_ENTER", "ZONE_EXIT", "ZONE_DWELL",
    "BILLING_QUEUE_JOIN", "BILLING_QUEUE_ABANDON", "REENTRY",
}


class EventMetadata(BaseModel):
    queue_depth: Optional[int] = None
    sku_zone: Optional[str] = None
    session_seq: int = 0


class StoreEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    store_id: str
    camera_id: str
    visitor_id: str
    event_type: str
    timestamp: str
    zone_id: Optional[str] = None
    dwell_ms: int = 0
    is_staff: bool = False
    confidence: float
    metadata: EventMetadata = Field(default_factory=EventMetadata)

    @field_validator("event_type")
    @classmethod
    def check_type(cls, v):
        if v not in VALID_EVENT_TYPES:
            raise ValueError(f"Unknown event_type: {v}")
        return v

    @field_validator("confidence")
    @classmethod
    def clamp(cls, v):
        return round(max(0.0, min(1.0, float(v))), 4)

    def to_jsonl(self) -> str:
        return self.model_dump_json() + "\n"


class EventEmitter:
    def __init__(self, path: Optional[str] = None):
        self._f = open(path, "a", buffering=1) if path else None
        self._counts: dict[str, int] = {}

    def emit(self, ev: StoreEvent) -> StoreEvent:
        if self._f:
            self._f.write(ev.to_jsonl())
        self._counts[ev.event_type] = self._counts.get(ev.event_type, 0) + 1
        return ev

    def summary(self) -> dict:
        return dict(self._counts)

    def close(self):
        if self._f:
            self._f.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
