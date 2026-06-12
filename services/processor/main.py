"""Processor worker — pops events from the Redis list and processes them.

Designed to run as a CronJob: drains the queue (up to BATCH_SIZE), then exits.
Bad events are moved to a dead-letter queue (events:dlq) instead of being dropped.
Exits with code 1 on Redis connection failure so k8s backoffLimit triggers.
"""

import os
import json
import sys

import redis

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
QUEUE_KEY = os.getenv("QUEUE_KEY", "events:queue")
DLQ_KEY = os.getenv("DLQ_KEY", "events:dlq")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))


def process_event(event: dict) -> None:
    """Simulate processing — just log the event."""
    print(f"[processed] id={event['id']} ts={event['timestamp']}")


def main() -> None:
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
    except redis.RedisError as e:
        print(f"[error] cannot connect to Redis: {e}", file=sys.stderr)
        sys.exit(1)

    processed = 0
    dead = 0

    while processed + dead < BATCH_SIZE:
        raw = r.lpop(QUEUE_KEY)
        if raw is None:
            break
        try:
            event = json.loads(raw)
            process_event(event)
            processed += 1
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[dlq] malformed event, moving to {DLQ_KEY}: {e}", file=sys.stderr)
            r.rpush(DLQ_KEY, raw)
            dead += 1

    print(f"[done] processed={processed} dead_lettered={dead}")


if __name__ == "__main__":
    main()
