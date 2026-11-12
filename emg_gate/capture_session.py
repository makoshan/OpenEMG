"""P0 CaptureSession schema and validation.

ADR §1: whitelist fields, closed gesture enum, reject rules.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from . import SCHEMA_VERSION
from .schemas import load_schema, required, whitelist

_SCHEMA = "capture_session"
FIELD_WHITELIST = whitelist(_SCHEMA)
REQUIRED_FIELDS = required(_SCHEMA)
QUALITY_WHITELIST = frozenset(load_schema(_SCHEMA)["properties"]["quality"]["properties"])
QUALITY_REQUIRED = frozenset(load_schema(_SCHEMA)["properties"]["quality"]["required"])
PAYLOAD_KINDS = frozenset(load_schema(_SCHEMA)["properties"]["payload_kind"]["enum"])


GESTURE_REST = "rest"
GESTURE_LIGHT = "light"
GESTURE_HARD = "hard"
GESTURE_LEAD_OFF_NEG = "lead_off_neg"
GESTURE_CONFIRM_PULSE = "confirm_pulse"

VALID_GESTURES = frozenset({
    GESTURE_REST,
    GESTURE_LIGHT,
    GESTURE_HARD,
    GESTURE_LEAD_OFF_NEG,
    GESTURE_CONFIRM_PULSE,
})

POSITIVE_GESTURES = frozenset({GESTURE_REST, GESTURE_LIGHT, GESTURE_HARD, GESTURE_CONFIRM_PULSE})

SOURCE_RECORDED = "recorded"
SOURCE_SYNTHETIC = "synthetic"
VALID_SOURCES = frozenset({SOURCE_RECORDED, SOURCE_SYNTHETIC})


class CaptureSessionError(Exception):
    """CaptureSession validation error."""


def validate_capture_session(session: Dict[str, Any]) -> None:
    """Validate P0 CaptureSession. Raises CaptureSessionError if invalid.

    Mirrors schemas/capture_session.schema.json: required set, field
    whitelist (additionalProperties=false), closed gesture enum, and the
    positive-gesture reject rule.
    """
    if not isinstance(session, dict):
        raise CaptureSessionError("CaptureSession must be an object")

    missing = sorted(REQUIRED_FIELDS - session.keys())
    if missing:
        raise CaptureSessionError(f"Missing required field: {missing[0]}")

    unknown = sorted(session.keys() - FIELD_WHITELIST)
    if unknown:
        raise CaptureSessionError(f"Field not in whitelist: {unknown}")

    for sid_field in ("session_id", "donning_id", "user_id", "device_id"):
        if not isinstance(session[sid_field], str) or not session[sid_field]:
            raise CaptureSessionError(f"{sid_field} must be a non-empty string")

    for ts_field in ("obs_ts_device_ms", "obs_ts_host_ms"):
        if isinstance(session[ts_field], bool) or not isinstance(
            session[ts_field], (int, float)
        ):
            raise CaptureSessionError(f"{ts_field} must be a number")

    if session["payload_kind"] not in PAYLOAD_KINDS:
        raise CaptureSessionError(
            f"Invalid payload_kind: {session['payload_kind']}. Must be one of {sorted(PAYLOAD_KINDS)}"
        )

    gesture = session["gesture_label"]
    if gesture not in VALID_GESTURES:
        raise CaptureSessionError(
            f"Invalid gesture_label: {gesture}. Must be one of {sorted(VALID_GESTURES)}"
        )

    if "source" in session:
        source = session["source"]
        if source not in VALID_SOURCES:
            raise CaptureSessionError(
                f"Invalid source: {source}. Must be one of {sorted(VALID_SOURCES)}"
            )

    quality = session["quality"]
    if not isinstance(quality, dict):
        raise CaptureSessionError("quality must be a dict")

    missing_q = sorted(QUALITY_REQUIRED - quality.keys())
    if missing_q:
        raise CaptureSessionError(f"Missing quality field: {missing_q[0]}")
    unknown_q = sorted(quality.keys() - QUALITY_WHITELIST)
    if unknown_q:
        raise CaptureSessionError(f"quality field not in whitelist: {unknown_q}")
    for qf in QUALITY_REQUIRED:
        if not isinstance(quality[qf], bool):
            raise CaptureSessionError(f"quality.{qf} must be boolean")

    if gesture in POSITIVE_GESTURES:
        if quality.get("lead_off") is True:
            raise CaptureSessionError(
                f"Positive gesture {gesture} must not have lead_off=true"
            )
        if quality.get("clip") is True:
            raise CaptureSessionError(
                f"Positive gesture {gesture} must not have clip=true"
            )


def create_capture_session(
    user_id: str,
    device_id: str,
    session_id: str,
    donning_id: str,
    gesture_label: str,
    *,
    obs_ts_device_ms: Optional[float] = None,
    obs_ts_host_ms: Optional[float] = None,
    fs_hz: float = 500.0,
    window_ms: float = 200.0,
    payload_kind: str = "feature_window",
    raw_window: Optional[List[float]] = None,
    feature_window: Optional[Dict[str, Any]] = None,
    quality: Optional[Dict[str, bool]] = None,
    context: Optional[Dict[str, Any]] = None,
    held_out: bool = False,
    export_flags: Optional[Dict[str, bool]] = None,
    source: str = SOURCE_RECORDED,
) -> Dict[str, Any]:
    """Create a P0 CaptureSession dict with defaults."""
    if obs_ts_host_ms is None:
        obs_ts_host_ms = time.time() * 1000.0
    if obs_ts_device_ms is None:
        obs_ts_device_ms = obs_ts_host_ms

    if quality is None:
        quality = {
            "lead_off": False,
            "poor_contact": False,
            "line_noise": False,
            "clip": False,
            "artifact_suspect": False,
        }

    session: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "user_id": user_id,
        "device_id": device_id,
        "session_id": session_id,
        "donning_id": donning_id,
        "gesture_label": gesture_label,
        "obs_ts_device_ms": obs_ts_device_ms,
        "obs_ts_host_ms": obs_ts_host_ms,
        "fs_hz": fs_hz,
        "window_ms": window_ms,
        "payload_kind": payload_kind,
        "quality": quality,
        "held_out": held_out,
        "source": source,
    }

    if raw_window is not None:
        session["raw_window"] = raw_window
    if feature_window is not None:
        session["feature_window"] = feature_window
    if context is not None:
        session["context"] = context
    if export_flags is not None:
        session["export_flags"] = export_flags
    else:
        session["export_flags"] = {"local_only": True}

    validate_capture_session(session)
    return session


def strip_raw_from_session(session: Dict[str, Any]) -> Dict[str, Any]:
    """Return session with raw_window removed (privacy default)."""
    out = dict(session)
    out.pop("raw_window", None)
    return out
