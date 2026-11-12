"""Late fusion of one XIAO IMU motion with one EMG effort band.

Effort comes from the existing RMS gate (band 0/1/2). IMU features never
enter that number. A paired window keeps the two labels apart: there is
no single gesture_label, and force-calibration labels cannot be renamed
into the five-class gesture set.

This module does not train, upload, or flash.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from . import SCHEMA_VERSION
from .capture_session import VALID_GESTURES
from .quality import (
    QUALITY_ARTIFACT,
    QUALITY_CLIP,
    QUALITY_LEAD_OFF,
    QUALITY_LINE_NOISE,
    QUALITY_OK,
    QUALITY_POOR_CONTACT,
    SUPPRESS_GREEN,
)
from .schemas import load_schema, required, whitelist

_SCHEMA = "paired_window"

IMU_FS_HZ = 52.0
IMU_WINDOW_MS = 2000.0
IMU_FEATURES = 12
EMG_WINDOW_MS = 200.0
EMG_HOP_MS = 50.0
MIN_IMU_SESSIONS = 2
MIN_IMU_TEST = 10

STILL = "still"
DAILY = "daily"
OTHER = "other"
NAMED_MOTIONS = frozenset({"circle", "up_wave", "punch", "hook", "uppercut"})
PUNCH_FAMILY = frozenset({"punch", "hook", "uppercut"})
MOTIONS = tuple(load_schema(_SCHEMA)["$defs"]["imu"]["properties"]["motion"]["enum"])

VERDICT_SUPPRESSED = "suppressed"
VERDICT_WITHHELD = "withheld"
VERDICT_REST = "rest"
VERDICT_MOTION_WITHOUT_EFFORT = "motion_without_effort"
VERDICT_ISOMETRIC = "isometric"
VERDICT_FORCEFUL = "forceful_motion"
VERDICT_DAILY_EFFORT = "daily_with_effort"
VERDICTS = (
    VERDICT_SUPPRESSED,
    VERDICT_WITHHELD,
    VERDICT_REST,
    VERDICT_MOTION_WITHOUT_EFFORT,
    VERDICT_ISOMETRIC,
    VERDICT_FORCEFUL,
    VERDICT_DAILY_EFFORT,
)
FORCE_VERDICTS = frozenset({VERDICT_ISOMETRIC, VERDICT_FORCEFUL, VERDICT_DAILY_EFFORT})

FIVE_CLASS = ("relax", "pinch", "rub", "snap", "fist")
FIVE_CLASS_CN = {
    "relax": "放松",
    "pinch": "捏合",
    "rub": "搓动",
    "snap": "响指",
    "fist": "握拳",
}

QUALITIES = frozenset({
    QUALITY_OK,
    QUALITY_LEAD_OFF,
    QUALITY_POOR_CONTACT,
    QUALITY_LINE_NOISE,
    QUALITY_CLIP,
    QUALITY_ARTIFACT,
})

_SUMMARY = {
    VERDICT_SUPPRESSED: "这一窗不报力量",
    VERDICT_WITHHELD: "肌电到了用力档，但没有放行",
    VERDICT_REST: "静止，肌电在休息档",
    VERDICT_MOTION_WITHOUT_EFFORT: "手腕在动，肌电在休息档",
    VERDICT_ISOMETRIC: "手腕静止，肌电在用力档",
    VERDICT_FORCEFUL: "手腕动作与肌电用力同时成立",
    VERDICT_DAILY_EFFORT: "日常动作期间肌电在用力档",
}

_EFFORT = {1: "light", 2: "hard"}
_SUPPRESS_PRIORITY = (QUALITY_CLIP, QUALITY_LEAD_OFF, QUALITY_POOR_CONTACT)


class FusionError(Exception):
    """Paired-window or fusion input is not usable."""


def _coverage() -> None:
    covered = set(NAMED_MOTIONS) | {STILL, DAILY}
    if covered != set(MOTIONS):
        raise FusionError(
            f"motion groups drifted from schema enum: schema={list(MOTIONS)} groups={sorted(covered)}"
        )


_coverage()


def _motion(motion: str) -> str:
    if motion not in MOTIONS:
        raise FusionError(f"Invalid motion: {motion}. Must be one of {list(MOTIONS)}")
    return motion


def _band(band: object) -> int:
    if isinstance(band, bool) or not isinstance(band, int) or band not in (0, 1, 2):
        raise FusionError("band must be 0, 1, or 2")
    return band


def _quality(quality: str) -> str:
    if quality not in QUALITIES:
        raise FusionError(f"Invalid quality: {quality}")
    return quality


def _flag(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise FusionError(f"{name} must be a boolean")
    return value


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FusionError(f"{name} must be a number")
    out = float(value)
    if not math.isfinite(out):
        raise FusionError(f"{name} must be finite")
    return out


def _positive(value: object, name: str) -> float:
    out = _number(value, name)
    if out <= 0:
        raise FusionError(f"{name} must be positive")
    return out


def _close(value: float, target: float) -> bool:
    return abs(value - target) <= 1e-6


def export_label(motion: str, *, merge_punch_family: bool = False) -> str:
    """IMU training label. still/daily collapse to other. Punch family stays split unless asked."""
    motion = _motion(motion)
    if motion in (STILL, DAILY):
        return OTHER
    if merge_punch_family and motion in PUNCH_FAMILY:
        return "punch"
    return motion


def _result(
    *,
    verdict: str,
    motion: str,
    band: int,
    band_in: int,
    quality: str,
    authorize_in: bool,
    report_force: bool,
    effort: Optional[str],
) -> Dict[str, Any]:
    if verdict not in VERDICTS:
        raise FusionError(f"unhandled verdict: {verdict}")
    if report_force != (verdict in FORCE_VERDICTS):
        raise FusionError(f"report_force does not match verdict {verdict}")
    if report_force and effort not in ("light", "hard"):
        raise FusionError("force verdict needs effort light or hard")
    if not report_force and effort is not None:
        raise FusionError("non-force verdict cannot carry effort")
    return {
        "verdict": verdict,
        "summary": _SUMMARY[verdict],
        "motion": motion,
        "train_label": export_label(motion),
        "band": band,
        "band_in": band_in,
        "effort": effort,
        "quality": quality,
        "authorize_in": authorize_in,
        "report_force": report_force,
        "envelope": "rms",
    }


def fuse(motion: str, band: int, quality: str, authorize: bool) -> Dict[str, Any]:
    """Combine one motion with one RMS gate output. IMU magnitude is not an argument."""
    motion = _motion(motion)
    band_in = _band(band)
    quality = _quality(quality)
    authorize_in = _flag(authorize, "authorize")

    if quality in SUPPRESS_GREEN:
        return _result(
            verdict=VERDICT_SUPPRESSED,
            motion=motion,
            band=0,
            band_in=band_in,
            quality=quality,
            authorize_in=authorize_in,
            report_force=False,
            effort=None,
        )

    if quality == QUALITY_LINE_NOISE and (band_in >= 1 or authorize_in):
        return _result(
            verdict=VERDICT_WITHHELD,
            motion=motion,
            band=band_in,
            band_in=band_in,
            quality=quality,
            authorize_in=authorize_in,
            report_force=False,
            effort=None,
        )

    if band_in == 0:
        verdict = VERDICT_REST if motion == STILL else VERDICT_MOTION_WITHOUT_EFFORT
        return _result(
            verdict=verdict,
            motion=motion,
            band=0,
            band_in=band_in,
            quality=quality,
            authorize_in=authorize_in,
            report_force=False,
            effort=None,
        )

    if not authorize_in:
        return _result(
            verdict=VERDICT_WITHHELD,
            motion=motion,
            band=band_in,
            band_in=band_in,
            quality=quality,
            authorize_in=authorize_in,
            report_force=False,
            effort=None,
        )

    if motion == STILL:
        verdict = VERDICT_ISOMETRIC
    elif motion == DAILY:
        verdict = VERDICT_DAILY_EFFORT
    elif motion in NAMED_MOTIONS:
        verdict = VERDICT_FORCEFUL
    else:
        raise FusionError(f"unhandled motion: {motion}")

    return _result(
        verdict=verdict,
        motion=motion,
        band=band_in,
        band_in=band_in,
        quality=quality,
        authorize_in=authorize_in,
        report_force=True,
        effort=_EFFORT[band_in],
    )


def decision_grid() -> List[Dict[str, Any]]:
    """Every motion × band × quality × authorize. Used to lock the table."""
    rows = []
    for motion in MOTIONS:
        for band in (0, 1, 2):
            for quality in sorted(QUALITIES):
                for authorize in (False, True):
                    rows.append(fuse(motion, band, quality, authorize))
    return rows


def _parse_hop(hop: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(hop, Mapping):
        raise FusionError("EMG hop must be an object")
    envelope = hop.get("envelope", "rms")
    if envelope != "rms":
        raise FusionError("force uses the RMS envelope")
    norm = None if "norm" not in hop or hop["norm"] is None else _number(hop["norm"], "norm")
    return {
        "t_host_ms": _number(hop["t_host_ms"], "t_host_ms"),
        "band": _band(hop["band"]),
        "quality": _quality(hop["quality"]),
        "authorize": _flag(hop["authorize"], "authorize"),
        "norm": norm,
    }


def _worst_suppress(hops: Sequence[Mapping[str, Any]]) -> str:
    present = {hop["quality"] for hop in hops}
    for quality in _SUPPRESS_PRIORITY:
        if quality in present:
            return quality
    raise FusionError("no suppress quality in window")


def summarize_emg_hops(hops: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Peak authorized RMS band inside one IMU window.

    Any lead_off / poor_contact / clip hop blocks force for the whole window.
    """
    parsed = [_parse_hop(hop) for hop in hops]
    if not parsed:
        raise FusionError("no EMG hop")
    blocked = [hop for hop in parsed if hop["quality"] in SUPPRESS_GREEN]
    if blocked:
        peak = max(parsed, key=lambda hop: (hop["band"], _norm_key(hop), -hop["t_host_ms"]))
        return {
            "band": peak["band"],
            "quality": _worst_suppress(blocked),
            "authorize": False,
            "norm": peak["norm"],
        }
    authorized = [
        hop for hop in parsed
        if hop["authorize"] and hop["band"] >= 1 and hop["quality"] != QUALITY_LINE_NOISE
    ]
    if authorized:
        peak = max(authorized, key=lambda hop: (hop["band"], _norm_key(hop), -hop["t_host_ms"]))
        return {
            "band": peak["band"],
            "quality": peak["quality"],
            "authorize": True,
            "norm": peak["norm"],
        }
    raised = [hop for hop in parsed if hop["band"] >= 1]
    if raised:
        peak = max(raised, key=lambda hop: (hop["band"], _norm_key(hop), -hop["t_host_ms"]))
        return {
            "band": peak["band"],
            "quality": peak["quality"],
            "authorize": False,
            "norm": peak["norm"],
        }
    ok = [hop for hop in parsed if hop["quality"] == QUALITY_OK]
    chosen = ok[0] if ok else parsed[0]
    return {"band": 0, "quality": chosen["quality"], "authorize": False, "norm": chosen["norm"]}


