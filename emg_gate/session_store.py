"""P0 local session pack: create session / don-doff / append window / export.

Layout (all local; nothing here uploads):

    <root>/pack.json                 pack meta + donning history
    <root>/sessions/<session_id>.json  session meta (donning_id, held_out, context)
    <root>/windows/<session_id>.jsonl  CaptureSession rows (may hold raw_window)

Rules enforced here (ADR-2026-09-23-EMG §1):
- a session can only be created under an *active* donning; doff() ends it, so
  re-donning forces a new donning_id
- every window is validated (validate_capture_session) BEFORE it is written
- default export strips raw_window; include_raw is an explicit developer flag
- export is deterministic (sorted rows, sorted keys) and returns its sha256
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from . import SCHEMA_VERSION
from .capture_session import (
    GESTURE_LEAD_OFF_NEG,
    POSITIVE_GESTURES,
    create_capture_session,
    strip_raw_from_session,
)
from .cloud_safe_event import create_cloud_safe_event
from .quality import quality_flags_to_label


class SessionPackError(Exception):
    """Session pack state / protocol violation."""


def _now_ms() -> float:
    return time.time() * 1000.0


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_row(row: Dict[str, Any]) -> str:
    """Deterministic single-line JSON used for export + hashing."""
    return json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def row_sort_key(row: Dict[str, Any]) -> Tuple[str, float, str]:
    return (
        str(row.get("session_id", "")),
        float(row.get("obs_ts_device_ms", 0.0)),
        str(row.get("gesture_label", "")),
    )


class SessionPack:
    """On-disk P0 session pack."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.meta_path = self.root / "pack.json"
        self.sessions_dir = self.root / "sessions"
        self.windows_dir = self.root / "windows"

    # ---------- lifecycle ----------

    @classmethod
    def create(cls, root: Path, *, user_id: str, device_id: str) -> "SessionPack":
        pack = cls(root)
        if pack.meta_path.exists():
            raise SessionPackError(f"pack already exists at {pack.root}")
        _write_json(
            pack.meta_path,
            {
                "schema_version": SCHEMA_VERSION,
                "user_id": user_id,
                "device_id": device_id,
                "created_at": _iso_now(),
                "donnings": [],
                "active_donning_id": None,
            },
        )
        pack.sessions_dir.mkdir(parents=True, exist_ok=True)
        pack.windows_dir.mkdir(parents=True, exist_ok=True)
        return pack

    @classmethod
    def open(cls, root: Path) -> "SessionPack":
        pack = cls(root)
        if not pack.meta_path.exists():
            raise SessionPackError(f"no pack.json under {pack.root}")
        return pack

    @property
    def meta(self) -> Dict[str, Any]:
        return _read_json(self.meta_path)

    def _save_meta(self, meta: Dict[str, Any]) -> None:
        _write_json(self.meta_path, meta)

    # ---------- donning ----------

    def don(self, donning_id: Optional[str] = None) -> str:
        """Start a new donning (electrodes placed). Ends any active one."""
        meta = self.meta
        if meta["active_donning_id"] is not None:
            self._end_active(meta)
        donning_id = donning_id or f"don_{uuid.uuid4().hex[:10]}"
        if any(d["donning_id"] == donning_id for d in meta["donnings"]):
            raise SessionPackError(f"donning_id {donning_id!r} already used; re-don needs a new id")
        meta["donnings"].append(
            {"donning_id": donning_id, "started_at": _iso_now(), "ended_at": None}
        )
        meta["active_donning_id"] = donning_id
        self._save_meta(meta)
        return donning_id

    def doff(self) -> Optional[str]:
        """Electrodes removed. Any further session requires don() again."""
        meta = self.meta
        ended = meta["active_donning_id"]
        if ended is not None:
            self._end_active(meta)
            self._save_meta(meta)
        return ended

    @staticmethod
    def _end_active(meta: Dict[str, Any]) -> None:
        active = meta["active_donning_id"]
        for d in meta["donnings"]:
            if d["donning_id"] == active and d["ended_at"] is None:
                d["ended_at"] = _iso_now()
        meta["active_donning_id"] = None

    @property
    def active_donning_id(self) -> Optional[str]:
        return self.meta["active_donning_id"]

    # ---------- sessions ----------

    def create_session(
        self,
        *,
        session_id: Optional[str] = None,
        held_out: bool = False,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a session bound to the active donning. Fails if doffed."""
        meta = self.meta
        donning_id = meta["active_donning_id"]
        if donning_id is None:
            raise SessionPackError("no active donning: call don() before create_session()")
        session_id = session_id or f"sess_{uuid.uuid4().hex[:10]}"
        path = self.sessions_dir / f"{session_id}.json"
        if path.exists():
            raise SessionPackError(f"session_id {session_id!r} already exists")
        _write_json(
            path,
            {
                "schema_version": SCHEMA_VERSION,
                "session_id": session_id,
                "donning_id": donning_id,
                "user_id": meta["user_id"],
                "device_id": meta["device_id"],
                "created_at": _iso_now(),
                "held_out": bool(held_out),
                "context": context or {},
            },
        )
        return session_id

    def session_meta(self, session_id: str) -> Dict[str, Any]:
        path = self.sessions_dir / f"{session_id}.json"
        if not path.exists():
            raise SessionPackError(f"unknown session_id {session_id!r}")
        return _read_json(path)

    def list_sessions(self) -> List[Dict[str, Any]]:
        return sorted(
            (_read_json(p) for p in self.sessions_dir.glob("*.json")),
            key=lambda m: (m["created_at"], m["session_id"]),
        )

    def mark_held_out(self, session_id: str, value: bool = True) -> None:
        """Flip held_out on the session and on every window already stored."""
        meta = self.session_meta(session_id)
        meta["held_out"] = bool(value)
        _write_json(self.sessions_dir / f"{session_id}.json", meta)
        wpath = self.windows_dir / f"{session_id}.jsonl"
        if wpath.exists():
            rows = list(self._iter_file(wpath))
            for r in rows:
                r["held_out"] = bool(value)
            wpath.write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                encoding="utf-8",
            )

    # ---------- windows ----------

    def append_window(
        self,
        session_id: str,
        *,
        gesture_label: str,
        quality: Dict[str, Any],
        obs_ts_device_ms: Optional[float] = None,
        obs_ts_host_ms: Optional[float] = None,
        fs_hz: float = 500.0,
        window_ms: float = 200.0,
        feature_window: Optional[Dict[str, Any]] = None,
        raw_window: Optional[List[float]] = None,
        context: Optional[Dict[str, Any]] = None,
        source: str = "recorded",
    ) -> Dict[str, Any]:
        """Validate then persist one CaptureSession row. Rejects never touch disk."""
        smeta = self.session_meta(session_id)
        host_ms = _now_ms() if obs_ts_host_ms is None else obs_ts_host_ms
        device_ms = host_ms if obs_ts_device_ms is None else obs_ts_device_ms
        payload_kind = "raw_window" if raw_window is not None and feature_window is None else "feature_window"
        row = create_capture_session(
            user_id=smeta["user_id"],
            device_id=smeta["device_id"],
            session_id=session_id,
            donning_id=smeta["donning_id"],
            gesture_label=gesture_label,
            obs_ts_device_ms=device_ms,
            obs_ts_host_ms=host_ms,
            fs_hz=fs_hz,
            window_ms=window_ms,
            payload_kind=payload_kind,
            raw_window=raw_window,
            feature_window=feature_window,
            quality=quality,
            context=context if context else (smeta.get("context") or None),
            held_out=bool(smeta.get("held_out", False)),
            source=source,
        )
        wpath = self.windows_dir / f"{session_id}.jsonl"
        wpath.parent.mkdir(parents=True, exist_ok=True)
        with wpath.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    @staticmethod
    def _iter_file(path: Path) -> Iterator[Dict[str, Any]]:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def iter_windows(self, session_id: Optional[str] = None) -> Iterator[Dict[str, Any]]:
        if session_id is not None:
            p = self.windows_dir / f"{session_id}.jsonl"
            if p.exists():
                yield from self._iter_file(p)
            return
        for p in sorted(self.windows_dir.glob("*.jsonl")):
            yield from self._iter_file(p)

    def load_windows(self) -> List[Dict[str, Any]]:
        return sorted(self.iter_windows(), key=row_sort_key)

    # ---------- export ----------

    def export(self, out_path: Path, *, include_raw: bool = False, mixed_ok: bool = False) -> Dict[str, Any]:
        """Deterministic export. Default strips raw_window (privacy default).
        
        Raises ValueError if both recorded and synthetic sources appear unless mixed_ok=True.
        """
        rows = self.load_windows()
        
        source_counts = {"recorded": 0, "synthetic": 0}
        for r in rows:
            src = r.get("source", "recorded")
            if src in source_counts:
                source_counts[src] += 1
        
        has_recorded = source_counts["recorded"] > 0
        has_synthetic = source_counts["synthetic"] > 0
        if has_recorded and has_synthetic and not mixed_ok:
            raise ValueError(
                f"Export contains mixed sources (recorded={source_counts['recorded']}, "
                f"synthetic={source_counts['synthetic']}). Use --mixed-ok to override."
            )
        
        if not include_raw:
            rows = [strip_raw_from_session(r) for r in rows]
        lines = [canonical_row(r) for r in rows]
        blob = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(blob)
        return {
            "path": str(out_path),
            "n_rows": len(rows),
            "include_raw": bool(include_raw),
            "has_raw": any("raw_window" in r for r in rows),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "source_recorded": source_counts["recorded"],
            "source_synthetic": source_counts["synthetic"],
        }

    def export_cloud_safe(self, out_path: Path) -> Dict[str, Any]:
        """Windows → CloudSafeEvent rows (band + quality + t_host_ms only)."""
        events = []
        for r in self.load_windows():
            feature = r.get("feature_window") or {}
            band = feature.get("band")
            events.append(
                create_cloud_safe_event(
                    kind=f"capture_{r['gesture_label']}",
                    quality=quality_flags_to_label(r["quality"]),
                    t_host_ms=r["obs_ts_host_ms"],
                    band=band if band in (0, 1, 2) else None,
                    confidence=feature.get("confidence"),
                )
            )
        lines = [canonical_row(e) for e in events]
        blob = ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(blob)
        return {"path": str(out_path), "n_rows": len(events), "sha256": hashlib.sha256(blob).hexdigest()}

    # ---------- accounting ----------

    def valid_coverage_ms(self, *, exclude_held_out: bool = False) -> Dict[str, float]:
        """Per-gesture union coverage (ms) of quality-qualified windows.

        Qualified = positive gesture with all flags false, or lead_off_neg with
        lead_off=true. Overlapping windows (hop < window) are not double counted.
        ``exclude_held_out`` gives the portion that may enter threshold fitting.
        """
        per_gesture: Dict[str, List[Tuple[float, float]]] = {}
        for r in self.iter_windows():
            if exclude_held_out and r.get("held_out"):
                continue
            g = r["gesture_label"]
            q = r["quality"]
            flags = {k: v for k, v in q.items() if k != "snr_hint"}
            if g in POSITIVE_GESTURES and any(flags.values()):
                continue
            if g == GESTURE_LEAD_OFF_NEG and not q.get("lead_off"):
                continue
            start = float(r["obs_ts_device_ms"])
            per_gesture.setdefault(g, []).append((start, start + float(r["window_ms"])))
        return {g: _union_ms(iv) for g, iv in per_gesture.items()}


def _union_ms(intervals: Iterable[Tuple[float, float]]) -> float:
    total = 0.0
    cur_start: Optional[float] = None
    cur_end = 0.0
    for start, end in sorted(intervals):
        if cur_start is None:
            cur_start, cur_end = start, end
        elif start <= cur_end:
            cur_end = max(cur_end, end)
        else:
            total += cur_end - cur_start
            cur_start, cur_end = start, end
    if cur_start is not None:
        total += cur_end - cur_start
    return total
