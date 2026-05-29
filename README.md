<div align="center">
  
# 🏬 Store Intelligence
### *From Raw CCTV Footage to Live Store Analytics*

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-00FFFF?style=for-the-badge&logo=yolo&logoColor=black)](https://ultralytics.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

**End-to-End Computer Vision Pipeline | 48-Hour Take-Home Challenge**

</div>

---

## 📖 About The Challenge

This is my submission for the **Store Intelligence Engineering Challenge** — a complete retail analytics system that transforms raw, anonymised CCTV footage into real-time, queryable store metrics.

**The Problem:** 40 physical stores, zero offline analytics.  
**The Solution:** A production-ready pipeline from detection → events → API → dashboard.

---

# 🏬 Store Intelligence — CCTV Retail Analytics

Converts raw, anonymised CCTV footage from the **Brigade Road (Bangalore)** retail store into real-time business metrics — footfall, conversion rate, billing-queue depth, and zone heatmaps. Built with YOLOv8 detection, a ByteTrack-style multi-object tracker with Re-ID, a FastAPI ingestion service, and a PostgreSQL event store.

---

## Table of Contents

- [What It Does](#what-it-does)
- [Camera Mapping](#camera-mapping)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Setup](#setup)
- [Running the Pipeline](#running-the-pipeline)
- [API Reference](#api-reference)
- [Live Dashboard](#live-dashboard)
- [Running Tests](#running-tests)
- [Event Types](#event-types)
- [Key Design Decisions](#key-design-decisions)
- [Edge Cases Handled](#edge-cases-handled)
- [Notes & Authorship](#notes--authorship)

---

## What It Does

- **Detects and tracks people** in CCTV footage using YOLOv8s (COCO person class) with ByteTrack-style IoU + Hungarian matching
- **Re-identifies visitors** across short gaps using a 96-bin HSV appearance gallery and cosine similarity, emitting `REENTRY` instead of a duplicate `ENTRY`
- **Classifies staff vs customers** using HSV histogram analysis on the upper-torso crop — no face data required or used
- **Generates structured events** (8 types) as newline-delimited JSON (JSONL), streamed as they occur
- **Correlates footfall with POS transactions** via a 30-minute time window to compute conversion rate
- **Ingests events idempotently** — duplicate `event_id` values are silently skipped (`ON CONFLICT DO NOTHING`)
- **Detects anomalies**: billing queue spikes (>2σ above baseline), conversion rate drops (<70% of 7-day average), and dead zones (no visits in 30 min)
- **Pushes live updates** to connected dashboard clients via WebSocket (`/ws/live`)

---

## Camera Mapping

| Camera | Role | Used For |
|--------|------|----------|
| **CAM3** | Entry / Exit | Footfall — unique visitor count |
| **CAM5** | Billing counter | Queue depth and abandonment rate |
| **CAM1** | Shelves (Zone A) | Zone visit counts and dwell time |
| **CAM2** | Shelves (Zone B) | Zone visit counts and dwell time |
| **CAM4** | Backroom | Staff detection and movement |

---

## Architecture

```
CCTV Videos (.mp4)  +  POS Transactions (.csv)
              │
              ▼
   YOLOv8s  ──  Person detection (COCO class 0)
   ByteTracker ── IoU matching + Kalman filter
   Staff Classifier ── HSV upper-torso histogram
   Re-ID ── Appearance gallery + cosine similarity
   DirectionClassifier ── Trajectory line-crossing
              │
              ▼
   Event Emission ──► data/events.jsonl
   (flat JSONL, 8 event types, UUID per event)
              │
              ▼
   pipeline/feed.py  ──► POST /events/ingest
   (batched, idempotent, up to 500 events/batch)
              │
              ▼
   FastAPI Ingestion API  ──  PostgreSQL 16
   INSERT ON CONFLICT (event_id) DO NOTHING
              │
              ▼
   GET /stores/{id}/metrics    visitors · conversion · queue depth
   GET /stores/{id}/funnel     entry → zone → billing → purchase
   GET /stores/{id}/heatmap    per-zone visit counts and dwell
   GET /stores/{id}/anomalies  spike · drop · dead zone
   WS  /ws/live                real-time push to dashboard
              │
              ▼
   http://localhost:8000/dashboard
   (auto-refreshes every 5 seconds)
```

---

## Project Structure

```
store-intelligence/
├── pipeline/
│   ├── detect.py             # Main detection + tracking script — YOLOv8s, reads clips, calls tracker
│   ├── tracker.py            # ByteTracker, DirectionClassifier, staff HSV classifier, Re-ID gallery
│   ├── emit.py               # StoreEvent schema + EventEmitter (append-mode JSONL writer)
│   └── run.sh                # One command to process all clips → events (detect → feed)
│
├── app/
│   ├── main.py               # FastAPI entrypoint — CORS, request logging, X-Trace-ID header
│   ├── models.py             # Pydantic schemas: EventIn, StoreMetrics, Anomaly, StoreFunnel …
│   ├── ingestion.py          # Ingest endpoint — batch dedup via INSERT ON CONFLICT DO NOTHING
│   ├── metrics.py            # Real-time metric computation — visitors, conversion, queue depth
│   ├── funnel.py             # Funnel stages + session logic (entry → zone → billing → purchase)
│   ├── anomalies.py          # Anomaly detection — queue spike (2σ), conversion drop, dead zone
│   └── health.py             # Health check — DB connectivity, STALE_FEED detection, uptime
│
├── tests/
│   ├── test_pipeline.py      # Unit tests: event schema (8 types), tracker, emitter, BBox IoU, Re-ID
│   ├── test_metrics.py       # API tests: ingest, idempotency, staff exclusion, funnel, queue depth
│   └── test_anomalies.py     # Anomaly logic: spike thresholds, conversion drop, dead zone, structure
│
├── docs/
│   ├── DESIGN.md             # Architecture overview + AI-vs-human decision log (3 decisions)
│   └── CHOICES.md            # Detailed option comparison tables (model, schema, data store)
│
├── docker-compose.yml        # Two services: postgres:16-alpine + api (port 8000)
└── README.md
```

---

## Setup

### Option A — Docker (recommended, no local Python needed)

```bash
# Clone and start both the API and the PostgreSQL database
git clone https://github.com/ZeagelOg/store-intelligence.git
cd store-intelligence
docker compose up --build

# API:              http://localhost:8000
# Interactive docs: http://localhost:8000/docs
# Live dashboard:   http://localhost:8000/dashboard
```

### Option B — Local virtual environment

```bash
# 1. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1        # Windows
# source venv/bin/activate          # Mac / Linux

# 2. Install dependencies
pip install -r requirements.txt
pip install ultralytics opencv-python

# 3. Place your data files (not committed — see Notes)
#    data/clips/               ← CCTV .mp4 recordings
#    data/pos_transactions.csv ← POS export
#    data/store_layout.json    ← camera-to-zone mapping

# 4. Start the API
uvicorn app.main:app --reload
# Runs at http://localhost:8000
```

---

## Running the Pipeline

Run each step in order to process footage and populate the database.

```bash
# Step 1 — Detect people in CCTV clips and emit events to JSONL
python pipeline/detect.py \
    --clips-dir data/clips \
    --layout    data/store_layout.json \
    --output    data/events.jsonl \
    --model     yolov8s.pt

# Step 2 — Seed POS transactions into the database
python pipeline/seed_data.py

# Step 3 — Feed all generated events to the API (batches of 100, idempotent)
python pipeline/feed.py \
    --events   data/events.jsonl \
    --api-url  http://localhost:8000

# Or run everything at once via the shell script
bash pipeline/run.sh
```

The feeder prints per-batch `accepted / rejected / duplicates` counts. Pass `--realtime` to throttle at 0.3 s per batch and simulate a live camera stream. Default batch size is 100; maximum the API accepts is 500 per request (larger batches return HTTP 422).

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Service info + link to Swagger docs |
| `GET` | `/health` | DB connectivity, store feed freshness (`STALE_FEED` if >10 min silent), uptime |
| `POST` | `/events/ingest` | Ingest a batch of events (max 500); duplicate UUIDs silently skipped |
| `GET` | `/stores/{store_id}/metrics` | Unique visitors, conversion rate, queue depth, abandonment rate, avg dwell by zone |
| `GET` | `/stores/{store_id}/funnel` | Entry → Zone → Billing → Purchase funnel with drop-off % per stage |
| `GET` | `/stores/{store_id}/heatmap` | Per-zone visit counts, avg dwell ms, and normalised heat score |
| `GET` | `/stores/{store_id}/anomalies` | Active anomalies with severity (INFO / WARN / CRITICAL) and suggested action |
| `WS` | `/ws/live` | WebSocket — real-time event push to dashboard clients |
| `GET` | `/dashboard` | Serves the live analytics dashboard HTML |

Full interactive docs at **http://localhost:8000/docs** (Swagger UI).

### Ingest request body

```json
{
  "events": [
    {
      "event_id":  "550e8400-e29b-41d4-a716-446655440000",
      "event_type": "ENTRY",
      "store_id":   "STORE_BLR_002",
      "camera_id":  "CAM3",
      "visitor_id": "VIS_a1b2c3",
      "timestamp":  "2026-05-01T09:15:32Z",
      "zone_id":    null,
      "dwell_ms":   0,
      "is_staff":   false,
      "confidence": 0.94,
      "metadata":   { "session_seq": 1 }
    }
  ]
}
```

---

## Live Dashboard

After starting the API, open:

```
http://localhost:8000/dashboard
```

The dashboard displays four live metric cards — **Unique Visitors**, **Conversion Rate**, **Queue Depth**, and **Abandonment Rate** — plus a scrolling **Live Event Feed** that colour-codes events as they arrive (ENTRY green / EXIT red / other purple). All data refreshes automatically every 5 seconds via WebSocket. A store selector at the top right switches between stores without a page reload.

---

## Running Tests

```bash
pip install pytest pytest-asyncio httpx aiosqlite

# Run all test suites
pytest tests/ -v

# Run individual suites
pytest tests/test_metrics.py   -v   # API ingestion and metrics
pytest tests/test_anomalies.py -v   # Anomaly detection logic
pytest tests/test_pipeline.py  -v   # Tracker, emitter, and schema
```

Tests run against an **in-memory SQLite database** using `aiosqlite` and `httpx.AsyncClient` against the FastAPI ASGI app — no running server or Docker required.

### Test coverage summary

**`test_metrics.py`** — Basic ingest, idempotency (same UUID → 1 DB row), partial-batch success, batch over 500 → HTTP 422, empty-store zero counts, staff exclusion from `unique_visitors`, queue depth from billing events, funnel re-entry deduplication (REENTRY counts as same visitor, not a new one), health endpoint.

**`test_anomalies.py`** — Queue spike detection at 2σ threshold, no trigger at exact boundary, WARN vs CRITICAL at 3σ, zero-variance edge case, conversion drop at 70% threshold, no-history guard (no false alerts), dead-zone 30-minute boundary, anomaly object structure validation (`anomaly_id`, `severity`, `suggested_action` all required).

**`test_pipeline.py`** — All 8 event types accepted by schema, confidence clamping (>1.0 → 1.0, <0.0 → 0.0), UUID uniqueness across 100 events, `visitor_id` determinism and `VIS_` prefix, BBox IoU (identical = 1.0, no overlap = 0.0, centroid correct), `EventEmitter` JSONL output validity and per-type event counts.

---

## Event Types

| Type | Camera | Emitted When |
|------|--------|--------------|
| `ENTRY` | CAM3 | Person crosses the entry threshold inbound |
| `EXIT` | CAM3 | Person crosses the entry threshold outbound |
| `ZONE_ENTER` | CAM1, CAM2 | Person enters a shelf zone |
| `ZONE_EXIT` | CAM1, CAM2 | Person leaves a shelf zone |
| `ZONE_DWELL` | CAM1, CAM2 | Person dwells in a zone above the dwell threshold |
| `BILLING_QUEUE_JOIN` | CAM5 | Person joins the billing queue |
| `BILLING_QUEUE_ABANDON` | CAM5 | Person leaves the queue without completing purchase |
| `REENTRY` | CAM3 | Same person re-enters within the Re-ID window (120 s) |

Each event carries: `event_id` (UUID), `store_id`, `camera_id`, `visitor_id`, `timestamp`, `zone_id`, `dwell_ms`, `is_staff`, `confidence`, and a `metadata` object with `session_seq` and optional `queue_depth`.

---

## Key Design Decisions

Full rationale with AI-vs-human reasoning logs is in [`docs/DESIGN.md`](docs/DESIGN.md) and [`docs/CHOICES.md`](docs/CHOICES.md).

**YOLOv8s over RT-DETR** — RT-DETR's transformer attention handles occlusion better in theory, but runs 3–5× slower (8+ hours vs 2 hours for 15 clips at ~90k frames with 3-frame subsampling). YOLOv8's native `model.track()` integration also eliminates an entire class of tracker-matching bugs. ByteTrack's Kalman filter covers the occlusion cases that actually appeared in the footage.

**Flat events over hierarchical sessions** — Flat events with `visitor_id` + `session_seq` allow atomic idempotency via UUID. A session-wrapper schema would require buffering until EXIT (up to 20 minutes) and creates race conditions on concurrent ingests. SQL `COUNT(DISTINCT visitor_id) FILTER (WHERE event_type = 'entry')` reconstructs sessions at query time in ~50 ms.

**PostgreSQL only, no Redis** — At 40 stores × ~10K events/hour, PostgreSQL window functions handle all analytics natively. One system means no cache-invalidation bugs and no additional failure surface. Redis can be added as a later optimisation.

**HSV histogram staff classifier over GPT-4V** — GPT-4V reached 85% accuracy on 50 labelled crops but at 200 ms/call. At 5 fps × 5 cameras that is 25 calls/second — impossible for real-time. The HSV upper-torso histogram runs in <1 ms at 79% accuracy with zero API cost.

---

## Edge Cases Handled

| Scenario | Solution |
|----------|----------|
| Group entry (2–4 people together) | ByteTracker spawns a separate track per detection bounding box |
| Staff in customer areas | HSV uniform-colour histogram on upper torso; `is_staff=true` events excluded from all visitor metrics |
| Re-entry within 2 minutes | Appearance gallery + cosine similarity >0.82 within 120 s window → `REENTRY`, not a second `ENTRY` |
| Partial occlusion (behind a shelf) | Confidence degraded to 0.15–0.35, track kept alive via Kalman prediction, never dropped |
| Billing queue buildup | `queue_position_at_join` tracked per visitor; abandonment detected when queue joined but not completed |
| Empty store periods | All counts return `0`, not `null` or an error |
| Camera overlap zones | Cross-camera deduplication via deterministic `visitor_id` hash (SHA-1 of `store_id + track_id`) |
| Low-confidence detections | Passed through with confidence flag; filtering is a query-time decision, not discarded at pipeline time |
| Stale camera feed | `/health` returns `STALE_FEED` warning when no events arrive for 10+ minutes |

---

## Notes & Authorship

**Data files are not committed.** CCTV video clips, generated JSONL event files, and POS CSVs are excluded via `.gitignore` for size and confidentiality. To run the full pipeline, place your files at:

```
data/
├── clips/                   ← .mp4 CCTV recordings (one file per camera)
├── store_layout.json        ← camera-to-zone mapping (provided with challenge)
├── events.jsonl             ← generated by detect.py
└── pos_transactions.csv     ← POS export with timestamp and amount columns
```

See [`docs/DESIGN.md`](docs/DESIGN.md) for the architecture and AI decision log, [`docs/CHOICES.md`](docs/CHOICES.md) for detailed option comparison tables, and `HOW_I_BUILT_THIS.md` for the development journey.

**On AI assistance:** This project was built with AI assistance for scaffolding and boilerplate. The camera-to-role mapping, per-camera pipeline scripts, POS deduplication logic, the live dashboard, and all debugging and validation were done and verified by me. Every case where an AI recommendation was overridden — and why — is documented in `docs/DESIGN.md`. AI accelerated the routine parts; the engineering decisions were mine.
