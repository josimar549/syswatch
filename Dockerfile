# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install dependencies into a local dir so we can copy them cleanly
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --target=/app/deps -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

LABEL maintainer="Josimar Arias <josimar85209@gmail.com>" \
      description="SysWatch — Linux System Health Monitor" \
      version="1.0.0"

WORKDIR /app

# Copy installed packages and source
COPY --from=builder /app/deps /app/deps
COPY syswatch.py .

# Put our deps on the Python path
ENV PYTHONPATH="/app/deps"
ENV PYTHONUNBUFFERED=1

# Create a non-root user (security best practice)
RUN useradd --system --no-create-home syswatch && \
    mkdir -p /app/logs && \
    chown syswatch:syswatch /app/logs

USER syswatch

# Run once by default; override CMD in docker run or compose
CMD ["python", "syswatch.py", "--interval", "30", "--json", "--output", "/app/logs/metrics.jsonl"]
