"""Split one recording into three training sets.

IMU windows keep the motion label and the 12 features. Force rows keep the
calibration gesture. Five-class rows keep relax/pinch/rub/snap/fist. A paired
window may add an IMU window and a decision; it does not write the force set
or the five-class set. One joint feature vector is refused.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from .capture_session import VALID_GESTURES
from .fusion import (
    FIVE_CLASS,
    IMU_FEATURES,
    FusionError,
    export_label,
    five_class_train_ready,
    fuse_pair,
    imu_test_ready,
    imu_train_ready,
    screen_five_class_label,
)

TRACKS = ("imu", "force", "five_class", "paired")
DEFAULT_IMU_LABELS = ("circle", "up_wave", "punch", "other")
_IMU_LABEL_ORDER = ("circle", "up_wave", "punch", "hook", "uppercut", "other")


def build_joint_snapshot(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """There is no joint IMU+EMG training snapshot."""
    raise FusionError(
        "IMU features and EMG effort stay in separate training sets"
        + (f" ({len(rows)} rows)" if rows else "")
    )


def split_recording(
    rows: Sequence[Mapping[str, Any]],
    *,
    imu_labels: Optional[Sequence[str]] = None,
    merge_punch_family: bool = False,
    five_min_count: int = 10,
) -> Dict[str, Any]:
    """Bucket rows. Contamination raises. Short sets come back with ready=false."""
    labels = tuple(imu_labels) if imu_labels is not None else DEFAULT_IMU_LABELS
    if not labels:
        raise FusionError("IMU label set is empty")
    _check_imu_label_set(labels)

    imu_train: List[Dict[str, Any]] = []
    imu_test: List[Dict[str, Any]] = []
    force_rows: List[Dict[str, Any]] = []
    five_rows: List[Dict[str, Any]] = []
    decisions: List[Dict[str, Any]] = []

    for index, row in enumerate(rows):
        track = _track(row, index)
        if track == "imu":
            window = _imu_window(row, labels, merge_punch_family)
            (imu_test if window.pop("_held_out") else imu_train).append(window)
        elif track == "force":
            force_rows.append(_force_row(row))
        elif track == "five_class":
            five_rows.append(_five_row(row))
        elif track == "paired":
            decision, window = _paired(row, labels, merge_punch_family)
            decisions.append(decision)
            if window is not None:
                (imu_test if window.pop("_held_out") else imu_train).append(window)
        else:
            raise FusionError(f"unhandled track: {track}")

    imu_snapshot = {
        "source": "emg_gate.split_tracks",
        "labels": list(labels),
        "merge_punch_family": merge_punch_family,
        "windows": imu_train,
        "test_windows": imu_test,
    }
    _assert_imu_snapshot(imu_snapshot)
    report = _report(imu_snapshot, force_rows, five_rows, decisions, five_min_count)
    return {
        "imu_snapshot": imu_snapshot,
        "force_rows": force_rows,
        "five_rows": five_rows,
        "decisions": decisions,
        "report": report,
    }


def _track(row: Mapping[str, Any], index: int) -> str:
    if not isinstance(row, Mapping):
        raise FusionError(f"row {index} must be an object")
    if "track" not in row:
        raise FusionError(f"row {index} needs a track: {', '.join(TRACKS)}")
    track = row["track"]
    if track == "joint":
        raise FusionError("IMU features and EMG effort stay in separate training sets")
    if track not in TRACKS:
        raise FusionError(f"row {index} has unknown track: {track}")
    _id(row, "session_id")
    _id(row, "donning_id")
    if "held_out" in row and not isinstance(row["held_out"], bool):
        raise FusionError("held_out must be a boolean")
    return track


def _id(row: Mapping[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value:
        raise FusionError(f"{key} must be a non-empty string")
    return value


def _held(row: Mapping[str, Any]) -> bool:
    return row.get("held_out") is True


def _features(row: Mapping[str, Any]) -> List[float]:
    values = row.get("features")
    if not isinstance(values, list) or len(values) != IMU_FEATURES:
        raise FusionError(f"IMU features must be {IMU_FEATURES} finite numbers")
    out = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise FusionError("IMU features must be finite numbers")
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            raise FusionError("IMU features must be finite numbers")
        out.append(number)
    return out


def _check_imu_label_set(labels: Sequence[str]) -> None:
    for label in labels:
        if label in VALID_GESTURES or label in FIVE_CLASS:
            raise FusionError(f"IMU label set cannot contain {label}")


def _imu_window(
    row: Mapping[str, Any],
    labels: Sequence[str],
    merge_punch_family: bool,
) -> Dict[str, Any]:
    if any(key in row for key in ("norm", "band", "effort", "emg", "force_label", "five_class_label")):
        raise FusionError("IMU training rows cannot carry EMG effort")
    motion = row.get("motion")
    exported = row.get("gesture_label")
    if isinstance(motion, str):
        label = export_label(motion, merge_punch_family=merge_punch_family)
        if exported is not None and exported != label:
            raise FusionError(
                f"IMU gesture_label must be {label}, derived from motion {motion}"
            )
    elif isinstance(exported, str):
        label = exported
    else:
        raise FusionError("IMU row needs motion or an exported gesture_label")
    return _accept_imu(label, labels, _features(row), row)


def rows_from_platform_fixture(doc: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Watch fixture windows. split=test stays held out and is not a force label."""
    windows = doc.get("windows") if isinstance(doc, Mapping) else None
    if not isinstance(windows, list) or not windows:
        raise FusionError("platform fixture needs a non-empty windows list")
    rows = []
    for index, window in enumerate(windows):
        if not isinstance(window, Mapping):
            raise FusionError(f"fixture window {index} must be an object")
        split = window.get("split")
        if split not in ("train", "test"):
            raise FusionError(f"fixture window {index} needs split train or test")
        rows.append({
            "track": "imu",
            "session_id": window.get("session_id"),
            "donning_id": window.get("donning_id"),
            "gesture_label": window.get("gesture_label"),
            "features": window.get("features"),
            "held_out": split == "test",
        })
    return rows


