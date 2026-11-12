"""Self-calibration: relax/light/hard → local thresholds.

State machine: sample → validate negatives → commit local profile.
Held-out sessions are excluded from threshold fitting.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .calibration_profile import create_calibration_profile, validate_calibration_profile
from .capture_session import (
    GESTURE_HARD,
    GESTURE_LEAD_OFF_NEG,
    GESTURE_LIGHT,
    GESTURE_REST,
)
from .pipeline import run_pipeline
from .synth import generate


def _middle_norms(result: Dict[str, Any]) -> np.ndarray:
    """Extract middle norm values (skip edge transients)."""
    norms = np.array([e["norm"] for e in result["events"]], dtype=np.float64)
    if len(norms) >= 5:
        a = len(norms) // 5
        b = -len(norms) // 5 or None
        norms = norms[a:b]
    return norms


def calibrate_from_streams(
    relax_uV: np.ndarray,
    light_uV: np.ndarray,
    hard_uV: np.ndarray,
    *,
    user_id: str = "local_user",
    device_id: str = "local_device",
    donning_id: Optional[str] = None,
    fs: float = 500.0,
    window_ms: float = 200.0,
    hop_ms: float = 50.0,
    norm_scale_uV: float = 200.0,
    lead_off_uV: Optional[np.ndarray] = None,
    prev_profile_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute TH_LOOSE_MAX / TH_HARD_MIN from three effort streams.
    
    Recipe (ADR):
      TH_LOOSE_MAX ≈ p95(relax) + margin, below p10(light)
      TH_HARD_MIN  ≈ midpoint(p90(light), p10(hard)) or below p20(hard)
    
    Reject commit if lead_off yields authorize green (false positive).
    Returns CalibrationProfile schema (validates with validate_calibration_profile).
    """
    common = dict(
        fs=fs,
        window_ms=window_ms,
        hop_ms=hop_ms,
        norm_scale_uV=norm_scale_uV,
        th_loose_max=0.15,
        th_hard_min=0.40,
        notch_mode="auto",
    )

    r_relax = run_pipeline(relax_uV, forced_quality=None, **common)
    r_light = run_pipeline(light_uV, forced_quality=None, **common)
    r_hard = run_pipeline(hard_uV, forced_quality=None, **common)

    n_relax = _middle_norms(r_relax)
    n_light = _middle_norms(r_light)
    n_hard = _middle_norms(r_hard)

    p95_relax = float(np.percentile(n_relax, 95)) if len(n_relax) else 0.05
    p10_light = float(np.percentile(n_light, 10)) if len(n_light) else 0.2
    p90_light = float(np.percentile(n_light, 90)) if len(n_light) else 0.3
    p10_hard = float(np.percentile(n_hard, 10)) if len(n_hard) else 0.5

    th_loose = min(p95_relax + 0.03, 0.5 * (p95_relax + p10_light))
    th_loose = float(np.clip(th_loose, 0.05, 0.35))
    th_hard = float(np.clip(0.5 * (p90_light + p10_hard), th_loose + 0.08, 0.85))

    neg_ok = True
    neg_detail: Dict[str, Any] = {}
    if lead_off_uV is not None:
        r_lo = run_pipeline(
            lead_off_uV,
            forced_quality="lead_off",
            th_loose_max=th_loose,
            th_hard_min=th_hard,
            fs=fs,
            window_ms=window_ms,
            hop_ms=hop_ms,
            norm_scale_uV=norm_scale_uV,
        )
        auth = r_lo["summary"]["authorize_count"]
        maj = r_lo["summary"]["majority_band"]
        neg_ok = auth == 0 and (maj is None or maj == 0)
        neg_detail = {
            "authorize_count": auth,
            "majority_band": maj,
            "suppressed_count": r_lo["summary"]["suppressed_count"],
        }

    profile = create_calibration_profile(
        user_id=user_id,
        device_id=device_id,
        th_loose_max=th_loose,
        th_hard_min=th_hard,
        donning_id=donning_id,
        prev_profile_ref=prev_profile_ref,
        stale=False,
    )

    profile["calibration_debug"] = {
        "fs": fs,
        "window_ms": window_ms,
        "hop_ms": hop_ms,
        "envelope": "rms",
        "hpf_hz": 20.0,
        "notch_hz": 50.0,
        "notch_mode": "auto",
        "norm_scale_uV": norm_scale_uV,
        "enable_delta2": False,
        "p95_relax": p95_relax,
        "p10_light": p10_light,
        "p90_light": p90_light,
        "p10_hard": p10_hard,
        "negatives_ok": neg_ok,
        "negatives": neg_detail,
        "committed": bool(neg_ok),
        "notes": "Local self-calibration profile. Do not upload. Raw not stored.",
    }
    if not neg_ok:
        profile["calibration_debug"]["error"] = "lead_off false-green; refuse commit"

    return profile


