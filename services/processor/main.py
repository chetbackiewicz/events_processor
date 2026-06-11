"""Processor worker — pops events from the Redis list and processes them.

Designed to run as a CronJob: drains the queue (up to BATCH_SIZE), then exits.
"""

import os
import json
import time

import redis

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
QUEUE_KEY = os.getenv("QUEUE_KEY", "events:queue")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))


def process_event(event: dict) -> None:
    """Simulate processing — just log the event."""
    print(f"[processed] id={event['id']} ts={event['timestamp']}")


def main() -> None:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    processed = 0

    while processed < BATCH_SIZE:
        raw = r.lpop(QUEUE_KEY)
        if raw is None:
            break
        event = json.loads(raw)
        process_event(event)
        processed += 1

    print(f"[done] processed {processed} events")


if __name__ == "__main__":
    main()
