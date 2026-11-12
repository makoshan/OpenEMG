"""P1 CalibrationProfile schema and validation.

Local self-calibration thresholds. NOT P3 (P3 is fine-tune weights).
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from . import CHAIN_VERSION, SCHEMA_VERSION
from .schemas import required, whitelist

_SCHEMA = "calibration_profile"
FIELD_WHITELIST = whitelist(_SCHEMA)
REQUIRED_FIELDS = required(_SCHEMA)


class CalibrationProfileError(Exception):
    """CalibrationProfile validation error."""


def validate_calibration_profile(profile: Dict[str, Any]) -> None:
    """Validate P1 CalibrationProfile. Raises CalibrationProfileError if invalid."""
    if not isinstance(profile, dict):
        raise CalibrationProfileError("CalibrationProfile must be an object")

    missing = sorted(REQUIRED_FIELDS - profile.keys())
    if missing:
        raise CalibrationProfileError(f"Missing required field: {missing[0]}")

    unknown = sorted(profile.keys() - FIELD_WHITELIST)
    if unknown:
        raise CalibrationProfileError(f"Field not in whitelist: {unknown}")

    thresholds = profile["thresholds"]
    if not isinstance(thresholds, dict):
        raise CalibrationProfileError("thresholds must be a dict")

    if "th_loose_max" not in thresholds or "th_hard_min" not in thresholds:
        raise CalibrationProfileError(
            "thresholds must contain th_loose_max and th_hard_min"
        )

    th_loose = thresholds["th_loose_max"]
    th_hard = thresholds["th_hard_min"]
    if not (0.0 <= th_loose < th_hard <= 1.0):
        raise CalibrationProfileError(
            f"Invalid thresholds: 0 <= th_loose_max ({th_loose}) < th_hard_min ({th_hard}) <= 1"
        )


def create_calibration_profile(
    user_id: str,
    device_id: str,
    th_loose_max: float,
    th_hard_min: float,
    *,
    donning_id: Optional[str] = None,
    created_at: Optional[str] = None,
    stale: bool = False,
    prev_profile_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a P1 CalibrationProfile dict."""
    if created_at is None:
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    profile: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "user_id": user_id,
        "device_id": device_id,
        "chain_ver": CHAIN_VERSION,
        "thresholds": {
            "th_loose_max": th_loose_max,
            "th_hard_min": th_hard_min,
        },
        "created_at": created_at,
        "stale": stale,
    }

    if donning_id is not None:
        profile["donning_id"] = donning_id
    if prev_profile_ref is not None:
        profile["prev_profile_ref"] = prev_profile_ref

    validate_calibration_profile(profile)
    return profile
