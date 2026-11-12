"""Continuous Rolling Raw EMG Buffer and Exporter.

Implements a 30-second circular raw data recorder as identified in Waveletech vendor specifications.
Enables continuous background recording, retrospective trigger capture, and offline False Alarm Rate auditing.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np


class RollingRawBuffer:
    """Circular pre-allocated buffer for continuous multi-channel raw sEMG streaming."""

    def __init__(
        self,
        capacity_seconds: float = 30.0,
        fs: float = 2000.0,
        n_channels: int = 8,
    ) -> None:
        self.capacity_seconds = capacity_seconds
        self.fs = fs
        self.n_channels = n_channels
        self.capacity_samples = int(fs * capacity_seconds)

        # Pre-allocated arrays for zero-allocation streaming
        self._data_buffer = np.zeros((self.capacity_samples, n_channels), dtype=np.float32)
        self._ts_buffer = np.zeros(self.capacity_samples, dtype=np.float64)
        self._seq_buffer = np.zeros(self.capacity_samples, dtype=np.int32)

        self._head_idx = 0
        self._total_samples_pushed = 0
        self._last_auto_flush_time = time.time()

    def push(
        self,
        sample_uv: np.ndarray,
        timestamp_sec: float | None = None,
        seq: int = 0,
    ) -> None:
        """Push a single raw 8-channel sample (microvolts) into the circular buffer."""
        if timestamp_sec is None:
            timestamp_sec = time.time()

        self._data_buffer[self._head_idx] = sample_uv
        self._ts_buffer[self._head_idx] = timestamp_sec
        self._seq_buffer[self._head_idx] = seq

        self._head_idx = (self._head_idx + 1) % self.capacity_samples
        self._total_samples_pushed += 1

    def push_batch(
        self,
        samples_uv: np.ndarray,
        timestamps_sec: np.ndarray | None = None,
        seqs: np.ndarray | None = None,
    ) -> None:
        """Push a batch of samples of shape (N, n_channels)."""
        n_pts = len(samples_uv)
        if n_pts == 0:
            return

        if timestamps_sec is None:
            t_now = time.time()
            timestamps_sec = t_now + np.arange(n_pts) / self.fs
        if seqs is None:
            seqs = np.zeros(n_pts, dtype=np.int32)

        for i in range(n_pts):
            self.push(samples_uv[i], float(timestamps_sec[i]), int(seqs[i]))

    @property
    def current_size(self) -> int:
        """Number of valid samples currently retained in buffer."""
        return min(self._total_samples_pushed, self.capacity_samples)

    @property
    def is_full(self) -> bool:
        """Whether the circular buffer has filled its full 30-second capacity."""
        return self._total_samples_pushed >= self.capacity_samples

    def snapshot(
        self,
        duration_seconds: float | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Extract chronologically ordered slice of recent data.

        Returns:
            (timestamps_sec, emg_uv, seq_ids)
        """
        valid_count = self.current_size
        if valid_count == 0:
            empty_emg = np.empty((0, self.n_channels), dtype=np.float32)
            empty_ts = np.empty(0, dtype=np.float64)
            empty_seq = np.empty(0, dtype=np.int32)
            return empty_ts, empty_emg, empty_seq

        if duration_seconds is not None:
            requested_pts = int(duration_seconds * self.fs)
            fetch_count = min(valid_count, requested_pts)
        else:
            fetch_count = valid_count

        if self._total_samples_pushed <= self.capacity_samples:
            # Buffer has not wrapped around yet
            start = valid_count - fetch_count
            end = valid_count
            ts = self._ts_buffer[start:end].copy()
            data = self._data_buffer[start:end].copy()
            seq = self._seq_buffer[start:end].copy()
        else:
            # Buffer wrapped around: head_idx points to the oldest entry
            # To get the most recent fetch_count points:
            # Order from oldest in window to newest (which is at head_idx - 1)
            ordered_indices = (np.arange(self.capacity_samples - fetch_count, self.capacity_samples) + self._head_idx) % self.capacity_samples
            ts = self._ts_buffer[ordered_indices].copy()
            data = self._data_buffer[ordered_indices].copy()
            seq = self._seq_buffer[ordered_indices].copy()

        return ts, data, seq

    def save_snapshot_npz(
        self,
        output_path: Path | str,
        duration_seconds: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Save buffer snapshot to a standard .npz archive."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        ts, data, seq = self.snapshot(duration_seconds=duration_seconds)
        meta_str = json.dumps(metadata or {}, ensure_ascii=False)

        np.savez_compressed(
            output_path,
            emg_uv=data,
            timestamps=ts,
            sequences=seq,
            fs=self.fs,
            meta=meta_str,
        )
        return output_path

    def export_npz(
        self,
        output_path: Path | str,
        duration_seconds: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """Alias for save_snapshot_npz."""
        return self.save_snapshot_npz(output_path, duration_seconds, metadata)

    def auto_flush_check(
        self,
        interval_seconds: float = 30.0,
        dump_dir: Path | str = "rolling_records",
        prefix: str = "raw_rolling",
    ) -> Path | None:
        """Check if interval has elapsed since last flush; if so, export archive and reset timer."""
        now = time.time()
        if now - self._last_auto_flush_time >= interval_seconds:
            self._last_auto_flush_time = now
            dump_dir = Path(dump_dir)
            t_iso = time.strftime("%Y%m%dT%H%M%S")
            file_name = f"{prefix}_{t_iso}.npz"
            path = dump_dir / file_name
            return self.save_snapshot_npz(path, duration_seconds=interval_seconds)
        return None