def _norm_key(hop: Mapping[str, Any]) -> float:
    norm = hop["norm"]
    return -1.0 if norm is None else float(norm)


def fuse_imu_window(
    motion: str,
    t0_ms: float,
    window_ms: float,
    hops: Sequence[Mapping[str, Any]],
    *,
    fs_hz: Optional[float] = None,
) -> Dict[str, Any]:
    """Fuse the EMG hops whose centers fall inside [t0, t0 + window]."""
    start = _number(t0_ms, "t_host_ms")
    width = _positive(window_ms, "window_ms")
    rate = None if fs_hz is None else _positive(fs_hz, "fs_hz")
    inside = []
    for hop in hops:
        parsed = _parse_hop(hop)
        if start <= parsed["t_host_ms"] <= start + width:
            inside.append(hop)
    if not inside:
        raise FusionError("no EMG hop inside the IMU window")
    summary = summarize_emg_hops(inside)
    decision = fuse(motion, summary["band"], summary["quality"], summary["authorize"])
    decision["norm"] = summary["norm"]
    decision["emg_hops"] = len(inside)
    decision["t_host_ms"] = start
    decision["window_ms"] = width
    decision["profile_match"] = rate is not None and _close(rate, IMU_FS_HZ) and _close(width, IMU_WINDOW_MS)
    return decision