def _accept_imu(
    label: str,
    labels: Sequence[str],
    features: Sequence[float],
    row: Mapping[str, Any],
) -> Dict[str, Any]:
    if label in VALID_GESTURES or label in FIVE_CLASS:
        raise FusionError(f"IMU training label cannot be {label}")
    if label not in labels:
        raise FusionError(f"IMU label {label} is outside the training set {list(labels)}")
    return {
        "gesture_label": label,
        "session_id": _id(row, "session_id"),
        "donning_id": _id(row, "donning_id"),
        "features": list(features),
        "_held_out": _held(row),
    }


def _force_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    if any(key in row for key in ("motion", "features", "norm", "band", "five_class_label")):
        raise FusionError("force calibration rows cannot carry IMU features or a five-class label")
    label = row.get("gesture_label")
    if label not in VALID_GESTURES:
        raise FusionError(f"force gesture_label must be one of {sorted(VALID_GESTURES)}")
    return {
        "gesture_label": label,
        "session_id": _id(row, "session_id"),
        "donning_id": _id(row, "donning_id"),
        "held_out": _held(row),
    }


def _five_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    if any(key in row for key in ("motion", "features", "norm", "band", "force_label")):
        raise FusionError("five-class rows cannot carry IMU features or a force label")
    label = screen_five_class_label(row.get("gesture_label"))
    return {
        "gesture_label": label,
        "session_id": _id(row, "session_id"),
        "donning_id": _id(row, "donning_id"),
        "held_out": _held(row),
    }


def _paired(
    row: Mapping[str, Any],
    labels: Sequence[str],
    merge_punch_family: bool,
):
    if any(key in row for key in ("gesture_label", "force_label", "five_class_label", "features", "norm")):
        raise FusionError("a paired window keeps motion and effort inside pair, not as one label")
    pair = row.get("pair")
    if not isinstance(pair, dict):
        raise FusionError("paired row needs a pair object")
    if pair.get("donning_id") != row["donning_id"]:
        raise FusionError("paired donning_id must match the EMG donning_id")
    decision = fuse_pair(pair)
    decision["session_id"] = _id(row, "session_id")
    decision["held_out"] = _held(row)
    window = None
    features = pair.get("imu", {}).get("features")
    if features is not None:
        label = export_label(pair["imu"]["motion"], merge_punch_family=merge_punch_family)
        window = _accept_imu(label, labels, _features(pair["imu"]), row)
    return decision, window


def _assert_imu_snapshot(snapshot: Mapping[str, Any]) -> None:
    labels = set(snapshot["labels"])
    for window in list(snapshot["windows"]) + list(snapshot["test_windows"]):
        if window["gesture_label"] not in labels:
            raise FusionError("IMU snapshot label drifted")
        if window["gesture_label"] in VALID_GESTURES or window["gesture_label"] in FIVE_CLASS:
            raise FusionError("IMU snapshot picked up a non-motion label")
        if len(window["features"]) != IMU_FEATURES:
            raise FusionError("IMU snapshot feature width drifted")
        if any(key in window for key in ("norm", "band", "effort", "emg")):
            raise FusionError("IMU snapshot picked up EMG effort")


def _sessions(windows: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    found: Dict[str, set] = {}
    for window in windows:
        found.setdefault(window["gesture_label"], set()).add(window["session_id"])
    return {label: len(sessions) for label, sessions in found.items()}


def _report(
    snapshot: Mapping[str, Any],
    force_rows: Sequence[Mapping[str, Any]],
    five_rows: Sequence[Mapping[str, Any]],
    decisions: Sequence[Mapping[str, Any]],
    five_min_count: int,
) -> Dict[str, Any]:
    labels = list(snapshot["labels"])
    train_sessions = {label: 0 for label in labels}
    train_sessions.update(_sessions(snapshot["windows"]))
    test_counts = {label: 0 for label in labels}
    for window in snapshot["test_windows"]:
        test_counts[window["gesture_label"]] = test_counts.get(window["gesture_label"], 0) + 1
    five_counts: Dict[str, int] = {label: 0 for label in FIVE_CLASS}
    for row in five_rows:
        if not row["held_out"]:
            five_counts[row["gesture_label"]] += 1
    five = (
        {"ready": False, "thin": list(FIVE_CLASS), "leaks": [], "foreign": [], "min_count": five_min_count,
         "why": "no five-class rows"}
        if not five_rows
        else five_class_train_ready(five_counts, min_count=five_min_count)
    )
    force_by_label: Dict[str, int] = {}
    for row in force_rows:
        force_by_label[row["gesture_label"]] = force_by_label.get(row["gesture_label"], 0) + 1
    train = imu_train_ready(train_sessions, labels)
    test = imu_test_ready(test_counts, labels)
    return {
        "imu": {
            "windows": len(snapshot["windows"]),
            "test_windows": len(snapshot["test_windows"]),
            "labels": labels,
            "train": train,
            "test": test,
            "continue": train["ready"],
        },
        "force": {
            "rows": len(force_rows),
            "by_label": force_by_label,
            "model": False,
            "why": "force stays on the calibration profile; this split does not fit a model",
        },
        "five_class": {
            "rows": len(five_rows),
            "model": False,
            "train": five,
            "why": "five-class rows are kept apart; this split does not train a model",
        },
        "decisions": len(decisions),
    }
