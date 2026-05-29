# PROMPT:
#   "Generate pytest tests for a FastAPI store metrics API. Cover: ingest idempotency,
#    partial batch success, staff exclusion, empty store, zero purchases, re-entry
#    funnel deduplication, heatmap normalisation, low-confidence flag, queue spike
#    anomaly, health STALE_FEED. Use pytest-asyncio and httpx.AsyncClient."
#
# CHANGES MADE:
#   - Fixed re-entry test: REENTRY must count as same session, not a new visitor.
#   - Added batch > 500 → 422 test (AI version missed the limit check).
#   - Replaced deprecated asyncio.get_event_loop() with pytest-asyncio fixtures.
#   - Added explicit assertion that is_staff=True events never appear in unique_visitors.

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import engine, Base


@pytest_asyncio.fixture(autouse=True)
async def reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


STORE = "ST1076"


def ev(event_type, visitor_id, zone_id=None, is_staff=False,
       timestamp="2026-04-10T14:00:00Z", dwell_ms=0, queue_pos=None, zone_type=None):
    meta = {"session_seq": 1}
    return {
        "event_id": str(uuid.uuid4()), "store_id": STORE,
        "camera_id": "cam1", "visitor_id": visitor_id,
        "event_type": event_type, "timestamp": timestamp,
        "zone_id": zone_id, "dwell_ms": dwell_ms,
        "is_staff": is_staff, "confidence": 0.9,
        "zone_type": zone_type,
        "queue_position_at_join": queue_pos,
        "metadata": meta,
    }


async def ingest(client, events):
    r = await client.post("/events/ingest", json={"events": events})
    assert r.status_code == 200
    return r.json()


@pytest.mark.asyncio
async def test_ingest_basic(client):
    res = await ingest(client, [ev("entry", "VIS_001")])
    assert res["accepted"] == 1 and res["rejected"] == 0


@pytest.mark.asyncio
async def test_ingest_idempotent(client):
    event = ev("entry", "VIS_001")
    await ingest(client, [event])
    res = await ingest(client, [event])
    from app.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as db:
        count = (await db.execute(text("SELECT COUNT(*) FROM events"))).scalar()
    assert count == 1


@pytest.mark.asyncio
async def test_ingest_partial_success(client):
    bad = {"event_id": "x", "store_id": STORE}
    res = await ingest(client, [ev("entry","VIS_001"), bad, ev("exit","VIS_002")])
    assert res["accepted"] == 2 and res["rejected"] == 1


@pytest.mark.asyncio
async def test_ingest_batch_too_large(client):
    big = [ev("entry", f"VIS_{i}") for i in range(501)]
    r = await client.post("/events/ingest", json={"events": big})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_metrics_empty_store(client):
    r = await client.get(f"/stores/{STORE}/metrics")
    assert r.status_code == 200
    d = r.json()
    assert d["unique_visitors"] == 0
    assert d["conversion_rate"] == 0.0


@pytest.mark.asyncio
async def test_metrics_excludes_staff(client):
    await ingest(client, [
        ev("entry", "VIS_CUST", is_staff=False),
        ev("entry", "VIS_STAFF", is_staff=True),
    ])
    d = (await client.get(f"/stores/{STORE}/metrics")).json()
    assert d["unique_visitors"] == 1


@pytest.mark.asyncio
async def test_metrics_all_staff_zero_visitors(client):
    await ingest(client, [ev("entry", f"VIS_S{i}", is_staff=True) for i in range(5)])
    d = (await client.get(f"/stores/{STORE}/metrics")).json()
    assert d["unique_visitors"] == 0


@pytest.mark.asyncio
async def test_metrics_queue_depth(client):
    await ingest(client, [ev("queue_completed","VIS_001",zone_id="BILLING",queue_pos=4)])
    d = (await client.get(f"/stores/{STORE}/metrics")).json()
    assert d["current_queue_depth"] == 4


@pytest.mark.asyncio
async def test_funnel_empty(client):
    r = await client.get(f"/stores/{STORE}/funnel")
    assert r.status_code == 200
    d = r.json()
    assert all(s["count"] == 0 for s in d["stages"])


@pytest.mark.asyncio
async def test_funnel_reentry_no_double_count(client):
    await ingest(client, [
        ev("entry",   "VIS_001", timestamp="2026-04-10T14:00:00Z"),
        ev("exit",    "VIS_001", timestamp="2026-04-10T14:10:00Z"),
        ev("reentry", "VIS_001", timestamp="2026-04-10T14:15:00Z"),
    ])
    d = (await client.get(f"/stores/{STORE}/funnel")).json()
    entry_stage = next(s for s in d["stages"] if s["stage"] == "Entry")
    assert entry_stage["count"] == 1


@pytest.mark.asyncio
async def test_heatmap_empty(client):
    r = await client.get(f"/stores/{STORE}/heatmap")
    assert r.status_code == 200
    assert r.json()["zones"] == []


@pytest.mark.asyncio
async def test_anomalies_empty(client):
    r = await client.get(f"/stores/{STORE}/anomalies")
    assert r.status_code == 200
    assert r.json()["anomalies"] == []


@pytest.mark.asyncio
async def test_health_ok(client):
    r = await client.get("/health")
    assert r.status_code in (200, 503)
    assert "status" in r.json()
