from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import List
import uuid

router = APIRouter()

class EventIn(BaseModel):
    event_id: str = None
    event_type: str
    store_id: str
    visitor_id: str
    timestamp: str

@router.post("/ingest")
async def ingest(events: List[EventIn], db: AsyncSession = Depends(lambda: None)):
    return {"accepted": len(events), "rejected": 0}
