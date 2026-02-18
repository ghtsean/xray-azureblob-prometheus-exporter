#!/usr/bin/env python3
"""
Prometheus exporter for Xray user traffic statistics stored in Azure Blob Storage.

Expects JSON files in container with path pattern:
<server_id>/<timestamp>.json

Example JSON structure (per convention used in your original code):
{
  "users": {
    "user1@example.com": {"up": 123456, "down": 789012},
    "user2@domain.net": {"up": 456, "down": 111}
  },
  "timestamp": 1700000000,
  ...
}
"""

import json
import os
import time
import logging
from typing import Optional
from flask import Flask, Response, jsonify
from prometheus_client import Counter, generate_latest, REGISTRY, Gauge
from azure.identity import DefaultAzureCredential, EnvironmentCredential, ChainedTokenCredential
from azure.storage.blob import BlobServiceClient, ContainerClient

app = Flask(__name__)

# --------------------- Configuration via environment variables ---------------------
STORAGE_ACCOUNT      = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "")
CONTAINER_NAME       = os.getenv("AZURE_CONTAINER_NAME", "xray-stats")
SERVER_ID            = os.getenv("XRAY_SERVER_ID", "unknown-server")
PORT                 = int(os.getenv("PORT", "9101"))
METRICS_UPDATE_EVERY = int(os.getenv("METRICS_UPDATE_EVERY_SECONDS", "30"))

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------- Prometheus metrics ---------------------
PREFIX = "xray_"

user_uplink_bytes = Counter(
    f"{PREFIX}user_uplink_bytes_total",
    "Total uplink bytes per user",
    ["server_id", "user"]
)
user_downlink_bytes = Counter(
    f"{PREFIX}user_downlink_bytes_total",
    "Total downlink bytes per user",
    ["server_id", "user"]
)
user_traffic_bytes = Counter(
    f"{PREFIX}user_traffic_bytes_total",
    "Total (up+down) bytes per user",
    ["server_id", "user"]
)

last_update_success = Gauge(
    f"{PREFIX}last_update_success",
    "1 if last metrics update from blob was successful, 0 otherwise"
)
last_blob_timestamp = Gauge(
    f"{PREFIX}last_blob_timestamp_seconds",
    "Timestamp of the latest JSON blob processed"
)

# --------------------- Azure Blob Client ---------------------
credential = ChainedTokenCredential(
    EnvironmentCredential(),
    DefaultAzureCredential()
)

if not STORAGE_ACCOUNT:
    logger.error("AZURE_STORAGE_ACCOUNT_NAME is required")
    exit(1)

account_url = f"https://{STORAGE_ACCOUNT}.blob.core.windows.net"
blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
container_client: ContainerClient = blob_service_client.get_container_client(CONTAINER_NAME)

# Cache control
_last_blob_name: Optional[str] = None
_last_update_time = 0.0


def get_latest_blob_name() -> Optional[str]:
    """Find the newest <server_id>/<timestamp>.json blob"""
    prefix = f"{SERVER_ID}/"
    latest_blob = None
    latest_ts = 0

    try:
        for blob in container_client.list_blobs(name_starts_with=prefix):
            try:
                # expected: server-01/1739999999.json
                filename = blob.name.split("/")[-1]
                if not filename.endswith(".json"):
                    continue
                ts_str = filename[:-5]  # remove .json
                ts = int(ts_str)
                if ts > latest_ts:
                    latest_ts = ts
                    latest_blob = blob.name
            except (ValueError, IndexError):
                continue
        return latest_blob
    except Exception as e:
        logger.exception("Failed to list blobs: %s", e)
        return None


def update_metrics_from_blob():
    global _last_blob_name, _last_update_time

    now = time.time()
    if now - _last_update_time < METRICS_UPDATE_EVERY:
        return  # rate limit

    blob_name = get_latest_blob_name()
    if not blob_name:
        logger.warning("No valid stats blob found for server %s", SERVER_ID)
        last_update_success.set(0)
        return

    if blob_name == _last_blob_name:
        _last_update_time = now
        return  # already processed

    try:
        blob_client = container_client.get_blob_client(blob_name)
        data = blob_client.download_blob().readall()
        payload = json.loads(data)

        # Reset counters (important if users disappear)
        user_uplink_bytes.clear()
        user_downlink_bytes.clear()
        user_traffic_bytes.clear()

        users = payload.get("users", {})
        for user, values in users.items():
            up = int(values.get("up", 0))
            down = int(values.get("down", 0))

            labels = {"server_id": SERVER_ID, "user": user}

            user_uplink_bytes.labels(**labels).inc(up)     # or .set(up) if absolute
            user_downlink_bytes.labels(**labels).inc(down)
            user_traffic_bytes.labels(**labels).inc(up + down)

        # Update metadata gauges
        ts = int(blob_name.split("/")[-1].replace(".json", ""))
        last_blob_timestamp.set(ts)
        last_update_success.set(1)

        _last_blob_name = blob_name
        _last_update_time = now
        logger.info("Metrics updated from %s (users: %d)", blob_name, len(users))

    except Exception as e:
        logger.exception("Failed to process blob %s: %s", blob_name, e)
        last_update_success.set(0)


@app.route("/metrics")
def metrics():
    update_metrics_from_blob()
    return Response(generate_latest(REGISTRY), mimetype="text/plain; version=0.0.4")


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "server_id": SERVER_ID,
        "last_blob": _last_blob_name,
        "last_update": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(_last_update_time))
    })


if __name__ == "__main__":
    if os.getenv("FLASK_ENV") == "development":
        app.run(host="0.0.0.0", port=PORT, debug=True)
    else:
        app.run(host="0.0.0.0", port=PORT)