# 🖥️ SysWatch — Linux System Health Monitor

![CI](https://github.com/josimar549/syswatch/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A production-style Python CLI tool that monitors CPU, memory, disk, and network metrics on Linux systems. Outputs human-readable reports or structured JSON logs, and fires alerts when configurable thresholds are breached.

---

## Features

- **Real-time metrics** — CPU (overall + per-core + load avg), RAM, swap, disk I/O, network I/O
- **Threshold alerts** — configurable WARNING/CRITICAL alerts logged to stderr
- **Structured JSON output** — machine-readable logs, one snapshot per line (JSONL format)
- **Continuous polling** — run once or loop on a configurable interval
- **Docker-ready** — multi-stage Dockerfile, non-root user, log volume mount
- **CI/CD pipeline** — GitHub Actions: lint → test → Docker build → smoke test

---

## Quick Start

### Run locally (Python)

```bash
# Install dependency
pip install -r requirements.txt

# One-shot human-readable output
python syswatch.py

# Poll every 30 seconds, JSON to stdout
python syswatch.py --interval 30 --json

# Write JSON logs to file with custom thresholds
python syswatch.py --interval 60 --json --output logs/metrics.jsonl \
  --cpu-threshold 80 --mem-threshold 80 --disk-threshold 85
```

### Run with Docker

```bash
# Build image
docker build -t syswatch .

# Run once
docker run --rm syswatch python syswatch.py

# Run with persistent logs
docker run -d \
  --name syswatch \
  -v $(pwd)/logs:/app/logs \
  syswatch
```

### Run with Docker Compose

```bash
docker compose up -d          # start in background
docker compose logs -f        # tail logs
docker compose down           # stop
```

---

## Sample Output

**Human-readable (`python syswatch.py`):**
```
════════════════════════════════════════════════════════════
  SysWatch  │  my-server  │  2025-06-01T14:22:33Z
════════════════════════════════════════════════════════════
  Status   : OK
  Uptime   : 3d 7h 12m
  OS       : Linux 5.15.0 (x86_64)
────────────────────────────────────────────────────────────
  CPU      : 12.4%   load avg 0.45 / 0.38 / 0.31
  Memory   : 54.2%   8.68 GB / 16.0 GB used
  Disk (/) : 37.8%   75.6 GB / 200.0 GB used
────────────────────────────────────────────────────────────
  ✓  All metrics within normal thresholds.
════════════════════════════════════════════════════════════
```

**JSON output (`--json`):**
```json
{
  "timestamp": "2025-06-01T14:22:33Z",
  "status": "OK",
  "cpu": { "percent_overall": 12.4, "load_avg_1_5_15": [0.45, 0.38, 0.31] },
  "memory": { "ram": { "percent": 54.2, "used_gb": 8.68, "total_gb": 16.0 } },
  "disk": { "path": "/", "percent": 37.8, "used_gb": 75.6, "total_gb": 200.0 },
  "alerts": []
}
```

---

## CLI Reference

```
usage: syswatch.py [-h] [--interval INTERVAL] [--disk DISK]
                   [--json] [--output OUTPUT]
                   [--cpu-threshold CPU_THRESHOLD]
                   [--mem-threshold MEM_THRESHOLD]
                   [--disk-threshold DISK_THRESHOLD]

Options:
  --interval INT        Poll interval in seconds (0 = run once, default: 0)
  --disk PATH           Disk path to monitor (default: /)
  --json                Output structured JSON instead of human-readable text
  --output FILE         Append JSON snapshots to this file (JSONL format)
  --cpu-threshold FLOAT CPU alert threshold % (default: 85.0)
  --mem-threshold FLOAT Memory alert threshold % (default: 85.0)
  --disk-threshold FLOAT Disk alert threshold % (default: 90.0)
```

---

## Project Structure

```
syswatch/
├── syswatch.py              # Main application
├── requirements.txt         # Python dependencies
├── Dockerfile               # Multi-stage Docker build
├── docker-compose.yml       # Compose config with log volume
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml           # CI: lint → test → Docker build
└── tests/
    └── test_syswatch.py     # pytest unit + integration tests
```

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.12 | Core language |
| psutil | Cross-platform system metrics |
| pytest | Unit & integration testing |
| flake8 | Linting / code style |
| Docker | Containerization (multi-stage build) |
| GitHub Actions | CI/CD pipeline |

---

## What I Learned / Demonstrated

- Writing production-grade Python CLI tooling with `argparse`, `logging`, and structured output
- Linux system metrics collection via `psutil` (CPU, memory, disk, network, processes)
- Containerizing a Python app with a multi-stage Dockerfile and non-root user
- Writing a real test suite with `pytest` covering unit and integration scenarios
- Building a CI/CD pipeline with GitHub Actions (lint → test → Docker build → smoke test)
- JSON / JSONL structured logging patterns used in production observability pipelines

---

## Author

**Josimar Arias** — Software Engineer · Mesa, AZ  
[josimar85209@gmail.com](mailto:josimar85209@gmail.com) · [GitHub](https://github.com/josimar549)

---

## License

MIT
