"""Data commons, part 1: same-hardware fingerprint + contribution bundle.

A bundle is what leaves a contributor's machine. It is built from a local
session pack and is pseudonymous by construction:

    <bundle>/manifest.json   CommonsManifest (hardware, pool_key, consent, counts, sha256)
    <bundle>/windows.jsonl   CommonsRow lines (canonical JSON, sorted)

- user_id / device_id / session_id / donning_id / absolute time never appear;
  sessions and donnings are re-labelled s01.. / d01.. per bundle and time is
  relative to the bundle's first window.
- the contributor holds an Ed25519 key in <pack>/commons_identity.json (never
  shared). contributor = "c_" + sha256(pubkey)[:16], so it is a pseudonym not
  derived from user_id. The manifest carries the pubkey and a signature, so any
  replica can check who may withdraw it without asking a server.
- raw_window is copied only when consent.tiers contains "raw".
- verify_bundle() recomputes everything from the files and never trusts the
  manifest's own numbers.

Nothing here uploads. Handing a bundle to a commons is `commons_ledger`.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import statistics
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from . import CHAIN_VERSION, SCHEMA_VERSION, __version__, ed25519
from .capture_session import GESTURE_HARD, GESTURE_LEAD_OFF_NEG, GESTURE_LIGHT, GESTURE_REST, POSITIVE_GESTURES
from .jsonlite import compile_check
from .jsonlite import errors as schema_errors
from .schemas import load_schema
from .session_store import SessionPack, canonical_row

IDENTITY_FILE = "commons_identity.json"
POOL_FIELDS: Tuple[str, ...] = tuple(load_schema("hardware_profile")["x-pool-fields"])
ROW_SCHEMA = load_schema("commons_row")
_ROW_OK = compile_check(ROW_SCHEMA)
POSTURES = frozenset(ROW_SCHEMA["properties"]["posture"]["enum"])
STRAP = frozenset(ROW_SCHEMA["properties"]["strap_nuisance"]["enum"])
FEATURE_KEYS = frozenset(ROW_SCHEMA["properties"]["feature_window"]["properties"])
QUALITY_KEYS = tuple(ROW_SCHEMA["properties"]["quality"]["required"])
DEFAULT_LICENSE = "CDLA-Permissive-2.0"


class CommonsError(Exception):
    """Commons protocol violation (bundle, ledger, snapshot or model)."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(obj: Any) -> bytes:
    return canonical_row(obj).encode("utf-8")