def _features(values: object) -> None:
    if not isinstance(values, list) or len(values) != IMU_FEATURES:
        raise FusionError(f"IMU features must be {IMU_FEATURES} finite numbers")
    for value in values:
        _number(value, "features")


def validate_paired_window(record: Dict[str, Any]) -> None:
    """Validate one paired window. Rejects a single gesture_label and a non-RMS envelope."""
    if not isinstance(record, dict):
        raise FusionError("PairedWindow must be an object")
    if "gesture_label" in record:
        raise FusionError("PairedWindow cannot carry a single gesture_label")
    missing = sorted(required(_SCHEMA) - record.keys())
    if missing:
        raise FusionError(f"Missing required field: {missing[0]}")
    unknown = sorted(record.keys() - whitelist(_SCHEMA))
    if unknown:
        raise FusionError(f"Field not in whitelist: {unknown}")
    if not isinstance(record["donning_id"], str) or not record["donning_id"]:
        raise FusionError("donning_id must be a non-empty string")
    if record["schema_version"] != SCHEMA_VERSION:
        raise FusionError(f"schema_version must be {SCHEMA_VERSION}")
    _number(record["t_host_ms"], "t_host_ms")
    _validate_imu(record["imu"])
    _validate_emg(record["emg"])


def _object(value: object, name: str, allowed: Iterable[str], required_keys: Iterable[str]) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise FusionError(f"{name} must be an object")
    allowed_set = set(allowed)
    unknown = sorted(value.keys() - allowed_set)
    if unknown:
        raise FusionError(f"Field not in {name} whitelist: {unknown}")
    missing = sorted(set(required_keys) - value.keys())
    if missing:
        raise FusionError(f"{name} missing required field: {missing[0]}")
    return value


