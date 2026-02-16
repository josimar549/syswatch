"""
tests/test_syswatch.py
Unit tests for syswatch.py — verifies data collection and alert logic.
"""

import pytest
import sys
import os

# Make sure the parent directory is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import syswatch


# ── Data collection tests ──────────────────────────────────────────────────────

class TestCollectCpu:
    def test_returns_dict(self):
        result = syswatch.collect_cpu()
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = syswatch.collect_cpu()
        assert "percent_overall" in result
        assert "percent_per_core" in result
        assert "core_count_logical" in result
        assert "load_avg_1_5_15" in result

    def test_percent_in_valid_range(self):
        result = syswatch.collect_cpu()
        assert 0.0 <= result["percent_overall"] <= 100.0

    def test_load_avg_has_three_values(self):
        result = syswatch.collect_cpu()
        assert len(result["load_avg_1_5_15"]) == 3


class TestCollectMemory:
    def test_returns_dict_with_ram_and_swap(self):
        result = syswatch.collect_memory()
        assert "ram" in result
        assert "swap" in result

    def test_ram_percent_in_valid_range(self):
        result = syswatch.collect_memory()
        assert 0.0 <= result["ram"]["percent"] <= 100.0

    def test_ram_used_not_greater_than_total(self):
        result = syswatch.collect_memory()
        assert result["ram"]["used_gb"] <= result["ram"]["total_gb"]


class TestCollectDisk:
    def test_returns_dict(self):
        result = syswatch.collect_disk("/")
        assert isinstance(result, dict)

    def test_has_path(self):
        result = syswatch.collect_disk("/")
        assert result["path"] == "/"

    def test_percent_in_valid_range(self):
        result = syswatch.collect_disk("/")
        assert 0.0 <= result["percent"] <= 100.0

    def test_custom_path(self):
        result = syswatch.collect_disk("/tmp")
        assert result["path"] == "/tmp"


class TestCollectNetwork:
    def test_returns_dict(self):
        result = syswatch.collect_network()
        assert isinstance(result, dict)

    def test_has_sent_and_recv(self):
        result = syswatch.collect_network()
        assert "bytes_sent_mb" in result
        assert "bytes_recv_mb" in result

    def test_values_non_negative(self):
        result = syswatch.collect_network()
        assert result["bytes_sent_mb"] >= 0
        assert result["bytes_recv_mb"] >= 0


class TestCollectSystemInfo:
    def test_returns_dict(self):
        result = syswatch.collect_system_info()
        assert isinstance(result, dict)

    def test_has_hostname(self):
        result = syswatch.collect_system_info()
        assert "hostname" in result
        assert len(result["hostname"]) > 0

    def test_uptime_positive(self):
        result = syswatch.collect_system_info()
        assert result["uptime_seconds"] > 0


# ── Alert logic tests ──────────────────────────────────────────────────────────

class TestCheckAlerts:
    def _make_snapshot(self, cpu=10.0, mem=10.0, disk=10.0):
        """Build a minimal fake snapshot for alert testing."""
        return {
            "cpu":    {"percent_overall": cpu},
            "memory": {"ram": {"percent": mem}},
            "disk":   {"percent": disk},
        }

    def test_no_alerts_when_below_thresholds(self):
        snap = self._make_snapshot(cpu=10.0, mem=20.0, disk=30.0)
        alerts = syswatch.check_alerts(snap)
        assert alerts == []

    def test_cpu_alert_fires_at_threshold(self):
        syswatch.THRESHOLDS["cpu_percent"] = 85.0
        snap = self._make_snapshot(cpu=90.0)
        alerts = syswatch.check_alerts(snap)
        assert any(a["metric"] == "cpu_percent" for a in alerts)

    def test_memory_alert_fires_at_threshold(self):
        syswatch.THRESHOLDS["memory_percent"] = 85.0
        snap = self._make_snapshot(mem=90.0)
        alerts = syswatch.check_alerts(snap)
        assert any(a["metric"] == "memory_percent" for a in alerts)

    def test_disk_alert_fires_at_threshold(self):
        syswatch.THRESHOLDS["disk_percent"] = 90.0
        snap = self._make_snapshot(disk=95.0)
        alerts = syswatch.check_alerts(snap)
        assert any(a["metric"] == "disk_percent" for a in alerts)

    def test_disk_alert_is_critical(self):
        syswatch.THRESHOLDS["disk_percent"] = 90.0
        snap = self._make_snapshot(disk=95.0)
        alerts = syswatch.check_alerts(snap)
        disk_alert = next(a for a in alerts if a["metric"] == "disk_percent")
        assert disk_alert["level"] == "CRITICAL"

    def test_no_alert_just_below_threshold(self):
        syswatch.THRESHOLDS["cpu_percent"] = 85.0
        snap = self._make_snapshot(cpu=84.9)
        alerts = syswatch.check_alerts(snap)
        assert not any(a["metric"] == "cpu_percent" for a in alerts)


# ── Snapshot integration test ──────────────────────────────────────────────────

class TestTakeSnapshot:
    def test_snapshot_has_all_sections(self):
        snap = syswatch.take_snapshot()
        for key in ["timestamp", "system", "cpu", "memory", "disk", "network", "alerts", "status"]:
            assert key in snap

    def test_snapshot_status_is_ok_or_alert(self):
        snap = syswatch.take_snapshot()
        assert snap["status"] in ("OK", "ALERT")

    def test_timestamp_ends_with_z(self):
        snap = syswatch.take_snapshot()
        assert snap["timestamp"].endswith("Z")


# ── Utility tests ──────────────────────────────────────────────────────────────

class TestFmtUptime:
    def test_zero(self):
        assert syswatch._fmt_uptime(0) == "0d 0h 0m"

    def test_one_hour(self):
        assert syswatch._fmt_uptime(3600) == "0d 1h 0m"

    def test_one_day(self):
        assert syswatch._fmt_uptime(86400) == "1d 0h 0m"

    def test_mixed(self):
        # 1 day + 2 hours + 30 minutes
        secs = 86400 + 7200 + 1800
        assert syswatch._fmt_uptime(secs) == "1d 2h 30m"
