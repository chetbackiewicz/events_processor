"""Ingestion API — accepts events and pushes them onto a Redis list."""

import os
import json
import time
import uuid

from flask import Flask, request, jsonify
import redis

app = Flask(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
QUEUE_KEY = os.getenv("QUEUE_KEY", "events:queue")

pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def get_redis():
    return redis.Redis(connection_pool=pool)


@app.route("/health", methods=["GET"])
def health():
    try:
        get_redis().ping()
        return jsonify({"status": "ok"})
    except Exception:
        return jsonify({"status": "degraded", "reason": "redis unreachable"}), 503


@app.route("/events", methods=["POST"])
def ingest_event():
    payload = request.get_json(force=True)
    event = {
        "id": str(uuid.uuid4()),
        "timestamp": time.time(),
        "payload": payload,
    }
    r = get_redis()
    r.rpush(QUEUE_KEY, json.dumps(event))
    return jsonify({"accepted": True, "event_id": event["id"]}), 202


@app.route("/queue/length", methods=["GET"])
def queue_length():
    r = get_redis()
    length = r.llen(QUEUE_KEY)
    return jsonify({"queue": QUEUE_KEY, "length": length})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
