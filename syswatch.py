#!/usr/bin/env python3
"""
syswatch.py — Linux System Health Monitor
Monitors CPU, memory, disk, and running services.
Logs results as structured JSON and alerts on threshold breaches.
"""

import json
import time
import argparse
import logging
import platform
from datetime import datetime, timezone

import psutil

# ── Default alert thresholds (%) ──────────────────────────────────────────────
THRESHOLDS = {
    "cpu_percent":    85.0,
    "memory_percent": 85.0,
    "disk_percent":   90.0,
}

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("syswatch")


# ── Data collection ───────────────────────────────────────────────────────────

def collect_cpu() -> dict:
    """Return CPU usage and per-core breakdown."""
    return {
        "percent_overall": psutil.cpu_percent(interval=1),
        "percent_per_core": psutil.cpu_percent(interval=None, percpu=True),
        "core_count_logical": psutil.cpu_count(logical=True),
        "core_count_physical": psutil.cpu_count(logical=False),
        "load_avg_1_5_15": list(psutil.getloadavg()),
    }


def collect_memory() -> dict:
    """Return RAM and swap usage."""
    ram  = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        "ram": {
            "total_gb":     round(ram.total  / 1e9, 2),
            "used_gb":      round(ram.used   / 1e9, 2),
            "available_gb": round(ram.available / 1e9, 2),
            "percent":      ram.percent,
        },
        "swap": {
            "total_gb": round(swap.total / 1e9, 2),
            "used_gb":  round(swap.used  / 1e9, 2),
            "percent":  swap.percent,
        },
    }


def collect_disk(path: str = "/") -> dict:
    """Return disk usage for the given mount point."""
    d = psutil.disk_usage(path)
    io = psutil.disk_io_counters()
    result = {
        "path":        path,
        "total_gb":    round(d.total / 1e9, 2),
        "used_gb":     round(d.used  / 1e9, 2),
        "free_gb":     round(d.free  / 1e9, 2),
        "percent":     d.percent,
    }
    if io:
        result["io"] = {
            "read_mb":  round(io.read_bytes  / 1e6, 2),
            "write_mb": round(io.write_bytes / 1e6, 2),
        }
    return result


def collect_network() -> dict:
    """Return basic network I/O stats."""
    net = psutil.net_io_counters()
    return {
        "bytes_sent_mb": round(net.bytes_sent / 1e6, 2),
        "bytes_recv_mb": round(net.bytes_recv / 1e6, 2),
        "packets_sent":  net.packets_sent,
        "packets_recv":  net.packets_recv,
        "errors_in":     net.errin,
        "errors_out":    net.errout,
    }


