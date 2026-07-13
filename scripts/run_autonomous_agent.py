import argparse
import json
import time
from datetime import datetime

import httpx


def timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the autonomous KRkRice Jira helpdesk agent.")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds (minimum 10).")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Local KRkRice API base URL.")
    args = parser.parse_args()
    endpoint = f"{args.url.rstrip('/')}/api/jira/autonomous-run"
    learning_endpoint = f"{args.url.rstrip('/')}/api/jira/learning-run"
    interval = max(args.interval, 10)

    print(f"Autonomous agent watching Jira every {interval} seconds. Press Control+C to stop.", flush=True)
    try:
        while True:
            try:
                response = httpx.post(
                    endpoint,
                    params={"limit": 10},
                    json={"confirm": "RUN_AUTONOMOUS"},
                    timeout=120.0,
                )
                response.raise_for_status()
                for result in response.json():
                    print(f"[{timestamp()}] {result['issue_key']}: {result['decision']} -> {result['status']}", flush=True)
                learning_response = httpx.post(
                    learning_endpoint,
                    params={"limit": 10},
                    json={"confirm": "RUN_LEARNING"},
                    timeout=120.0,
                )
                learning_response.raise_for_status()
                for article in learning_response.json():
                    print(
                        f"[{timestamp()}] {article['source_issue_key']}: learned -> {article['article_id']}",
                        flush=True,
                    )
            except httpx.HTTPError as exc:
                print(f"[{timestamp()}] Autonomous agent error: {exc}", flush=True)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nAutonomous agent stopped.", flush=True)


if __name__ == "__main__":
    main()
