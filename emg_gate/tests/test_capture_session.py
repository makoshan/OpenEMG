"""Test CaptureSession schema and validation."""

import unittest

from emg_gate.capture_session import (
    GESTURE_HARD,
    GESTURE_LEAD_OFF_NEG,
    GESTURE_LIGHT,
    GESTURE_REST,
    SOURCE_RECORDED,
    SOURCE_SYNTHETIC,
    CaptureSessionError,
    create_capture_session,
    strip_raw_from_session,
    validate_capture_session,
)


class TestCaptureSession(unittest.TestCase):
    def test_create_valid_session(self):
        """Test creating a valid capture session."""
        session = create_capture_session(
            user_id="user_test",
            device_id="ads1292_001",
            session_id="sess_001",
            donning_id="don_001",
            gesture_label=GESTURE_REST,
            feature_window={"band": 0, "norm": 0.08},
        )
        self.assertEqual(session["user_id"], "user_test")
        self.assertEqual(session["gesture_label"], GESTURE_REST)
        self.assertIn("quality", session)
        self.assertFalse(session["held_out"])

    def test_missing_required_field(self):
        """Test that missing required field raises error."""
        session = {
            "schema_version": "1.0.0",
            "user_id": "test",
            "device_id": "dev_001",
        }
        with self.assertRaises(CaptureSessionError):
            validate_capture_session(session)

    def test_invalid_gesture(self):
        """Test that invalid gesture label raises error."""
        with self.assertRaises(CaptureSessionError):
            create_capture_session(
                user_id="user_test",
                device_id="ads1292_001",
                session_id="sess_001",
                donning_id="don_001",
                gesture_label="invalid_gesture",
            )

    def test_positive_gesture_with_lead_off_rejected(self):
        """Test that positive gesture with lead_off=true is rejected."""
        session = create_capture_session(
            user_id="user_test",
            device_id="ads1292_001",
            session_id="sess_001",
            donning_id="don_001",
            gesture_label=GESTURE_LIGHT,
        )
        session["quality"]["lead_off"] = True
        with self.assertRaises(CaptureSessionError):
            validate_capture_session(session)

    def test_positive_gesture_with_clip_rejected(self):
        """Test that positive gesture with clip=true is rejected."""
        session = create_capture_session(
            user_id="user_test",
            device_id="ads1292_001",
            session_id="sess_001",
            donning_id="don_001",
            gesture_label=GESTURE_HARD,
        )
        session["quality"]["clip"] = True
        with self.assertRaises(CaptureSessionError):
            validate_capture_session(session)

    def test_negative_gesture_allowed_with_lead_off(self):
        """Test that negative gesture can have lead_off=true."""
        session = create_capture_session(
            user_id="user_test",
            device_id="ads1292_001",
            session_id="sess_001",
            donning_id="don_001",
            gesture_label=GESTURE_LEAD_OFF_NEG,
            quality={
                "lead_off": True,
                "poor_contact": False,
                "line_noise": False,
                "clip": False,
                "artifact_suspect": False,
            },
        )
        validate_capture_session(session)

    def test_strip_raw(self):
        """Test stripping raw_window from session."""
        session = create_capture_session(
            user_id="user_test",
            device_id="ads1292_001",
            session_id="sess_001",
            donning_id="don_001",
            gesture_label=GESTURE_REST,
            raw_window=[1.0, 2.0, 3.0],
        )
        self.assertIn("raw_window", session)

        stripped = strip_raw_from_session(session)
        self.assertNotIn("raw_window", stripped)
        self.assertEqual(stripped["user_id"], "user_test")

    def test_held_out_flag(self):
        """Test held_out flag."""
        session = create_capture_session(
            user_id="user_test",
            device_id="ads1292_001",
            session_id="sess_001",
            donning_id="don_001",
            gesture_label=GESTURE_REST,
            held_out=True,
        )
        self.assertTrue(session["held_out"])

    def test_source_recorded_default(self):
        """Test that source defaults to recorded."""
        session = create_capture_session(
            user_id="user_test",
            device_id="ads1292_001",
            session_id="sess_001",
            donning_id="don_001",
            gesture_label=GESTURE_REST,
        )
        self.assertEqual(session["source"], SOURCE_RECORDED)

    def test_source_synthetic(self):
        """Test that source can be set to synthetic."""
        session = create_capture_session(
            user_id="user_test",
            device_id="ads1292_001",
            session_id="sess_001",
            donning_id="don_001",
            gesture_label=GESTURE_REST,
            source=SOURCE_SYNTHETIC,
        )
        self.assertEqual(session["source"], SOURCE_SYNTHETIC)

    def test_invalid_source_rejected(self):
        """Test that invalid source value raises error."""
        session = create_capture_session(
            user_id="user_test",
            device_id="ads1292_001",
            session_id="sess_001",
            donning_id="don_001",
            gesture_label=GESTURE_REST,
        )
        session["source"] = "demo"
        with self.assertRaises(CaptureSessionError) as ctx:
            validate_capture_session(session)
        self.assertIn("Invalid source", str(ctx.exception))

    def test_missing_source_backward_compatible(self):
        """Test that missing source field is accepted (backward compatibility)."""
        session = create_capture_session(
            user_id="user_test",
            device_id="ads1292_001",
            session_id="sess_001",
            donning_id="don_001",
            gesture_label=GESTURE_REST,
        )
        del session["source"]
        validate_capture_session(session)


if __name__ == "__main__":
    unittest.main()
