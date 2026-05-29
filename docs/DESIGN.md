# Design Document

## Architecture
FastAPI + PostgreSQL + YOLOv8

## AI Decisions
- Chose YOLOv8s over RT-DETR for speed
- Flat events over hierarchical for idempotency
- PostgreSQL only over Redis+PostgreSQL for simplicity