def _validate_imu(imu: object) -> None:
    schema = load_schema(_SCHEMA)["$defs"]["imu"]
    body = _object(imu, "imu", schema["properties"], schema["required"])
    _motion(body["motion"])
    _positive(body["fs_hz"], "fs_hz")
    _positive(body["window_ms"], "window_ms")
    if "features" in body:
        _features(body["features"])


def _validate_emg(emg: object) -> None:
    schema = load_schema(_SCHEMA)["$defs"]["emg"]
    body = _object(emg, "emg", schema["properties"], schema["required"])
    if body["envelope"] != "rms":
        raise FusionError("force uses the RMS envelope")
    _band(body["band"])
    _quality(body["quality"])
    _flag(body["authorize"], "authorize")
    _positive(body["window_ms"], "window_ms")
    _positive(body["hop_ms"], "hop_ms")
    if "norm" in body:
        _number(body["norm"], "norm")


def fuse_pair(record: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a paired window, then fuse. Features are checked and then ignored."""
    validate_paired_window(record)
    imu = record["imu"]
    emg = record["emg"]
    decision = fuse(imu["motion"], emg["band"], emg["quality"], emg["authorize"])
    decision["donning_id"] = record["donning_id"]
    decision["t_host_ms"] = _number(record["t_host_ms"], "t_host_ms")
    decision["norm"] = emg.get("norm")
    decision["profile_match"] = (
        _close(_positive(imu["fs_hz"], "fs_hz"), IMU_FS_HZ)
        and _close(_positive(imu["window_ms"], "window_ms"), IMU_WINDOW_MS)
        and _close(_positive(emg["window_ms"], "window_ms"), EMG_WINDOW_MS)
        and _close(_positive(emg["hop_ms"], "hop_ms"), EMG_HOP_MS)
    )
    return decision


def _thin(counts: Mapping[str, object], labels: Sequence[str], minimum: int) -> List[str]:
    thin = []
    for label in labels:
        value = counts.get(label, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise FusionError(f"count for {label} must be a non-negative integer")
        if value < minimum:
            thin.append(label)
    return thin


def imu_train_ready(sessions_per_label: Mapping[str, object], labels: Sequence[str]) -> Dict[str, Any]:
    """Session-grouped training needs two sessions in every class that will be fit."""
    label_list = tuple(labels)
    if not label_list:
        return {"ready": False, "thin": [], "min_sessions": MIN_IMU_SESSIONS, "why": "no labels"}
    thin = _thin(sessions_per_label, label_list, MIN_IMU_SESSIONS)
    why = "" if not thin else "need at least 2 sessions per class: " + ", ".join(thin)
    return {"ready": not thin, "thin": thin, "min_sessions": MIN_IMU_SESSIONS, "why": why}


def imu_test_ready(
    windows_per_label: Mapping[str, object],
    labels: Sequence[str],
    *,
    min_windows: int = MIN_IMU_TEST,
) -> Dict[str, Any]:
    """Accuracy stays unreported until every class has enough held-out windows."""
    if isinstance(min_windows, bool) or not isinstance(min_windows, int) or min_windows < 1:
        raise FusionError("min_windows must be a positive integer")
    label_list = tuple(labels)
    if not label_list:
        return {
            "report_accuracy": False,
            "thin": [],
            "min_windows": min_windows,
            "why": "no labels",
        }
    thin = _thin(windows_per_label, label_list, min_windows)
    why = "" if not thin else f"held-out under {min_windows} per class: " + ", ".join(thin)
    return {
        "report_accuracy": not thin,
        "thin": thin,
        "min_windows": min_windows,
        "why": why,
    }


def screen_five_class_label(label: str) -> str:
    """Five-class gestures are a new set. Force-calibration labels stay out."""
    if label in VALID_GESTURES:
        raise FusionError(
            f"{label} is a force-calibration label and cannot enter the five-class set"
        )
    if label not in FIVE_CLASS:
        raise FusionError(f"unknown five-class label: {label}")
    return label


def five_class_train_ready(counts_per_label: Mapping[str, object], *, min_count: int) -> Dict[str, Any]:
    if isinstance(min_count, bool) or not isinstance(min_count, int) or min_count < 1:
        raise FusionError("min_count must be a positive integer")
    leaks = sorted(label for label in counts_per_label if label in VALID_GESTURES)
    foreign = sorted(
        label for label in counts_per_label if label not in FIVE_CLASS and label not in VALID_GESTURES
    )
    thin = _thin(counts_per_label, FIVE_CLASS, min_count)
    ready = not leaks and not foreign and not thin
    why = ""
    if leaks:
        why = "force labels in the five-class counts: " + ", ".join(leaks)
    elif foreign:
        why = "labels outside the five-class set: " + ", ".join(foreign)
    elif thin:
        why = "five-class short: " + ", ".join(thin)
    return {
        "ready": ready,
        "leaks": leaks,
        "foreign": foreign,
        "thin": thin,
        "min_count": min_count,
        "why": why,
    }


def sample_paired_window(**over: Any) -> Dict[str, Any]:
    """One valid paired window. Overrides are shallow except imu/emg, which merge."""
    record: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "donning_id": "don_emg",
        "t_host_ms": 1000.0,
        "imu": {"motion": "punch", "fs_hz": IMU_FS_HZ, "window_ms": IMU_WINDOW_MS},
        "emg": {
            "envelope": "rms",
            "band": 2,
            "quality": QUALITY_OK,
            "authorize": True,
            "norm": 0.62,
            "window_ms": EMG_WINDOW_MS,
            "hop_ms": EMG_HOP_MS,
        },
    }
    for key, value in over.items():
        if key in ("imu", "emg") and isinstance(value, dict):
            merged = dict(record[key])
            merged.update(value)
            record[key] = merged
        else:
            record[key] = value
    return record