def write_json(path: Path, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------- hardware ----------


def default_hardware(**over: Any) -> Dict[str, Any]:
    """Reference build: ADS1292, 500 Hz, gain 6, gel electrodes on the forearm flexor."""
    hw = {
        "schema_version": SCHEMA_VERSION,
        "family": "emg-ads1292-1ch",
        "afe": "ADS1292",
        "channels": 1,
        "fs_hz": 500.0,
        "gain": 6,
        "electrode": "ag_agcl_gel",
        "placement": "forearm_flexor",
        "chain_ver": CHAIN_VERSION,
        "window_ms": 200.0,
        "hop_ms": 50.0,
        "norm_scale_uV": 200.0,
        "board_rev": "unknown",
        "firmware_build": "unknown",
    }
    hw.update(over)
    return hw


def validate_hardware(hw: Dict[str, Any]) -> None:
    errs = schema_errors(load_schema("hardware_profile"), hw)
    if errs:
        raise CommonsError("hardware profile: " + "; ".join(errs))


def pool_key(hw: Dict[str, Any]) -> str:
    """Only fields that change what a window means; board_rev / firmware_build do not split the pool."""
    validate_hardware(hw)
    return sha256_hex(canonical({f: hw[f] for f in POOL_FIELDS}))[:16]


# ---------- identity / signatures ----------


def contributor_id(pubkey_hex: str) -> str:
    return "c_" + sha256_hex(bytes.fromhex(pubkey_hex))[:16]


def load_or_create_identity(path: Path) -> Dict[str, str]:
    """Local-only Ed25519 key. The pseudonym is derived from the public key, not from user_id."""
    path = Path(path)
    if path.exists():
        ident = read_json(path)
        seed = ident.get("seed", "")
        if len(seed) != 64:
            raise CommonsError(f"bad identity file {path} (needs a 32-byte hex seed)")
        pub = ed25519.public_key(bytes.fromhex(seed)).hex()
        if ident.get("pubkey") != pub or ident.get("contributor") != contributor_id(pub):
            raise CommonsError(f"identity file {path} does not match its own seed")
        return ident
    seed = secrets.token_bytes(32)
    pub = ed25519.public_key(seed).hex()
    ident = {
        "contributor": contributor_id(pub),
        "pubkey": pub,
        "seed": seed.hex(),
        "note": "Local only. Never upload. Signs your bundles, withdrawals and attestations.",
    }
    write_json(path, ident)
    return ident


def _message(purpose: str, body: Dict[str, Any]) -> bytes:
    # Domain separation: a manifest signature can never be replayed as a withdrawal.
    return f"vibe-hw/commons/{purpose}\n".encode() + canonical(body)


def sign_body(ident: Dict[str, str], purpose: str, body: Dict[str, Any]) -> str:
    return ed25519.sign(bytes.fromhex(ident["seed"]), _message(purpose, body)).hex()


def signature_ok(pubkey_hex: str, purpose: str, body: Dict[str, Any], sig_hex: str) -> bool:
    try:
        return ed25519.verify(bytes.fromhex(pubkey_hex), _message(purpose, body), bytes.fromhex(sig_hex))
    except ValueError:
        return False


def bundle_id_for(pk: str, windows_sha: str, contributor: str) -> str:
    return "b_" + sha256_hex(f"{pk}:{windows_sha}:{contributor}".encode())[:16]


def make_withdrawal(ident: Dict[str, str], manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Signed notice that works on any replica, even one that never saw the bundle."""
    if manifest["contributor"] != ident["contributor"]:
        raise CommonsError("this identity did not sign that bundle")
    body = {
        "bundle_id": manifest["bundle_id"],
        "contributor": ident["contributor"],
        "pubkey": ident["pubkey"],
        "pool_key": manifest["pool_key"],
        "windows_sha256": manifest["files"]["windows.jsonl"]["sha256"],
    }
    return {**body, "sig": sign_body(ident, "withdraw", body)}


def verify_withdrawal(notice: Dict[str, Any], *, expected_pool_key: Optional[str] = None) -> List[str]:
    keys = ("bundle_id", "contributor", "pubkey", "pool_key", "windows_sha256", "sig")
    if not isinstance(notice, dict) or set(notice) != set(keys):
        return [f"withdrawal must have exactly {list(keys)}"]
    errs: List[str] = []
    try:
        if notice["contributor"] != contributor_id(notice["pubkey"]):
            errs.append("contributor is not derived from pubkey")
    except ValueError:
        return ["pubkey is not hex"]
    if notice["bundle_id"] != bundle_id_for(notice["pool_key"], notice["windows_sha256"], notice["contributor"]):
        errs.append("bundle_id does not belong to this contributor")
    if expected_pool_key and notice["pool_key"] != expected_pool_key:
        errs.append("withdrawal is for another pool")
    body = {k: notice[k] for k in keys if k != "sig"}
    if not signature_ok(notice["pubkey"], "withdraw", body, notice["sig"]):
        errs.append("withdrawal signature does not verify")
    return errs


# ---------- rows ----------


def is_clean(row: Dict[str, Any]) -> bool:
    """Same qualification as splits.clean_windows / session_store coverage."""
    q = row.get("quality") or {}
    g = row.get("gesture_label")
    if g == GESTURE_LEAD_OFF_NEG:
        return bool(q.get("lead_off")) and not any(q.get(k) for k in QUALITY_KEYS if k != "lead_off")
    if g in POSITIVE_GESTURES:
        return not any(q.get(k) for k in QUALITY_KEYS)
    return False


def band_order_issue(rows: Iterable[Dict[str, Any]]) -> str:
    """'' when clean medians order rest < light < hard, else the reason.

    Catches swapped labels, an electrode on the wrong muscle, or poisoning by
    label flipping. It does not catch data that is ordered but scaled wrong.
    """
    rows = list(rows)
    med: Dict[str, float] = {}
    for g in (GESTURE_REST, GESTURE_LIGHT, GESTURE_HARD):
        norms = [r["feature_window"]["norm"] for r in rows if r["gesture_label"] == g and is_clean(r)]
        if len(norms) < 3:
            return f"fewer than 3 clean {g} windows"
        med[g] = float(statistics.median(norms))
    if not med[GESTURE_REST] < med[GESTURE_LIGHT] < med[GESTURE_HARD]:
        return "band order violated: median norm " + ", ".join(f"{g}={v:.3f}" for g, v in med.items())
    return ""


def clean_seconds(rows: Iterable[Dict[str, Any]]) -> Dict[str, float]:
    """Per-gesture union of clean windows, per (session) so overlapping hops count once."""
    spans: Dict[str, Dict[str, List[Tuple[float, float]]]] = {}
    for r in rows:
        if is_clean(r):
            start = float(r["t_ms"])
            spans.setdefault(r["gesture_label"], {}).setdefault(r["session"], []).append(
                (start, start + float(r["window_ms"]))
            )
    out: Dict[str, float] = {}
    for g, by_session in spans.items():
        total = 0.0
        for iv in by_session.values():
            cur_s: Optional[float] = None
            cur_e = 0.0
            for s, e in sorted(iv):
                if cur_s is None:
                    cur_s, cur_e = s, e
                elif s <= cur_e:
                    cur_e = max(cur_e, e)
                else:
                    total += cur_e - cur_s
                    cur_s, cur_e = s, e
            if cur_s is not None:
                total += cur_e - cur_s
        out[g] = round(total / 1000.0, 3)
    return dict(sorted(out.items()))


def _commons_row(
    row: Dict[str, Any], session: str, donning: str, t0: float, with_raw: bool
) -> Optional[Dict[str, Any]]:
    feature = row.get("feature_window") or {}
    if "norm" not in feature:
        return None
    out: Dict[str, Any] = {
        "session": session,
        "donning": donning,
        "gesture_label": row["gesture_label"],
        "t_ms": round(float(row["obs_ts_device_ms"]) - t0, 3),
        "fs_hz": float(row["fs_hz"]),
        "window_ms": float(row["window_ms"]),
        "feature_window": {k: feature[k] for k in sorted(FEATURE_KEYS) if k in feature},
        "quality": {k: bool(row["quality"].get(k, False)) for k in QUALITY_KEYS},
        "held_out": bool(row.get("held_out", False)),
    }
    ctx = row.get("context") or {}
    if ctx.get("posture_tag") in POSTURES:
        out["posture"] = ctx["posture_tag"]
    if ctx.get("strap_nuisance") in STRAP:
        out["strap_nuisance"] = ctx["strap_nuisance"]
    if with_raw and row.get("raw_window") is not None:
        out["raw_window"] = [float(x) for x in row["raw_window"]]
    return out


def _rows_blob(rows: List[Dict[str, Any]]) -> bytes:
    lines = [canonical_row(r) for r in rows]
    return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")


def _row_key(r: Dict[str, Any]) -> Tuple[float, str, str]:
    return (float(r["t_ms"]), r["session"], r["gesture_label"])


# ---------- build ----------


def build_bundle(
    pack_root: Path,
    out_dir: Path,
    hardware: Dict[str, Any],
    *,
    tiers: Sequence[str] = ("features",),
    license: str = DEFAULT_LICENSE,
    identity_path: Optional[Path] = None,
    granted_on: Optional[str] = None,
) -> Dict[str, Any]:
    """Local pack → pseudonymous bundle. Returns the manifest."""
    pk = pool_key(hardware)
    pack = SessionPack.open(pack_root)
    src_rows = pack.load_windows()
    if not src_rows:
        raise CommonsError(f"pack {pack_root} has no windows")

    sources = {r.get("source", "recorded") for r in src_rows}
    if len(sources) != 1:
        raise CommonsError(f"pack mixes sources {sorted(sources)}; bundle one source at a time")
    for r in src_rows:
        if float(r["fs_hz"]) != float(hardware["fs_hz"]) or float(r["window_ms"]) != float(hardware["window_ms"]):
            raise CommonsError(
                f"window fs/window_ms {r['fs_hz']}/{r['window_ms']} does not match hardware "
                f"{hardware['fs_hz']}/{hardware['window_ms']}"
            )

    # Re-label by first appearance in time, so labels carry no ids or dates.
    first_seen: Dict[str, float] = {}
    donning_first: Dict[str, float] = {}
    for r in src_rows:
        t = float(r["obs_ts_device_ms"])
        first_seen[r["session_id"]] = min(t, first_seen.get(r["session_id"], t))
        donning_first[r["donning_id"]] = min(t, donning_first.get(r["donning_id"], t))
    s_map = {sid: f"s{i + 1:02d}" for i, sid in enumerate(sorted(first_seen, key=lambda s: (first_seen[s], s)))}
    d_map = {did: f"d{i + 1:02d}" for i, did in enumerate(sorted(donning_first, key=lambda d: (donning_first[d], d)))}
    t0 = min(first_seen.values())

    with_raw = "raw" in tiers
    rows = [
        cr
        for r in src_rows
        if (cr := _commons_row(r, s_map[r["session_id"]], d_map[r["donning_id"]], t0, with_raw)) is not None
    ]
    if not rows:
        raise CommonsError("no window carries feature_window.norm; nothing to share")
    rows.sort(key=_row_key)
    blob = _rows_blob(rows)
    windows_sha = sha256_hex(blob)

    ident = load_or_create_identity(identity_path or Path(pack_root) / IDENTITY_FILE)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": bundle_id_for(pk, windows_sha, ident["contributor"]),
        "contributor": ident["contributor"],
        "pubkey": ident["pubkey"],
        "hardware": hardware,
        "pool_key": pk,
        "consent": {
            "version": "commons-consent-v1",
            "tiers": sorted(set(tiers)),
            "license": license,
            "allow_model_training": True,
            "granted_on": granted_on or time.strftime("%Y-%m-%d", time.gmtime()),
        },
        "source": sources.pop(),
        "counts": _counts(rows),
        "files": {"windows.jsonl": {"sha256": windows_sha, "bytes": len(blob)}},
        "tool": {"emg_gate": __version__},
    }
    manifest["sig"] = sign_body(ident, "manifest", manifest)
    errs = schema_errors(load_schema("commons_manifest"), manifest)
    if errs:
        raise CommonsError("manifest: " + "; ".join(errs))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "windows.jsonl").write_bytes(blob)
    write_json(out_dir / "manifest.json", manifest)
    return manifest


def _counts(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "n_rows": len(rows),
        "n_sessions": len({r["session"] for r in rows}),
        "n_donnings": len({r["donning"] for r in rows}),
        "clean_seconds": clean_seconds(rows),
        "has_raw": any("raw_window" in r for r in rows),
    }


# ---------- verify ----------


def read_rows(bundle_dir: Path) -> List[Dict[str, Any]]:
    text = (Path(bundle_dir) / "windows.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def verify_bundle(
    bundle_dir: Path,
    *,
    expected_pool_key: Optional[str] = None,
    expected_license: Optional[str] = None,
) -> Dict[str, Any]:
    """Recompute a bundle from its files. Returns {ok, errors, manifest, rows}."""
    bundle_dir = Path(bundle_dir)
    errs: List[str] = []
    report: Dict[str, Any] = {"ok": False, "errors": errs, "manifest": None, "rows": []}
    try:
        manifest = read_json(bundle_dir / "manifest.json")
        blob = (bundle_dir / "windows.jsonl").read_bytes()
    except (OSError, ValueError) as e:
        errs.append(f"unreadable bundle: {e}")
        return report
    report["manifest"] = manifest
    errs.extend(schema_errors(load_schema("commons_manifest"), manifest))
    if errs:
        return report

    try:
        pk = pool_key(manifest["hardware"])
    except CommonsError as e:
        errs.append(str(e))
        return report
    if pk != manifest["pool_key"]:
        errs.append(f"pool_key {manifest['pool_key']} does not match hardware ({pk})")
    if expected_pool_key and pk != expected_pool_key:
        errs.append(f"hardware pool {pk} is not this commons' pool {expected_pool_key}")
    if expected_license and manifest["consent"]["license"] != expected_license:
        errs.append(f"license {manifest['consent']['license']} is not this commons' {expected_license}")

    fmeta = manifest["files"]["windows.jsonl"]
    if sha256_hex(blob) != fmeta["sha256"] or len(blob) != fmeta["bytes"]:
        errs.append("windows.jsonl sha256/bytes do not match manifest (tampered or truncated)")
    if manifest["bundle_id"] != bundle_id_for(pk, fmeta["sha256"], manifest["contributor"]):
        errs.append("bundle_id is not derived from pool_key + windows sha256 + contributor")
    if manifest["contributor"] != contributor_id(manifest["pubkey"]):
        errs.append("contributor is not derived from pubkey")
    unsigned = {k: v for k, v in manifest.items() if k != "sig"}
    if not signature_ok(manifest["pubkey"], "manifest", unsigned, manifest["sig"]):
        errs.append("manifest signature does not verify (edited after signing, or signed by another key)")

    try:
        rows = [json.loads(line) for line in blob.decode("utf-8").splitlines() if line.strip()]
    except ValueError as e:
        errs.append(f"windows.jsonl is not JSON lines: {e}")
        return report
    raw_ok = "raw" in manifest["consent"]["tiers"]
    hw = manifest["hardware"]
    for i, r in enumerate(rows):
        row_errs = [] if _ROW_OK(r) else schema_errors(ROW_SCHEMA, r, f"row[{i}]")
        if "raw_window" in r and not raw_ok:
            row_errs.append(f"row[{i}]: raw_window without raw-tier consent")
        if isinstance(r, dict) and (r.get("fs_hz") != hw["fs_hz"] or r.get("window_ms") != hw["window_ms"]):
            row_errs.append(f"row[{i}]: fs_hz/window_ms differ from hardware profile")
        errs.extend(row_errs[:3])
        if len(errs) > 20:
            errs.append("... more row errors truncated")
            return report
    if errs:
        return report
    if [_row_key(r) for r in rows] != sorted(_row_key(r) for r in rows):
        errs.append("rows are not in canonical order")
    counts = _counts(rows)
    if counts != manifest["counts"]:
        errs.append(f"manifest counts {manifest['counts']} differ from recomputed {counts}")

    report["rows"] = rows
    report["ok"] = not errs
    return report
