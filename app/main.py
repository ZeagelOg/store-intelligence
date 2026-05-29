"""
main.py — FastAPI application entrypoint.
"""
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.routers import events, stores
from app.websocket import router as ws_router

logger = structlog.get_logger()

app = FastAPI(
    title="Store Intelligence API",
    description="Real-time retail analytics",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    trace_id = str(uuid.uuid4())[:8]
    request.state.trace_id = trace_id
    t0 = time.monotonic()
    
    response = await call_next(request)
    latency = round((time.monotonic() - t0) * 1000, 2)
    
    logger.info(
        "http_request",
        trace_id=trace_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency_ms=latency,
    )
    response.headers["X-Trace-ID"] = trace_id
    return response


@app.get("/")
async def root():
    return {"message": "Store Intelligence API", "docs": "/docs"}


app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(stores.router, prefix="/stores", tags=["Stores"])
app.include_router(ws_router, tags=["WebSocket"])
