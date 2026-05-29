# DESIGN.md — Store Intelligence System

## Architecture Overview

The system converts raw CCTV footage into real-time store analytics through four stages:
Raw CCTV Clips → Detection Layer (YOLOv8 + ByteTrack) → Event Stream (JSONL) → Intelligence API (FastAPI) → Live Dashboard


### Component Details

**1. Detection Pipeline (`pipeline/`)**
- **Model:** YOLOv8s for person detection (COCO class 0)
- **Tracking:** ByteTrack with IoU-based Hungarian matching
- **Staff Detection:** HSV histogram on upper torso (uniform colour detection)
- **Re-ID:** Cosine similarity on 96-bin HSV histograms from clothing (not face)
- **Direction:** Trajectory-based line crossing (entry threshold at 450px)

**2. Event Stream**
- Flat schema with 8 event types: ENTRY, EXIT, ZONE_ENTER, ZONE_EXIT, ZONE_DWELL, BILLING_QUEUE_JOIN, BILLING_QUEUE_ABANDON, REENTRY
- Each event has UUID, store_id, visitor_id, timestamp, confidence, is_staff flag
- Emitted as JSONL for streaming compatibility

**3. Intelligence API (`app/`)**
- FastAPI with async PostgreSQL (asyncpg)
- Idempotent ingestion (`INSERT ON CONFLICT DO NOTHING`)
- Real-time metrics computed via SQL aggregates (no pre-cached values)
- WebSocket (`/ws/live`) for dashboard push

**4. Database**
- PostgreSQL 16 with JSONB for flexible metadata
- Indexes on (store_id, timestamp) and (visitor_id)
- POS transactions joined via 30-minute time window for conversion

---

## AI-Assisted Decisions

### Decision 1: Detection Model — YOLOv8s vs RT-DETR

**What AI suggested:** Claude recommended RT-DETR, arguing its transformer attention mechanism handles partial occlusion better than CNN-based detectors.

**What I did:** I chose YOLOv8s despite the AI's suggestion.

**Why:** 
- RT-DETR is 3–5× slower (8+ hours vs 2 hours on 15 clips)
- YOLOv8 has native ByteTrack integration (`model.track()`), removing an entire class of tracker-matching bugs
- Face blur in footage doesn't affect full-body detection
- The occlusion cases in billing queue were manageable with ByteTrack's Kalman filter

**Outcome:** YOLOv8s achieved sufficient accuracy. The 3-frame subsampling (5fps from 15fps source) reduced compute without losing entry/exit events.

---

### Decision 2: Event Schema — Hierarchical vs Flat

**What AI suggested:** GPT-4 recommended a hierarchical session model where zone visits are nested inside session objects. It argued this would make funnel queries a simple lookup rather than a GROUP BY aggregation.

**What I did:** I overrode the AI and chose flat events with `visitor_id` and `session_seq`.

**Why:**
- **Idempotency:** Flat events allow `INSERT ON CONFLICT (event_id) DO NOTHING`. Session-level idempotency is much harder.
- **Stream-friendly:** Events are emitted the moment detection happens. Hierarchical would require buffering until EXIT.
- **Flexibility:** SQL `COUNT(DISTINCT visitor_id)` reconstructs sessions on the fly. Adding new event types doesn't require schema migration.

**Outcome:** The flat schema passed all idempotency tests. The funnel query runs in ~50ms at current volume — acceptable for 5 stores.

---

### Decision 3: Data Store — PostgreSQL + Redis vs PostgreSQL Only

**What AI suggested:** Claude suggested Redis for real-time metric caching (updated on each ingest) with PostgreSQL as the write-through store. It argued this makes `/metrics` O(1).

**What I did:** I chose PostgreSQL only, no Redis.

**Why:**
- One system means no cache invalidation bugs and two fewer failure surfaces
- PostgreSQL window functions (`FILTER`, `INTERVAL`) handle all analytics natively
- At 40 stores with 10K events/hour, PostgreSQL with proper indexes is sufficient
- Redis can be bolted on later as an optimisation, not a structural dependency

**Outcome:** `/metrics` runs aggregation queries in ~50ms. The health endpoint correctly detects `STALE_FEED` when no events arrive for 10+ minutes.

---

## Edge Cases Handled

| Edge Case | Solution |
|-----------|----------|
| Group entry (2–4 people) | ByteTracker spawns separate track per detection |
| Staff movement | HSV uniform histogram on upper torso (79% accuracy) |
| Re-entry (same person, new session) | Appearance gallery + cosine similarity (>0.65 within 120s window) |
| Partial occlusion | Confidence degraded (0.15–0.35), not suppressed |
| Billing queue buildup | Track queue_position_at_join + abandonment detection |
| Empty store periods | Zero counts return 0, not null or error |
| Camera overlap | Cross-camera deduplication via visitor_id |
| Low-confidence detections | Passed through with confidence flag, never dropped |   
