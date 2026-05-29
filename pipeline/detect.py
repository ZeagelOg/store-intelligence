import argparse, json, uuid
from datetime import datetime, timezone

def main():
    print("Detection pipeline ready")
    with open("data/events.jsonl", "w") as f:
        event = {
            "event_id": str(uuid.uuid4()),
            "store_id": "STORE_BLR_002",
            "event_type": "ENTRY",
            "visitor_id": "VIS_001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_staff": False,
            "confidence": 0.95
        }
        f.write(json.dumps(event) + "\n")
        print("Mock event created")

if __name__ == "__main__":
    main()
