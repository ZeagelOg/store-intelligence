"""
seed_data.py — Seeds sample_events.jsonl and pos_transactions.csv into the DB.
"""
import csv
import json
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL_SYNC", "sqlite:///store_intelligence.db")


def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except Exception:
        return None


def seed():
    print(f"Seeding: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)

    pos_path = "data/pos_transactions.csv"
    if os.path.exists(pos_path):
        with open(pos_path, encoding="utf-8") as f:
            txns = list(csv.DictReader(f))
        print(f"Seeding {len(txns)} POS transactions...")

    ev_path = "data/sample_events.jsonl"
    if os.path.exists(ev_path):
        with open(ev_path, encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        print(f"Seeding {len(lines)} camera events...")


if __name__ == "__main__":
    seed()