def collect_top_processes(n: int = 5) -> list:
    """Return the top N processes by CPU usage."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return sorted(procs, key=lambda x: x.get("cpu_percent") or 0, reverse=True)[:n]


def collect_system_info() -> dict:
    """Return static host information."""
    boot = datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc)
    uptime_secs = int((datetime.now(timezone.utc) - boot).total_seconds())
    return {
        "hostname":   platform.node(),
        "os":         platform.system(),
        "os_release": platform.release(),
        "arch":       platform.machine(),
        "python":     platform.python_version(),
        "boot_time":  boot.isoformat(),
        "uptime_seconds": uptime_secs,
        "uptime_human":   _fmt_uptime(uptime_secs),
    }


# ── Alert checking ────────────────────────────────────────────────────────────

def check_alerts(snapshot: dict) -> list:
    """Compare snapshot values against thresholds; return list of alert dicts."""
    alerts = []

    cpu_pct = snapshot["cpu"]["percent_overall"]
    if cpu_pct >= THRESHOLDS["cpu_percent"]:
        alerts.append({
            "level":   "WARNING",
            "metric":  "cpu_percent",
            "value":   cpu_pct,
            "threshold": THRESHOLDS["cpu_percent"],
            "message": f"CPU usage {cpu_pct}% exceeds {THRESHOLDS['cpu_percent']}% threshold",
        })

    mem_pct = snapshot["memory"]["ram"]["percent"]
    if mem_pct >= THRESHOLDS["memory_percent"]:
        alerts.append({
            "level":   "WARNING",
            "metric":  "memory_percent",
            "value":   mem_pct,
            "threshold": THRESHOLDS["memory_percent"],
            "message": f"Memory usage {mem_pct}% exceeds {THRESHOLDS['memory_percent']}% threshold",
        })

    disk_pct = snapshot["disk"]["percent"]
    if disk_pct >= THRESHOLDS["disk_percent"]:
        alerts.append({
            "level":   "CRITICAL",
            "metric":  "disk_percent",
            "value":   disk_pct,
            "threshold": THRESHOLDS["disk_percent"],
            "message": f"Disk usage {disk_pct}% exceeds {THRESHOLDS['disk_percent']}% threshold",
        })

    return alerts


# ── Snapshot builder ──────────────────────────────────────────────────────────

def take_snapshot(disk_path: str = "/") -> dict:
    """Collect all metrics and return a single timestamped snapshot."""
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "system":    collect_system_info(),
        "cpu":       collect_cpu(),
        "memory":    collect_memory(),
        "disk":      collect_disk(disk_path),
        "network":   collect_network(),
        "top_processes": collect_top_processes(),
    }
    snapshot["alerts"] = check_alerts(snapshot)
    snapshot["status"] = "ALERT" if snapshot["alerts"] else "OK"
    return snapshot


# ── Output helpers ────────────────────────────────────────────────────────────

def print_snapshot(snapshot: dict) -> None:
    """Pretty-print a snapshot to stdout in human-readable form."""
    s = snapshot["system"]
    c = snapshot["cpu"]
    m = snapshot["memory"]["ram"]
    d = snapshot["disk"]

    status_color = "\033[91m" if snapshot["status"] == "ALERT" else "\033[92m"
    reset = "\033[0m"

    print("\n" + "═" * 60)
    print(f"  SysWatch  │  {s['hostname']}  │  {snapshot['timestamp']}")
    print("═" * 60)
    print(f"  Status   : {status_color}{snapshot['status']}{reset}")
    print(f"  Uptime   : {s['uptime_human']}")
    print(f"  OS       : {s['os']} {s['os_release']} ({s['arch']})")
    print("─" * 60)
    print(f"  CPU      : {c['percent_overall']}%   "
          f"load avg {c['load_avg_1_5_15'][0]:.2f} / "
          f"{c['load_avg_1_5_15'][1]:.2f} / "
          f"{c['load_avg_1_5_15'][2]:.2f}")
    print(f"  Memory   : {m['percent']}%   "
          f"{m['used_gb']} GB / {m['total_gb']} GB used")
    print(f"  Disk ({d['path']}) : {d['percent']}%   "
          f"{d['used_gb']} GB / {d['total_gb']} GB used")
    print("─" * 60)
    if snapshot["alerts"]:
        print("  ⚠  ALERTS:")
        for a in snapshot["alerts"]:
            print(f"     [{a['level']}] {a['message']}")
    else:
        print("  ✓  All metrics within normal thresholds.")
    print("═" * 60 + "\n")


def _fmt_uptime(seconds: int) -> str:
    days, rem  = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    mins, _    = divmod(rem, 60)
    return f"{days}d {hours}h {mins}m"


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="SysWatch — Linux System Health Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run once, human-readable output
  python syswatch.py

  # Run every 30 seconds, JSON output to file
  python syswatch.py --interval 30 --json --output logs/metrics.jsonl

  # Watch a specific disk path
  python syswatch.py --disk /var
        """,
    )
    p.add_argument("--interval", type=int, default=0,
                   help="Poll interval in seconds (0 = run once, default: 0)")
    p.add_argument("--disk", default="/",
                   help="Disk path to monitor (default: /)")
    p.add_argument("--json", action="store_true",
                   help="Output structured JSON instead of human-readable text")
    p.add_argument("--output", default=None,
                   help="Append JSON snapshots to this file (one JSON object per line)")
    p.add_argument("--cpu-threshold", type=float, default=THRESHOLDS["cpu_percent"],
                   help=f"CPU alert threshold %% (default: {THRESHOLDS['cpu_percent']})")
    p.add_argument("--mem-threshold", type=float, default=THRESHOLDS["memory_percent"],
                   help=f"Memory alert threshold %% (default: {THRESHOLDS['memory_percent']})")
    p.add_argument("--disk-threshold", type=float, default=THRESHOLDS["disk_percent"],
                   help=f"Disk alert threshold %% (default: {THRESHOLDS['disk_percent']})")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # Apply custom thresholds
    THRESHOLDS["cpu_percent"]    = args.cpu_threshold
    THRESHOLDS["memory_percent"] = args.mem_threshold
    THRESHOLDS["disk_percent"]   = args.disk_threshold

    log.info("SysWatch starting — disk=%s interval=%ss", args.disk, args.interval)

    try:
        while True:
            snapshot = take_snapshot(disk_path=args.disk)

            if args.json:
                line = json.dumps(snapshot)
                print(line)
                if args.output:
                    with open(args.output, "a") as f:
                        f.write(line + "\n")
            else:
                print_snapshot(snapshot)

            # Log alerts regardless of output mode
            for alert in snapshot["alerts"]:
                log.warning(alert["message"])

            if args.interval == 0:
                break
            time.sleep(args.interval)

    except KeyboardInterrupt:
        log.info("SysWatch stopped by user.")


if __name__ == "__main__":
    main()