def calibrate_synth_demo(
    out_path: Path,
    *,
    fs: float = 500.0,
    duration_s: float = 2.0,
    seed: int = 7,
    store_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Demo calibration using synthetic signals; commits via commit_profile.

    If a profile already exists at out_path it is archived into
    ``store_dir`` (default ``<out_path.parent>/profile_store``) and the new
    profile gets ``prev_profile_ref`` pointing at it, so rollback works.
    """
    relax, _ = generate("rest", fs=fs, duration_s=duration_s, seed=seed)
    light, _ = generate("light", fs=fs, duration_s=duration_s, seed=seed + 1)
    hard, _ = generate("hard", fs=fs, duration_s=duration_s, seed=seed + 2)
    lead, _ = generate("lead_off", fs=fs, duration_s=duration_s, seed=seed + 3)

    profile = calibrate_from_streams(
        relax, light, hard, fs=fs, lead_off_uV=lead,
        user_id="demo_user",
        device_id="demo_device",
    )

    out_path = Path(out_path)
    if store_dir is None:
        store_dir = out_path.parent / "profile_store"
    return commit_profile(profile, out_path, Path(store_dir))


def _profile_archive_name(profile: Dict[str, Any]) -> str:
    """Stable archive filename: created_at + content hash (no user data in name)."""
    stamp = str(profile.get("created_at", "")).replace(":", "").replace("-", "")
    digest = hashlib.sha256(
        json.dumps(profile, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:8]
    return f"profile_{stamp}_{digest}.json"


def commit_profile(
    profile: Dict[str, Any],
    active_path: Path,
    store_dir: Path,
) -> Dict[str, Any]:
    """Commit a profile as the active one.

    - Refuses to commit if ``calibration_debug.committed`` is False
      (lead_off false-green).
    - Archives the previously active profile into ``store_dir`` and sets
      ``prev_profile_ref`` on the new profile to that archive filename.
    - Validates against the CalibrationProfile schema before writing.
    """
    active_path = Path(active_path)
    store_dir = Path(store_dir)
    debug = profile.get("calibration_debug", {})
    if debug.get("committed") is False:
        raise CalibrationCommitError(
            debug.get("error", "calibration failed negatives; refuse commit")
        )

    if active_path.exists():
        previous = json.loads(active_path.read_text(encoding="utf-8"))
        store_dir.mkdir(parents=True, exist_ok=True)
        archive_name = _profile_archive_name(previous)
        (store_dir / archive_name).write_text(
            json.dumps(previous, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        profile["prev_profile_ref"] = archive_name

    validate_calibration_profile(profile)
    active_path.parent.mkdir(parents=True, exist_ok=True)
    active_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return profile


class CalibrationCommitError(Exception):
    """Refused to commit a calibration profile."""


def load_profile(path: Path) -> Dict[str, Any]:
    """Read + validate a CalibrationProfile from disk."""
    profile = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_calibration_profile(profile)
    return profile


_EXPECTED_BAND = {GESTURE_REST: 0, GESTURE_LIGHT: 1, GESTURE_HARD: 2, GESTURE_LEAD_OFF_NEG: 0}


def evaluate_profile(
    profile: Dict[str, Any],
    sessions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Evaluate a profile against held_out sessions only.
    
    Args:
        profile: CalibrationProfile dict with thresholds
        sessions: List of CaptureSession dicts
        
    Returns:
        {"n": int, "accuracy": float, "confusion": {真档: {判档: n}}}
        
    Raises:
        ValueError: If no held_out sessions found
    """
    th_loose = profile["thresholds"]["th_loose_max"]
    th_hard = profile["thresholds"]["th_hard_min"]
    held_out = [s for s in sessions if s.get("held_out", False)]
    
    if not held_out:
        raise ValueError("No held_out sessions found; cannot evaluate")
    
    confusion: Dict[int, Dict[int, int]] = {0: {0: 0, 1: 0, 2: 0}, 1: {0: 0, 1: 0, 2: 0}, 2: {0: 0, 1: 0, 2: 0}}
    n = 0
    correct = 0
    
    for sess in held_out:
        gesture = sess.get("gesture_label")
        feature = sess.get("feature_window") or {}
        if gesture not in _EXPECTED_BAND or "norm" not in feature:
            continue
        if gesture == GESTURE_LEAD_OFF_NEG:
            continue
            
        norm = float(feature["norm"])
        expected = _EXPECTED_BAND[gesture]
        predicted = 0 if norm < th_loose else (1 if norm < th_hard else 2)
        
        n += 1
        confusion[expected][predicted] += 1
        if predicted == expected:
            correct += 1
    
    accuracy = correct / n if n > 0 else 0.0
    
    return {
        "n": n,
        "accuracy": accuracy,
        "confusion": confusion,
    }


def evaluate_sessions(
    profile: Dict[str, Any],
    sessions: List[Dict[str, Any]],
    *,
    held_out_only: bool = True,
) -> Dict[str, Any]:
    """Score windows against a committed profile (false-pos / false-neg report).

    Intended for held_out sessions AFTER commit; they never touch the fit.
    A window counts as *false green* when a lead_off_neg window would reach
    band>=1 without its quality flags forcing suppression.
    """
    th_loose = profile["thresholds"]["th_loose_max"]
    th_hard = profile["thresholds"]["th_hard_min"]
    pool = [s for s in sessions if s.get("held_out", False)] if held_out_only else sessions

    per_gesture: Dict[str, Dict[str, int]] = {}
    false_green = 0
    false_pos = 0
    false_neg = 0
    n = 0
    for sess in pool:
        gesture = sess.get("gesture_label")
        feature = sess.get("feature_window") or {}
        if gesture not in _EXPECTED_BAND or "norm" not in feature:
            continue
        norm = float(feature["norm"])
        q = sess.get("quality", {})
        suppressed = bool(q.get("lead_off") or q.get("poor_contact") or q.get("clip"))
        predicted = 0 if norm < th_loose else (1 if norm < th_hard else 2)
        if suppressed:
            predicted = 0
        expected = _EXPECTED_BAND[gesture]
        n += 1
        bucket = per_gesture.setdefault(gesture, {"n": 0, "correct": 0})
        bucket["n"] += 1
        if predicted == expected:
            bucket["correct"] += 1
        if gesture == GESTURE_LEAD_OFF_NEG and norm >= th_loose and not suppressed:
            false_green += 1
        if expected == 0 and predicted >= 1:
            false_pos += 1
        if expected >= 1 and predicted == 0:
            false_neg += 1

    return {
        "n_windows": n,
        "false_green": false_green,
        "false_pos": false_pos,
        "false_neg": false_neg,
        "false_pos_rate": (false_pos / n) if n else None,
        "false_neg_rate": (false_neg / n) if n else None,
        "per_gesture": per_gesture,
        "held_out_only": held_out_only,
    }


def calibrate_from_sessions(
    sessions: List[Dict[str, Any]],
    *,
    user_id: str,
    device_id: str,
    donning_id: Optional[str] = None,
    fs: float = 500.0,
    window_ms: float = 200.0,
    hop_ms: float = 50.0,
    norm_scale_uV: float = 200.0,
    prev_profile_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """Calibrate from CaptureSession list. EXCLUDES held_out=true sessions from fit.
    
    Args:
        sessions: List of CaptureSession dicts (must have gesture_label, held_out, feature_window)
        user_id: User identifier
        device_id: Device identifier
        donning_id: Optional donning identifier
        fs: Sampling rate
        window_ms: Window size
        hop_ms: Hop size
        norm_scale_uV: Normalization scale
        prev_profile_ref: Previous profile reference for rollback
        
    Returns:
        CalibrationProfile dict
        
    Raises:
        ValueError: If insufficient non-held-out sessions for calibration
    """
    training_windows = [s for s in sessions if not s.get("held_out", False)]
    held_out_windows = [s for s in sessions if s.get("held_out", False)]

    rest_norms = []
    light_norms = []
    hard_norms = []
    lead_off_norms = []

    for sess in training_windows:
        gesture = sess.get("gesture_label")
        feature = sess.get("feature_window")
        if not feature or "norm" not in feature:
            continue
        
        norm = feature["norm"]
        if gesture == GESTURE_REST:
            rest_norms.append(norm)
        elif gesture == GESTURE_LIGHT:
            light_norms.append(norm)
        elif gesture == GESTURE_HARD:
            hard_norms.append(norm)
        elif gesture == GESTURE_LEAD_OFF_NEG:
            lead_off_norms.append(norm)

    if len(rest_norms) < 3 or len(light_norms) < 3 or len(hard_norms) < 3:
        raise ValueError(
            f"Insufficient training samples: rest={len(rest_norms)}, "
            f"light={len(light_norms)}, hard={len(hard_norms)}. "
            f"Need at least 3 each (held_out excluded)."
        )

    rest_arr = np.array(rest_norms, dtype=np.float64)
    light_arr = np.array(light_norms, dtype=np.float64)
    hard_arr = np.array(hard_norms, dtype=np.float64)

    p95_relax = float(np.percentile(rest_arr, 95))
    p10_light = float(np.percentile(light_arr, 10))
    p90_light = float(np.percentile(light_arr, 90))
    p10_hard = float(np.percentile(hard_arr, 10))

    th_loose = min(p95_relax + 0.03, 0.5 * (p95_relax + p10_light))
    th_loose = float(np.clip(th_loose, 0.05, 0.35))
    th_hard = float(np.clip(0.5 * (p90_light + p10_hard), th_loose + 0.08, 0.85))

    neg_ok = True
    if lead_off_norms:
        lead_off_above_th = sum(1 for n in lead_off_norms if n >= th_loose)
        neg_ok = lead_off_above_th == 0

    profile = create_calibration_profile(
        user_id=user_id,
        device_id=device_id,
        th_loose_max=th_loose,
        th_hard_min=th_hard,
        donning_id=donning_id,
        prev_profile_ref=prev_profile_ref,
        stale=False,
    )

    profile["calibration_debug"] = {
        "fs": fs,
        "window_ms": window_ms,
        "hop_ms": hop_ms,
        "n_training_windows": len(training_windows),
        "n_held_out_windows": len(held_out_windows),
        "n_rest": len(rest_norms),
        "n_light": len(light_norms),
        "n_hard": len(hard_norms),
        "n_lead_off": len(lead_off_norms),
        "p95_relax": p95_relax,
        "p10_light": p10_light,
        "p90_light": p90_light,
        "p10_hard": p10_hard,
        "negatives_ok": neg_ok,
        "committed": bool(neg_ok),
        "notes": "Calibrated from sessions. Held-out excluded from fit.",
    }

    return profile


def rollback_profile(
    current_profile_path: Path,
    store_dir: Path,
) -> Optional[Dict[str, Any]]:
    """Rollback to previous calibration profile if prev_profile_ref exists.
    
    Args:
        current_profile_path: Path to current active profile
        store_dir: Directory containing profile history
        
    Returns:
        Restored profile dict, or None if no prev_profile_ref
        
    Side effects:
        - Marks current profile as stale=true
        - Restores prev_profile_ref as active
    """
    current_profile_path = Path(current_profile_path)
    store_dir = Path(store_dir)
    
    if not current_profile_path.exists():
        raise FileNotFoundError(f"Current profile not found: {current_profile_path}")
    
    current = json.loads(current_profile_path.read_text(encoding="utf-8"))
    prev_ref = current.get("prev_profile_ref")
    
    if not prev_ref:
        return None
    
    prev_path = store_dir / prev_ref
    if not prev_path.exists():
        raise FileNotFoundError(f"Previous profile not found: {prev_path}")
    
    prev_profile = json.loads(prev_path.read_text(encoding="utf-8"))
    validate_calibration_profile(prev_profile)

    current["stale"] = True
    stale_name = f"{current_profile_path.stem}_stale_{int(time.time() * 1000)}.json"
    store_dir.mkdir(parents=True, exist_ok=True)
    (store_dir / stale_name).write_text(
        json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    current_profile_path.write_text(
        json.dumps(prev_profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    
    return prev_profile
