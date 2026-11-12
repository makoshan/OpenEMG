"""CloudSafeEvent schema: REJECTS raw fields.

ADR sync contract: only events + band + quality + summary to cloud.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from . import SCHEMA_VERSION
from .schemas import load_schema, required, whitelist

_SCHEMA = "cloud_safe_event"
FIELD_WHITELIST = whitelist(_SCHEMA)
REQUIRED_FIELDS = required(_SCHEMA)
QUALITY_ENUM = frozenset(load_schema(_SCHEMA)["properties"]["quality"]["enum"])
FORBIDDEN_FIELDS = frozenset(
    field
    for clause in load_schema(_SCHEMA)["not"]["anyOf"]
    for field in clause["required"]
)


class CloudSafeEventError(Exception):
    """CloudSafeEvent validation error."""


def validate_cloud_safe_event(event: Dict[str, Any]) -> None:
    """Validate CloudSafeEvent. Raises CloudSafeEventError on raw or unknown fields.

    Raw is rejected twice on purpose: by the explicit forbidden list (clear
    error message) and by the whitelist (additionalProperties=false).
    """
    if not isinstance(event, dict):
        raise CloudSafeEventError("CloudSafeEvent must be an object")

    for forbidden in sorted(FORBIDDEN_FIELDS):
        if forbidden in event:
            raise CloudSafeEventError(
                f"CloudSafeEvent must NOT contain {forbidden}. Privacy violation."
            )

    unknown = sorted(event.keys() - FIELD_WHITELIST)
    if unknown:
        raise CloudSafeEventError(f"Field not in CloudSafeEvent whitelist: {unknown}")

    missing = sorted(REQUIRED_FIELDS - event.keys())
    if missing:
        raise CloudSafeEventError(f"Missing required field: {missing[0]}")

    if event["quality"] not in QUALITY_ENUM:
        raise CloudSafeEventError(f"Invalid quality: {event['quality']}")
    if "band" in event and event["band"] not in (0, 1, 2):
        raise CloudSafeEventError(f"Invalid band: {event['band']}")


def create_cloud_safe_event(
    kind: str,
    quality: str,
    t_host_ms: float,
    *,
    band: Optional[int] = None,
    confidence: Optional[float] = None,
    summary: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a CloudSafeEvent (no raw, ready for upload)."""
    event: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": kind,
        "quality": quality,
        "t_host_ms": t_host_ms,
    }

    if band is not None:
        event["band"] = band
    if confidence is not None:
        event["confidence"] = confidence
    if summary is not None:
        event["summary"] = summary

    validate_cloud_safe_event(event)
    return event


def gate_event_to_cloud_safe(gate_event: Dict[str, Any]) -> Dict[str, Any]:
    """Convert gate event to CloudSafeEvent (strip raw, keep band/quality)."""
    kind_map = {
        0: "rest",
        1: "light_effort",
        2: "hard_effort",
    }
    band = gate_event.get("band", 0)
    kind = kind_map.get(band, "band_change")

    if gate_event.get("event_suppressed"):
        kind = "suppressed_" + kind

    event = create_cloud_safe_event(
        kind=kind,
        quality=gate_event.get("quality", "ok"),
        t_host_ms=gate_event.get("t_host_ms", 0.0),
        band=band,
        confidence=gate_event.get("confidence"),
    )

    return event
