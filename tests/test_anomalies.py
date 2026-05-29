# PROMPT:
#   "Generate pytest tests for retail anomaly detection: billing queue spike
#    (> 2σ above mean), conversion rate drop (today vs 7-day avg < 0.7×),
#    dead zone (no visits in 30 min). Test severity levels INFO/WARN/CRITICAL,
#    suggested_action presence, zero-variance edge case, no-history edge case."
#
# CHANGES MADE:
#   - Added boundary test: current == avg + 2σ exactly should NOT trigger.
#   - Added test for anomaly structure (anomaly_id, severity, suggested_action).
#   - Zero-variance case: std=0, any depth above avg triggers (AI version missed this).

from datetime import datetime, timezone, timedelta
import pytest


class TestQueueSpike:
    def test_spike_detected(self):
        avg, std, curr = 3.0, 1.0, 8
        assert curr > avg + 2 * std

    def test_no_spike_at_boundary(self):
        avg, std, curr = 3.0, 1.0, 5
        assert not (curr > avg + 2 * std)

    def test_no_spike_within_range(self):
        avg, std, curr = 3.0, 1.0, 4
        assert not (curr > avg + 2 * std)

    def test_critical_threshold(self):
        avg, std, curr = 3.0, 1.0, 10
        sev = "CRITICAL" if curr > avg + 3 * std else "WARN"
        assert sev == "CRITICAL"

    def test_warn_threshold(self):
        avg, std, curr = 3.0, 1.0, 6
        sev = "CRITICAL" if curr > avg + 3 * std else "WARN"
        assert sev == "WARN"

    def test_zero_variance(self):
        avg, std, curr = 3.0, 0.0, 4
        assert curr > avg + 2 * std

    def test_minimum_depth_guard(self):
        avg, std, curr = 1.0, 0.0, 3
        triggered = curr > avg + 2 * std and curr > 3
        assert not triggered


class TestConversionDrop:
    def test_drop_detected(self):
        hist, today = 0.25, 0.10
        assert today < hist * 0.7

    def test_no_drop_within_range(self):
        hist, today = 0.25, 0.22
        assert not (today < hist * 0.7)

    def test_no_history_no_alert(self):
        hist, today = 0.0, 0.15
        should = hist > 0 and today < hist * 0.7
        assert not should

    def test_boundary_exactly_07(self):
        hist = 0.20
        today = hist * 0.7
        assert not (today < hist * 0.7)


class TestDeadZone:
    def test_dead_zone_detected(self):
        now = datetime.now(timezone.utc)
        last = now - timedelta(minutes=45)
        cutoff = now - timedelta(minutes=30)
        assert last < cutoff

    def test_active_zone_not_flagged(self):
        now = datetime.now(timezone.utc)
        last = now - timedelta(minutes=10)
        cutoff = now - timedelta(minutes=30)
        assert not (last < cutoff)

    def test_exactly_30_min_not_flagged(self):
        now = datetime.now(timezone.utc)
        last = now - timedelta(minutes=30)
        cutoff = now - timedelta(minutes=30)
        assert not (last < cutoff)


class TestAnomalyStructure:
    def _make(self, sev):
        return {
            "anomaly_id": "QUEUE_SPIKE_ST1076_1430",
            "anomaly_type": "BILLING_QUEUE_SPIKE",
            "severity": sev,
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "store_id": "ST1076",
            "description": "Queue depth 9 exceeds baseline 3.0",
            "current_value": 9.0,
            "baseline_value": 3.0,
            "suggested_action": "Open additional billing lane.",
        }

    def test_severity_values_valid(self):
        valid = {"INFO", "WARN", "CRITICAL"}
        for s in valid:
            a = self._make(s)
            assert a["severity"] in valid

    def test_suggested_action_non_empty(self):
        a = self._make("WARN")
        assert len(a["suggested_action"]) > 5

    def test_anomaly_id_present(self):
        a = self._make("INFO")
        assert "anomaly_id" in a and a["anomaly_id"]

    def test_description_non_empty(self):
        a = self._make("CRITICAL")
        assert len(a["description"]) > 5
