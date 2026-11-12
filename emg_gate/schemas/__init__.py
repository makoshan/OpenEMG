"""JSON Schema files are the cross-language contract; Python validators mirror them.

`load_schema(name)` returns the parsed schema; `whitelist(name)` returns the
top-level property whitelist so Python validators cannot drift from the JSON.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, FrozenSet

SCHEMA_DIR = Path(__file__).resolve().parent

SCHEMA_NAMES = (
    "capture_session",
    "calibration_profile",
    "cloud_safe_event",
    "paired_window",
    "hardware_profile",
    "commons_manifest",
    "commons_row",
    "commons_model_card",
    "commons_attestation",
)


@lru_cache(maxsize=None)
def load_schema(name: str) -> Dict[str, Any]:
    if name not in SCHEMA_NAMES:
        raise KeyError(f"unknown schema {name!r}; known: {SCHEMA_NAMES}")
    path = SCHEMA_DIR / f"{name}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def whitelist(name: str) -> FrozenSet[str]:
    return frozenset(load_schema(name)["properties"].keys())


def required(name: str) -> FrozenSet[str]:
    return frozenset(load_schema(name)["required"])
