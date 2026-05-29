# CHOICES.md — Key Technical Decisions

## Decision 1: Detection Model — YOLOv8s

### Options Considered

| Model | Pros | Cons |
|-------|------|------|
| **YOLOv8s** | Fast (2hr processing), native ByteTrack, large community | Weaker on extreme occlusion vs transformers |
| **YOLOv8n** | Fastest inference, smallest model | Lower accuracy on crowded scenes |
| **RT-DETR** | Transformer attention handles occlusion | 3–5× slower, complex setup, 500MB+ model |
| **MediaPipe** | Lightweight, runs on CPU | Single-person only, not multi-object |

### What AI Suggested
Claude recommended RT-DETR, stating: *"The transformer attention mechanism in RT-DETR handles partial occlusion significantly better than CNN-based detectors like YOLO. For retail CCTV where customers are often behind displays or each other, this is critical."*

### What I Chose and Why
**I chose YOLOv8s.**

**Reasoning:**
1. **Native ByteTrack:** `model.track()` gives detection + tracking in one call. With RT-DETR, I would need to implement Hungarian matching and Kalman filtering separately — adding ~500 lines of bug-prone code.

2. **Processing time:** 15 clips × 20 min × 15fps = 270k frames. With 3-frame subsampling = 90k frames. YOLOv8s: ~2 hours on a single GPU. RT-DETR: ~8+ hours.

3. **Face blur is irrelevant:** The dataset has full-face blur, but YOLO detects full-body bounding boxes (COCO class 0). Face blur has zero effect on detection quality.

4. **Occlusion handling is sufficient:** ByteTrack's Kalman filter predicts through 2–5 frames of occlusion (e.g., behind a display). The billing clip's worst occlusion was 8 frames — the track re-appeared correctly.

**Trade-off accepted:** RT-DETR might perform better on extreme occlusion (e.g., 10+ frames). For this dataset and 48-hour timeline, YOLOv8s was the right choice.

---

### VLM Experiment (Staff Detection)

I also experimented with GPT-4V for staff classification.

**Prompt used:**
> *"You are analyzing a retail CCTV frame. A bounding box is drawn around a person. Look at the upper body clothing. Is this person a store staff member? Staff wear either a dark blue polo with 'PURPLLE' logo or a black apron. Reply with 'STAFF' or 'CUSTOMER' and a confidence score (0-100)."*

**Evaluation on 50 labelled crops:**
- Accuracy: 85% (42/50 correct)
- Latency: 200ms per call
- At 5fps × 5 cameras = 25 calls/second = 5 seconds of VLM processing per second → impossible for real-time

**Final decision:** Used HSV histogram instead:
- 79% accuracy (acceptable)
- <1ms per call (200× faster)
- No API cost

---

## Decision 2: Event Schema — Flat vs Hierarchical

### Options Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **Hierarchical** | Session wrapper containing nested zone visits | Simpler funnel query | Hard idempotency, requires buffering |
| **Flat (chosen)** | Individual events linked by visitor_id + session_seq | Stream-friendly, easy dedup | Funnel requires GROUP BY |
| **Denormalised** | Pre-computed session table + raw events | Fast reads | Duplicate data, sync complexity |

### What AI Suggested
GPT-4 suggested: *"Wrap events in a session object. Store zone visits as a nested array inside the session. Then your /funnel endpoint becomes a simple session lookup rather than a complex GROUP BY."*

### What I Chose and Why
**I chose flat events with session_seq.**

**Reasoning:**
1. **Idempotency is atomic:** `INSERT INTO events ... ON CONFLICT (event_id) DO NOTHING` works at the event level. With hierarchical sessions, I'd need to check if the session already exists before inserting — race conditions on concurrent ingests.

2. **Real-time emission:** The pipeline emits events as they happen (ENTRY at frame 0, ZONE_ENTER at frame 150, etc.). Hierarchical would require buffering until EXIT (possibly 20+ minutes later).

3. **Real-world schema matches:** The provided `sample_events.jsonl` uses exactly this flat structure. Aligning with the real data reduced validation effort.

**Funnel query (PostgreSQL):**
```sql
SELECT COUNT(DISTINCT visitor_id) FILTER (WHERE event_type = 'entry') as entry,
       COUNT(DISTINCT visitor_id) FILTER (WHERE event_type = 'zone_entered') as zone_visit
FROM events WHERE store_id = :sid
