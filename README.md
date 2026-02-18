# Xray Azure Blob Prometheus Exporter

Prometheus metrics exporter that reads Xray-core user traffic statistics from JSON files stored in **Azure Blob Storage**.

## Features

- Reads latest `<server_id>/<timestamp>.json` file
- Exposes per-user uplink/downlink/total traffic counters
- Uses Azure AD authentication (managed identity, workload identity, CLI, etc.)
- Configured entirely via environment variables
- Simple `/health` endpoint

## Metrics

- `xray_user_uplink_bytes_total{server_id, user}`
- `xray_user_downlink_bytes_total{server_id, user}`
- `xray_user_traffic_bytes_total{server_id, user}`
- `xray_last_update_success`
- `xray_last_blob_timestamp_seconds`

## Quick Start (Docker)

```bash
docker run -d --name xray-exporter \
  -p 9101:9101 \
  -e AZURE_STORAGE_ACCOUNT_NAME="mystorageacct" \
  -e AZURE_CONTAINER_NAME="xray-stats" \
  -e XRAY_SERVER_ID="sg-sin-01" \
  -e METRICS_UPDATE_EVERY_SECONDS=30 \
  ghcr.io/yourusername/xray-azureblob-exporter:latest