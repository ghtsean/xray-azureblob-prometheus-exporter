# =============================================================================
# Dockerfile for xray-azureblob-prometheus-exporter
# Multi-stage build → small final image (~100-120 MB)
# =============================================================================

# ────────────────────────────────────────
# Builder stage
# ────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ────────────────────────────────────────
# Final runtime stage
# ────────────────────────────────────────
FROM python:3.12-slim

# Labels (good GitHub practice)
LABEL org.opencontainers.image.title="Xray Azure Blob Prometheus Exporter" \
      org.opencontainers.image.description="Prometheus exporter for Xray-core user traffic stats from Azure Blob Storage JSON snapshots" \
      org.opencontainers.image.source="https://github.com/YOUR_USERNAME/xray-azureblob-prometheus-exporter" \
      org.opencontainers.image.licenses="MIT" \
      maintainer="Your Name <your-email@example.com>"

# Create non-root user (security best practice)
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy only the installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY src/ /app/src/
# If you renamed main file → adjust here
# COPY src/app.py /app/   (or src/main.py)

# Ensure directory permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the metrics port (standard for Prometheus exporters is often 8000–9100+)
EXPOSE 9101

# Healthcheck (optional but recommended)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:9101/health || exit 1

# Run the application
# Adjust filename if you use main.py instead of app.py
CMD ["python", "-u", "src/app.py"]