# \# Xray Azure Blob Prometheus Exporter

# 

# Prometheus metrics exporter that reads Xray-core user traffic statistics from JSON files stored in \*\*Azure Blob Storage\*\*.

# 

# \## Features

# 

# \- Reads latest `<server\_id>/<timestamp>.json` file

# \- Exposes per-user uplink/downlink/total traffic counters

# \- Uses Azure AD authentication (managed identity, workload identity, CLI, etc.)

# \- Configured entirely via environment variables

# \- Simple `/health` endpoint

# 

# \## Metrics

# 

# \- `xray\_user\_uplink\_bytes\_total{server\_id, user}`

# \- `xray\_user\_downlink\_bytes\_total{server\_id, user}`

# \- `xray\_user\_traffic\_bytes\_total{server\_id, user}`

# \- `xray\_last\_update\_success`

# \- `xray\_last\_blob\_timestamp\_seconds`

# 

# \## Quick Start (Docker)

# 

# ```bash

# docker run -d --name xray-exporter \\

# &nbsp; -p 9101:9101 \\

# &nbsp; -e AZURE\_STORAGE\_ACCOUNT\_NAME="mystorageacct" \\

# &nbsp; -e AZURE\_CONTAINER\_NAME="xray-stats" \\

# &nbsp; -e XRAY\_SERVER\_ID="sg-sin-01" \\

# &nbsp; -e METRICS\_UPDATE\_EVERY\_SECONDS=30 \\

# &nbsp; ghcr.io/yourusername/xray-azureblob-exporter:latest

