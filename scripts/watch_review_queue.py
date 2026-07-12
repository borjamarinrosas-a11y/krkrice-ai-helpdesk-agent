import argparse
import json
import time
from datetime import datetime

import httpx


def print_queue(items: list[dict[str, object]]) -> None:
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    if not items:
        print(f"[{timestamp}] No pending tickets.", flush=True)
        return

    print(f"[{timestamp}] {len(items)} ticket(s) awaiting human review:", flush=True)
    for item in items:
        comment = str(item.get("comment", ""))
        category_line = next((line for line in comment.splitlines() if line.startswith("**Category:**")), "")
        route_line = next(
            (
                line for line in comment.splitlines()
                if line.startswith("**Team:**") or line.startswith("**Suggested team:**")
            ),
            "",
        )
        print(
            f"  - {item.get('issue_key')}: {item.get('action')} | "
            f"{category_line.replace('**', '')} | {route_line.replace('**', '')}",
            flush=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch the KRkRice human-review queue without writing to Jira.")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds (minimum 10).")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Local KRkRice API base URL.")
    args = parser.parse_args()
    interval = max(args.interval, 10)
    endpoint = f"{args.url.rstrip('/')}/api/jira/review-queue"
    previous_snapshot = None

    print(f"Watching {endpoint} every {interval} seconds. Press Control+C to stop.", flush=True)
    try:
        while True:
            try:
                response = httpx.post(endpoint, params={"limit": 10}, timeout=60.0)
                response.raise_for_status()
                items = response.json()
                snapshot = json.dumps(items, sort_keys=True)
                if snapshot != previous_snapshot:
                    print_queue(items)
                    previous_snapshot = snapshot
            except httpx.HTTPError as exc:
                timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
                print(f"[{timestamp}] Monitor error: {exc}", flush=True)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitor stopped.", flush=True)


if __name__ == "__main__":
    main()
