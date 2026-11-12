"""Feature extraction for multi-channel sEMG windows.

Includes:
  - Classic Hudgins 4 time-domain features: MAV, WL, ZC, SSC
  - Extended time-domain features: RMS, WAMP, VAR
  - Frequency-domain features: MNF (Mean Frequency), MDF (Median Frequency)
"""

from __future__ import annotations

import numpy as np


def mean_absolute_value(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """MAV: Mean Absolute Value."""
    return np.mean(np.abs(x), axis=axis)


def root_mean_square(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """RMS: Root Mean Square."""
    return np.sqrt(np.mean(np.square(x), axis=axis))


def waveform_length(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """WL: Cumulative waveform length along specified axis."""
    diff = np.diff(x, axis=axis)
    return np.sum(np.abs(diff), axis=axis)


def zero_crossings(x: np.ndarray, threshold: float = 10.0, axis: int = -1) -> np.ndarray:
    """ZC: Zero Crossings with noise deadband threshold (in uV)."""
    # Sign multiplication: positive * negative < 0
    s1 = x[..., :-1]
    s2 = x[..., 1:]
    sign_change = (s1 * s2) < 0
    amp_condition = np.abs(s1 - s2) >= threshold
    return np.sum(sign_change & amp_condition, axis=axis)


def slope_sign_changes(x: np.ndarray, threshold: float = 10.0, axis: int = -1) -> np.ndarray:
    """SSC: Slope Sign Changes with noise deadband threshold (in uV)."""
    # Peak / valley test: (x[i] - x[i-1]) * (x[i] - x[i+1]) > 0 with amplitude condition
    x_prev = x[..., :-2]
    x_curr = x[..., 1:-1]
    x_next = x[..., 2:]
    diff1 = x_curr - x_prev
    diff2 = x_curr - x_next
    peak_valley = (diff1 * diff2 > 0) & ((np.abs(diff1) >= threshold) | (np.abs(diff2) >= threshold))
    return np.sum(peak_valley, axis=axis)


def willison_amplitude(x: np.ndarray, threshold: float = 15.0, axis: int = -1) -> np.ndarray:
    """WAMP: Willison Amplitude (number of times amplitude difference exceeds threshold)."""
    diff = np.abs(np.diff(x, axis=axis))
    return np.sum(diff >= threshold, axis=axis)


def mean_median_frequency(x: np.ndarray, fs: float = 2000.0) -> tuple[np.ndarray, np.ndarray]:
    """Calculate Mean Frequency (MNF) and Median Frequency (MDF) per channel.

    Expects shape (num_channels, n_samples).
    """
    n_channels, n_samples = x.shape
    # FFT along time axis
    fft_vals = np.fft.rfft(x, axis=-1)
    psd = np.abs(fft_vals) ** 2
    freqs = np.fft.rfftfreq(n_samples, 1.0 / fs)

    total_power = np.sum(psd, axis=-1, keepdims=True)
    # Avoid div by zero
    total_power = np.maximum(total_power, 1e-12)

    # MNF: sum(f * P(f)) / sum(P(f))
    mnf = np.sum(psd * freqs, axis=-1) / total_power.squeeze(axis=-1)

    # MDF: frequency where cumulative power reaches 50%
    cum_power = np.cumsum(psd, axis=-1)
    half_power = total_power * 0.5
    mdf = np.zeros(n_channels, dtype=np.float64)
    for ch in range(n_channels):
        idx = np.searchsorted(cum_power[ch], half_power[ch, 0])
        idx = min(idx, len(freqs) - 1)
        mdf[ch] = freqs[idx]

    return mnf, mdf


def extract_features_from_window(
    window: np.ndarray,
    fs: float = 2000.0,
    deadband_uv: float = 10.0,
    feature_set: str = "extended",
) -> np.ndarray:
    """Extract feature vector from a single multi-channel window.

    Args:
        window: np.ndarray of shape (num_channels, n_samples)
        fs: sampling rate in Hz
        deadband_uv: noise rejection deadband in microvolts
        feature_set: 'hudgins' (32 dims for 8ch) or 'extended' (48 dims for 8ch)

    Returns:
        1D float64 feature vector
    """
    mav = mean_absolute_value(window, axis=-1)
    wl = waveform_length(window, axis=-1)
    zc = zero_crossings(window, threshold=deadband_uv, axis=-1)
    ssc = slope_sign_changes(window, threshold=deadband_uv, axis=-1)

    if feature_set == "hudgins":
        # 4 features * n_channels
        return np.concatenate([mav, wl, zc, ssc]).astype(np.float64)

    rms = root_mean_square(window, axis=-1)
    wamp = willison_amplitude(window, threshold=deadband_uv * 1.5, axis=-1)

    # 6 features * n_channels = 48 dimensions for 8 channels
    return np.concatenate([mav, rms, wl, zc, ssc, wamp]).astype(np.float64)


def extract_features_batch(
    windows: np.ndarray,
    fs: float = 2000.0,
    deadband_uv: float = 10.0,
    feature_set: str = "extended",
) -> np.ndarray:
    """Extract features for a batch of windows.

    Args:
        windows: np.ndarray of shape (n_windows, num_channels, n_samples)

    Returns:
        np.ndarray of shape (n_windows, n_features)
    """
    n_windows = windows.shape[0]
    feat_list = [
        extract_features_from_window(windows[i], fs=fs, deadband_uv=deadband_uv, feature_set=feature_set)
        for i in range(n_windows)
    ]
    return np.array(feat_list, dtype=np.float64)
