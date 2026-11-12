"""P0 acceptance checklist (ADR-2026-09-23-EMG §1.5) against a session pack.

Items:
  1. new session requires session_id + donning_id
  2. re-don forces a new donning_id (>=2 donnings, all closed between)
  3. rest / light / hard / lead_off_neg each reach the required valid duration
  4. held_out markable (>=1 held_out session)
  5. local export reproducible (same sha256 twice) and default export has no raw

Each item reports sat / unsat with the numbers behind the verdict.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict, List

from .capture_session import (
    GESTURE_HARD,
    GESTURE_LEAD_OFF_NEG,
    GESTURE_LIGHT,
    GESTURE_REST,
    CaptureSessionError,
    validate_capture_session,
)
from .session_store import SessionPack, SessionPackError
from .splits import find_leaks, split_grid

ADR_MIN_SECONDS_PER_GESTURE = 120.0
REQUIRED_GESTURES = (GESTURE_REST, GESTURE_LIGHT, GESTURE_HARD, GESTURE_LEAD_OFF_NEG)

ITEM_TITLES = {
    "session_and_donning_ids": "新建会话必有 session_id + donning_id",
    "redon_new_donning_id": "摘戴强制新 donning_id（≥2 次 donning）",
    "gesture_durations": "三档 + 松脱负样可采满时长",
    "held_out_markable": "可标记 held_out",
    "export_reproducible_no_raw": "本地导出可复现；默认上传无 raw",
    "no_split_leak": "训练/测试划分无泄漏",
}


def check_p0_acceptance(
    pack_dir: Path,
    *,
    min_seconds_per_gesture: float = ADR_MIN_SECONDS_PER_GESTURE,
) -> Dict[str, Any]:
    """Evaluate the five P0 items. Never raises on a bad pack; reports unsat."""
    items: Dict[str, Dict[str, Any]] = {}

    try:
        pack = SessionPack.open(pack_dir)
    except SessionPackError as exc:
        for key in ITEM_TITLES:
            items[key] = {"sat": False, "detail": {"error": str(exc)}}
        return _finish(items, min_seconds_per_gesture)

    windows = pack.load_windows()
    sessions = pack.list_sessions()
    meta = pack.meta

    # 1. ids present + every row validates against the whitelist schema
    invalid: List[str] = []
    for r in windows:
        try:
            validate_capture_session(r)
        except CaptureSessionError as exc:
            invalid.append(str(exc))
    sessions_missing_ids = [
        s["session_id"] for s in sessions if not s.get("session_id") or not s.get("donning_id")
    ]
    items["session_and_donning_ids"] = {
        "sat": bool(sessions) and not sessions_missing_ids and not invalid,
        "detail": {
            "n_sessions": len(sessions),
            "n_windows": len(windows),
            "sessions_missing_ids": sessions_missing_ids,
            "invalid_windows": invalid[:5],
            "n_invalid_windows": len(invalid),
        },
    }

    # 2. re-don: >=2 donnings, each earlier donning closed before the next
    donnings = meta.get("donnings", [])
    donning_ids = [d["donning_id"] for d in donnings]
    closed_before_next = all(d.get("ended_at") for d in donnings[:-1])
    unique = len(set(donning_ids)) == len(donning_ids)
    session_donnings = {s["donning_id"] for s in sessions}
    items["redon_new_donning_id"] = {
        "sat": len(donning_ids) >= 2 and unique and closed_before_next and session_donnings <= set(donning_ids),
        "detail": {
            "donning_ids": donning_ids,
            "unique": unique,
            "closed_before_next": closed_before_next,
            "session_donning_ids": sorted(session_donnings),
        },
    }

    # 3. durations of quality-qualified windows per required gesture.
    #    Verdict uses the NON-held_out portion: that is all the fit may see.
    coverage_all = pack.valid_coverage_ms()
    coverage_train = pack.valid_coverage_ms(exclude_held_out=True)
    need_ms = min_seconds_per_gesture * 1000.0
    per_gesture = {
        g: {
            "valid_s_all": round(coverage_all.get(g, 0.0) / 1000.0, 2),
            "valid_s_train": round(coverage_train.get(g, 0.0) / 1000.0, 2),
            "sat": coverage_train.get(g, 0.0) >= need_ms,
        }
        for g in REQUIRED_GESTURES
    }
    items["gesture_durations"] = {
        "sat": all(v["sat"] for v in per_gesture.values()),
        "detail": {
            "min_seconds_per_gesture": min_seconds_per_gesture,
            "verdict_basis": "valid_s_train (held_out excluded)",
            "per_gesture": per_gesture,
        },
    }

    # 4. held_out
    held_out_sessions = [s["session_id"] for s in sessions if s.get("held_out")]
    held_out_windows = sum(1 for r in windows if r.get("held_out"))
    items["held_out_markable"] = {
        "sat": bool(held_out_sessions) and held_out_windows > 0,
        "detail": {"held_out_sessions": held_out_sessions, "held_out_windows": held_out_windows},
    }

    # 5. export twice → same hash; default export carries no raw
    with tempfile.TemporaryDirectory() as tmp:
        e1 = pack.export(Path(tmp) / "a.jsonl")
        e2 = pack.export(Path(tmp) / "b.jsonl")
    items["export_reproducible_no_raw"] = {
        "sat": bool(windows) and e1["sha256"] == e2["sha256"] and not e1["has_raw"],
        "detail": {
            "sha256_run1": e1["sha256"],
            "sha256_run2": e2["sha256"],
            "n_rows": e1["n_rows"],
            "default_export_has_raw": e1["has_raw"],
            "pack_stores_raw_locally": any("raw_window" in r for r in windows),
        },
    }

    # 6. no train/test leak in donning × gesture grid
    grid = split_grid(windows)
    leaks = find_leaks(grid)
    items["no_split_leak"] = {
        "sat": bool(windows) and len(leaks) == 0,
        "detail": {"grid": {f"{d}:{g}": counts for (d, g), counts in grid.items()}, "leaks": leaks},
    }

    return _finish(items, min_seconds_per_gesture)


def _finish(items: Dict[str, Dict[str, Any]], min_seconds: float) -> Dict[str, Any]:
    return {
        "items": items,
        "all_sat": all(v["sat"] for v in items.values()),
        "min_seconds_per_gesture": min_seconds,
        "adr_min_seconds_per_gesture": ADR_MIN_SECONDS_PER_GESTURE,
    }


def format_checklist_report(results: Dict[str, Any]) -> str:
    lines = ["# P0 验收清单（ADR §1.5）", ""]
    for key, title in ITEM_TITLES.items():
        item = results["items"].get(key, {"sat": False, "detail": {}})
        mark = "x" if item["sat"] else " "
        lines.append(f"- [{mark}] {title} — {'sat' if item['sat'] else 'UNSAT'}")
        for k, v in item["detail"].items():
            if k == "grid":
                continue
            lines.append(f"    - {k}: {v}")
    lines.append("")
    
    # Append donning × gesture grid if present
    no_split_item = results["items"].get("no_split_leak", {})
    grid_dict = no_split_item.get("detail", {}).get("grid", {})
    if grid_dict:
        lines.append("## 佩戴 × 手势划分格子")
        lines.append("")
        grid_parsed = {}
        for key_str, counts in grid_dict.items():
            donning, gesture = key_str.split(":", 1)
            if donning not in grid_parsed:
                grid_parsed[donning] = {}
            grid_parsed[donning][gesture] = counts
        
        all_donnings = sorted(grid_parsed.keys())
        all_gestures = sorted({g for d_dict in grid_parsed.values() for g in d_dict.keys()})
        
        header = ["donning_id"] + all_gestures
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join([" --- " for _ in header]) + "|")
        
        for donning in all_donnings:
            row = [donning]
            for gesture in all_gestures:
                counts = grid_parsed[donning].get(gesture, {"train": 0, "test": 0})
                train = counts["train"]
                test = counts["test"]
                if train > 0 and test > 0:
                    cell = f"T{train}+H{test}"
                elif train > 0:
                    cell = f"T{train}"
                elif test > 0:
                    cell = f"H{test}"
                else:
                    cell = "·"
                row.append(cell)
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
    
    verdict = "PASS" if results["all_sat"] else "FAIL"
    note = ""
    if results["min_seconds_per_gesture"] < results["adr_min_seconds_per_gesture"]:
        note = (
            f"（时长门槛已放宽到 {results['min_seconds_per_gesture']} s/档；"
            f"ADR 要求 {results['adr_min_seconds_per_gesture']} s/档，此结果不构成正式过线）"
        )
    lines.append(f"**Overall: {verdict}** {note}".rstrip())
    return "\n".join(lines)
