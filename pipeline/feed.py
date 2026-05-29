"""
feed.py — Send detected events to the Intelligence API.
"""
import argparse
import json
import time
import httpx


def feed(events_path: str, api_url: str, batch_size: int = 100, realtime: bool = False):
    with open(events_path) as f:
        events = [json.loads(l) for l in f if l.strip()]

    print(f"Loaded {len(events)} events from {events_path}")
    ok = err = dup = 0
    client = httpx.Client(timeout=30)

    for i in range(0, len(events), batch_size):
        batch = events[i:i+batch_size]
        try:
            r = client.post(f"{api_url}/events/ingest", json={"events": batch})
            res = r.json()
            ok += res.get("accepted", 0)
            err += res.get("rejected", 0)
            dup += res.get("duplicates", 0)
            print(f"  batch {i//batch_size+1}: accepted={res.get('accepted')}  "
                  f"rejected={res.get('rejected')}  duplicates={res.get('duplicates')}")
        except Exception as exc:
            print(f"  batch {i//batch_size+1}: ERROR — {exc}")
            err += len(batch)
        if realtime:
            time.sleep(0.3)

    client.close()
    print(f"\nDone — accepted={ok}  rejected={err}  duplicates={dup}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--events", required=True)
    p.add_argument("--api-url", default="http://localhost:8000")
    p.add_argument("--batch-size", type=int, default=100)
    p.add_argument("--realtime", action="store_true")
    args = p.parse_args()
    feed(args.events, args.api_url, args.batch_size, args.realtime)


if __name__ == "__main__":
    main()
