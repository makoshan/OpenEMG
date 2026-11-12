"""JSON Schema files ↔ Python validators stay in lock-step.

If `jsonschema` happens to be installed the sample objects are additionally
validated against the JSON files; otherwise that part is skipped (numpy-only
is the hard dependency policy).
"""

import unittest

try:
    import jsonschema
except ImportError:  # optional dependency; numpy-only is the hard policy
    jsonschema = None

from emg_gate import calibration_profile, capture_session, cloud_safe_event
from emg_gate.calibration_profile import CalibrationProfileError, create_calibration_profile, validate_calibration_profile
from emg_gate.capture_session import CaptureSessionError, create_capture_session, validate_capture_session
from emg_gate.cloud_safe_event import CloudSafeEventError, create_cloud_safe_event, validate_cloud_safe_event
from emg_gate.schemas import SCHEMA_NAMES, load_schema, required, whitelist

HAS_JSONSCHEMA = jsonschema is not None


def _sample_session(**over):
    base = dict(
        user_id="u", device_id="d", session_id="s", donning_id="don", gesture_label="rest",
        obs_ts_device_ms=1.0, obs_ts_host_ms=2.0, feature_window={"band": 0, "norm": 0.1},
    )
    base.update(over)
    return create_capture_session(**base)


class TestSchemaFiles(unittest.TestCase):
    def test_all_schema_files_parse_and_declare_required(self):
        for name in SCHEMA_NAMES:
            s = load_schema(name)
            self.assertEqual(s["type"], "object", name)
            self.assertTrue(required(name) <= whitelist(name), f"{name}: required ⊄ properties")

    def test_capture_session_whitelist_matches_adr(self):
        self.assertEqual(
            whitelist("capture_session"),
            {
                "schema_version", "user_id", "device_id", "session_id", "donning_id", "gesture_label",
                "obs_ts_device_ms", "obs_ts_host_ms", "fs_hz", "window_ms", "payload_kind",
                "raw_window", "feature_window", "quality", "context", "held_out", "export_flags", "source",
            },
        )
        self.assertEqual(
            set(load_schema("capture_session")["properties"]["gesture_label"]["enum"]),
            set(capture_session.VALID_GESTURES),
        )
        self.assertFalse(load_schema("capture_session")["additionalProperties"])

    def test_cloud_safe_schema_forbids_raw_structurally(self):
        s = load_schema("cloud_safe_event")
        self.assertFalse(s["additionalProperties"])
        for f in ("raw_window", "raw_adc", "raw_uV", "raw_imu"):
            self.assertNotIn(f, s["properties"])
            self.assertIn(f, cloud_safe_event.FORBIDDEN_FIELDS)

    def test_python_constants_derive_from_json(self):
        self.assertEqual(capture_session.REQUIRED_FIELDS, required("capture_session"))
        self.assertEqual(calibration_profile.FIELD_WHITELIST, whitelist("calibration_profile"))
        self.assertEqual(cloud_safe_event.FIELD_WHITELIST, whitelist("cloud_safe_event"))


class TestPythonValidatorsEnforceWhitelist(unittest.TestCase):
    def test_capture_session_rejects_unknown_field(self):
        s = _sample_session()
        s["free_text"] = "squeeze harder"
        with self.assertRaises(CaptureSessionError):
            validate_capture_session(s)

    def test_capture_session_rejects_unknown_quality_flag(self):
        s = _sample_session()
        s["quality"]["wet"] = True
        with self.assertRaises(CaptureSessionError):
            validate_capture_session(s)

    def test_capture_session_rejects_bad_payload_kind_and_empty_ids(self):
        s = _sample_session()
        s["payload_kind"] = "video"
        with self.assertRaises(CaptureSessionError):
            validate_capture_session(s)
        with self.assertRaises(CaptureSessionError):
            _sample_session(donning_id="")

    def test_calibration_profile_rejects_legacy_shape(self):
        legacy = {"schema_version": "1.0.0", "chain_version": "1.0.0", "TH_LOOSE_MAX": 0.1, "TH_HARD_MIN": 0.4}
        with self.assertRaises(CalibrationProfileError):
            validate_calibration_profile(legacy)
        p = create_calibration_profile("u", "d", 0.1, 0.4)
        p["personalization_adapter"] = "p3.bin"  # P3 field must not sneak in
        with self.assertRaises(CalibrationProfileError):
            validate_calibration_profile(p)

    def test_cloud_safe_rejects_unknown_and_bad_quality(self):
        e = create_cloud_safe_event("pass", "ok", 1.0, band=1)
        e["feature_window"] = {"norm": 0.5}
        with self.assertRaises(CloudSafeEventError):
            validate_cloud_safe_event(e)
        with self.assertRaises(CloudSafeEventError):
            create_cloud_safe_event("pass", "wet", 1.0)


@unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema not installed (optional)")
class TestAgainstJsonSchemaLibrary(unittest.TestCase):
    def test_samples_validate_with_jsonschema(self):
        jsonschema.validate(_sample_session(), load_schema("capture_session"))
        jsonschema.validate(create_calibration_profile("u", "d", 0.1, 0.4), load_schema("calibration_profile"))
        jsonschema.validate(create_cloud_safe_event("pass", "ok", 1.0, band=1), load_schema("cloud_safe_event"))
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate({**create_cloud_safe_event("pass", "ok", 1.0), "raw_uV": [1]}, load_schema("cloud_safe_event"))
        bad = _sample_session(gesture_label="lead_off_neg", quality={"lead_off": True, "poor_contact": False, "line_noise": False, "clip": False, "artifact_suspect": False})
        bad["gesture_label"] = "light"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(bad, load_schema("capture_session"))


if __name__ == "__main__":
    unittest.main()
