"""Test CloudSafeEvent schema and validation."""

import unittest

from emg_gate.cloud_safe_event import (
    CloudSafeEventError,
    create_cloud_safe_event,
    gate_event_to_cloud_safe,
    validate_cloud_safe_event,
)


class TestCloudSafeEvent(unittest.TestCase):
    def test_create_valid_event(self):
        """Test creating a valid CloudSafeEvent."""
        event = create_cloud_safe_event(
            kind="band_change",
            quality="ok",
            t_host_ms=1234567890.0,
            band=1,
            confidence=0.75,
        )

        self.assertEqual(event["kind"], "band_change")
        self.assertEqual(event["quality"], "ok")
        self.assertEqual(event["band"], 1)
        self.assertNotIn("raw_window", event)
        self.assertNotIn("raw_uV", event)

    def test_reject_raw_window(self):
        """Test that raw_window is rejected."""
        event = {
            "schema_version": "1.0.0",
            "kind": "band_change",
            "quality": "ok",
            "t_host_ms": 1234567890.0,
            "raw_window": [1.0, 2.0, 3.0],
        }

        with self.assertRaises(CloudSafeEventError):
            validate_cloud_safe_event(event)

    def test_reject_raw_uV(self):
        """Test that raw_uV is rejected."""
        event = {
            "schema_version": "1.0.0",
            "kind": "band_change",
            "quality": "ok",
            "t_host_ms": 1234567890.0,
            "raw_uV": [1.0, 2.0, 3.0],
        }

        with self.assertRaises(CloudSafeEventError):
            validate_cloud_safe_event(event)

    def test_reject_raw_adc(self):
        """Test that raw_adc is rejected."""
        event = {
            "schema_version": "1.0.0",
            "kind": "band_change",
            "quality": "ok",
            "t_host_ms": 1234567890.0,
            "raw_adc": [100, 200, 300],
        }

        with self.assertRaises(CloudSafeEventError):
            validate_cloud_safe_event(event)

    def test_gate_event_conversion(self):
        """Test converting gate event to CloudSafeEvent."""
        gate_event = {
            "band": 1,
            "confidence": 0.72,
            "quality": "ok",
            "t_host_ms": 1234567890.0,
            "event_suppressed": False,
            "raw_uV": [1.0, 2.0, 3.0],
        }

        cloud_event = gate_event_to_cloud_safe(gate_event)

        validate_cloud_safe_event(cloud_event)
        self.assertNotIn("raw_uV", cloud_event)
        self.assertEqual(cloud_event["band"], 1)
        self.assertEqual(cloud_event["quality"], "ok")

    def test_gate_event_suppressed_conversion(self):
        """Test converting suppressed gate event."""
        gate_event = {
            "band": 0,
            "confidence": 0.2,
            "quality": "lead_off",
            "t_host_ms": 1234567890.0,
            "event_suppressed": True,
        }

        cloud_event = gate_event_to_cloud_safe(gate_event)
        validate_cloud_safe_event(cloud_event)

        self.assertIn("suppressed", cloud_event["kind"])

    def test_missing_required_field(self):
        """Test that missing required field raises error."""
        event = {
            "schema_version": "1.0.0",
            "kind": "band_change",
        }

        with self.assertRaises(CloudSafeEventError):
            validate_cloud_safe_event(event)


if __name__ == "__main__":
    unittest.main()
