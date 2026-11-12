"""Data commons, part 2: replicas, hash-chained local log, contributor-level snapshots.

A commons is a *replica*: any number of people can hold one, and nobody's
copy is the master. Layout (one pool = one hardware pool_key):

    <root>/commons.json                    pool_key, hardware, licenses, policy (local choice)
    <root>/ledger.jsonl                    this replica's append-only log (hash chain)
    <root>/bundles/<bundle_id>/            signed, content-addressed bundles
    <root>/withdrawals/<bundle_id>.json    signed withdrawal notices (kept forever)
    <root>/attestations/<model_id>/<c>.json  signed local-evaluation results
    <root>/snapshots/<snapshot_id>.json

What is shared between replicas is only self-verifying objects: bundles
(hash + Ed25519 signature), withdrawal notices and attestations (signature).
`merge` pulls them from another replica and re-verifies every one. The local
ledger is an audit log, not the source of truth, so two replicas that hold
the same objects compute the same snapshot_id and the same model_id no
matter in which order they received them.

Rules:
- a bundle enters only after verify_bundle() against this pool and license,
  and with enough clean seconds per force band
- a withdrawal notice is signed by the bundle's key and names pool_key +
  windows sha256, so any replica can check it even without the bundle; files
  are deleted, the id can never come back, and every snapshot that used the
  bundle becomes stale
- a snapshot first quarantines contributors whose clean windows do not order
  rest < light < hard (band_order_issue), then splits the rest by
  *contributor*: nobody is in both train and test
- one contributor may hold at most policy.max_contributor_share of the
  training windows; extra windows are thinned by a fixed stride
- recorded and synthetic bundles never share a snapshot
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import SCHEMA_VERSION
from .capture_session import GESTURE_HARD, GESTURE_LIGHT, GESTURE_REST
from .commons_bundle import (
    DEFAULT_LICENSE,
    CommonsError,
    band_order_issue,
    canonical,
    is_clean,
    pool_key,
    read_json,
    read_rows,
    sha256_hex,
    verify_bundle,
    verify_withdrawal,
    write_json,
)
from .commons_attest import verify_attestation

MODEL_LICENSE = "Apache-2.0"
DEFAULT_POLICY: Dict[str, Any] = {
    "max_contributor_share": 0.5,
    "test_fraction": 0.25,
    "min_contributors": 4,
    "min_clean_seconds": 30.0,
    "min_accuracy": 0.8,
}
FORCE_BANDS = (GESTURE_REST, GESTURE_LIGHT, GESTURE_HARD)
GENESIS = "0" * 64


def _entry_hash(entry: Dict[str, Any]) -> str:
    return sha256_hex(canonical({k: entry[k] for k in ("seq", "prev", "kind", "body", "at")}))


class Commons:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.meta_path = self.root / "commons.json"
        self.ledger_path = self.root / "ledger.jsonl"
        self.bundles_dir = self.root / "bundles"
        self.snapshots_dir = self.root / "snapshots"
        self.models_dir = self.root / "models"
        self.withdrawals_dir = self.root / "withdrawals"
        self.attestations_dir = self.root / "attestations"

    # ---------- lifecycle ----------

    @classmethod
    def init(
        cls,
        root: Path,
        hardware: Dict[str, Any],
        *,
        data_license: str = DEFAULT_LICENSE,
        policy: Optional[Dict[str, Any]] = None,
    ) -> "Commons":
        c = cls(root)
        if c.meta_path.exists():
            raise CommonsError(f"commons already exists at {c.root}")
        pk = pool_key(hardware)
        pol = {**DEFAULT_POLICY, **(policy or {})}
        if pol["max_contributor_share"] * (pol["min_contributors"] - _n_test(pol["min_contributors"], pol)) < 1:
            raise CommonsError("policy: max_contributor_share × train contributors < 1 cannot be met")
        write_json(
            c.meta_path,
            {
                "schema_version": SCHEMA_VERSION,
                "pool_key": pk,
                "hardware": hardware,
                "data_license": data_license,
                "model_license": MODEL_LICENSE,
                "policy": pol,
            },
        )
        c.root.mkdir(parents=True, exist_ok=True)
        c._append("init", {"pool_key": pk, "data_license": data_license, "policy": pol})
        return c

    @classmethod
    def open(cls, root: Path) -> "Commons":
        c = cls(root)
        if not c.meta_path.exists():
            raise CommonsError(f"no commons.json under {c.root}")
        return c

    @property
    def meta(self) -> Dict[str, Any]:
        return read_json(self.meta_path)

    @property
    def policy(self) -> Dict[str, Any]:
        return self.meta["policy"]

    # ---------- ledger ----------

    def entries(self) -> List[Dict[str, Any]]:
        """Parsed ledger, cached on the file's sha256 so a long ledger is not re-parsed per call.

        The key is the content hash, not size/mtime: an edit that keeps the
        length and lands in the same timestamp tick must still be seen.
        """
        if not self.ledger_path.exists():
            return []
        data = self.ledger_path.read_bytes()
        key = hashlib.sha256(data).digest()
        cached = getattr(self, "_entries_cache", None)
        if cached is None or cached[0] != key:
            cached = (key, [json.loads(l) for l in data.decode("utf-8").splitlines() if l.strip()])
            self._entries_cache = cached
        return list(cached[1])

    def _append(self, kind: str, body: Dict[str, Any]) -> Dict[str, Any]:
        entries = self.entries()
        entry = {
            "seq": len(entries),
            "prev": entries[-1]["hash"] if entries else GENESIS,
            "kind": kind,
            "body": body,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        entry["hash"] = _entry_hash(entry)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("ab") as f:
            f.write(canonical(entry) + b"\n")
        self._entries_cache = (hashlib.sha256(self.ledger_path.read_bytes()).digest(), entries + [entry])
        return entry

    def verify_ledger(self) -> List[str]:
        """Chain breaks, edited entries, or a pool that differs from commons.json."""
        errs: List[str] = []
        prev = GENESIS
        for i, e in enumerate(self.entries()):
            if e.get("seq") != i:
                errs.append(f"entry {i}: seq {e.get('seq')} out of order")
            if e.get("prev") != prev:
                errs.append(f"entry {i}: prev hash does not chain")
            if e.get("hash") != _entry_hash(e):
                errs.append(f"entry {i}: hash does not match content (edited)")
            prev = e.get("hash")
        entries = self.entries()
        if not entries or entries[0]["kind"] != "init":
            errs.append("ledger does not start with init")
        elif entries[0]["body"]["pool_key"] != self.meta["pool_key"]:
            errs.append("commons.json pool_key differs from the ledger's init entry")
        return errs

    def state(self) -> Dict[str, Any]:
        """Replay: active bundles, withdrawn bundles, snapshots, released models."""
        active: Dict[str, Dict[str, Any]] = {}
        withdrawn: Dict[str, int] = {}
        snapshots: Dict[str, Dict[str, Any]] = {}
        models: Dict[str, Dict[str, Any]] = {}
        for e in self.entries():
            b = e["body"]
            if e["kind"] == "contribute":
                active[b["bundle_id"]] = b
            elif e["kind"] == "withdraw":
                active.pop(b["bundle_id"], None)
                withdrawn[b["bundle_id"]] = e["seq"]
            elif e["kind"] == "snapshot":
                snapshots[b["snapshot_id"]] = {**b, "seq": e["seq"]}
            elif e["kind"] == "model":
                models[b["model_id"]] = b
        return {"active": active, "withdrawn": withdrawn, "snapshots": snapshots, "models": models}

    # ---------- contribute / withdraw ----------

    def contribute(self, bundle_dir: Path) -> Dict[str, Any]:
        meta = self.meta
        rep = verify_bundle(bundle_dir, expected_pool_key=meta["pool_key"], expected_license=meta["data_license"])
        if not rep["ok"]:
            raise CommonsError("bundle rejected: " + "; ".join(rep["errors"]))
        man = rep["manifest"]
        st = self.state()
        if man["bundle_id"] in st["withdrawn"] or (self.withdrawals_dir / f"{man['bundle_id']}.json").exists():
            raise CommonsError(f"bundle {man['bundle_id']} was withdrawn by its contributor; it cannot come back")
        if man["bundle_id"] in st["active"]:
            raise CommonsError(f"bundle {man['bundle_id']} already contributed")
        short = {
            g: man["counts"]["clean_seconds"].get(g, 0.0)
            for g in FORCE_BANDS
            if man["counts"]["clean_seconds"].get(g, 0.0) < self.policy["min_clean_seconds"]
        }
        if short:
            raise CommonsError(f"bundle rejected: clean seconds below {self.policy['min_clean_seconds']:g}: {short}")
        dest = self.bundles_dir / man["bundle_id"]
        dest.mkdir(parents=True, exist_ok=True)
        for name in ("manifest.json", "windows.jsonl"):
            shutil.copyfile(Path(bundle_dir) / name, dest / name)
        body = {
            "bundle_id": man["bundle_id"],
            "contributor": man["contributor"],
            "windows_sha256": man["files"]["windows.jsonl"]["sha256"],
            "source": man["source"],
            "tiers": man["consent"]["tiers"],
            "clean_seconds": man["counts"]["clean_seconds"],
        }
        self._append("contribute", body)
        return body

    def withdraw(self, notice: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a signed withdrawal notice (see commons_bundle.make_withdrawal)."""
        errs = verify_withdrawal(notice, expected_pool_key=self.meta["pool_key"])
        if errs:
            raise CommonsError("withdrawal rejected: " + "; ".join(errs))
        bid = notice["bundle_id"]
        st = self.state()
        if bid in st["withdrawn"]:
            return {"bundle_id": bid, "already": True}
        if bid in st["active"] and st["active"][bid]["contributor"] != notice["contributor"]:
            raise CommonsError("withdrawal rejected: signer is not this bundle's contributor")
        write_json(self.withdrawals_dir / f"{bid}.json", notice)
        if (self.bundles_dir / bid).exists():
            shutil.rmtree(self.bundles_dir / bid)
        stale = sorted(s for s, snap in st["snapshots"].items() if bid in snap["bundles"])
        body = {"bundle_id": bid, "contributor": notice["contributor"], "stales_snapshots": stale,
                "was_active": bid in st["active"]}
        self._append("withdraw", body)
        return body

    # ---------- attestations ----------

    def add_attestation(self, att: Dict[str, Any]) -> bool:
        """Store a signed local-evaluation result. False when an equal or newer one is already here."""
        errs = verify_attestation(att, expected_pool_key=self.meta["pool_key"])
        if errs:
            raise CommonsError("attestation rejected: " + "; ".join(errs))
        path = self.attestations_dir / att["model_id"] / f"{att['contributor']}.json"
        if path.exists():
            old = read_json(path)
            if (old["made_on"], old["sig"]) >= (att["made_on"], att["sig"]):
                return False
        write_json(path, att)
        self._append("attest", {"model_id": att["model_id"], "contributor": att["contributor"],
                                "sig": att["sig"]})
        return True

    def attestations(self, model_id: str) -> List[Dict[str, Any]]:
        return [read_json(p) for p in sorted((self.attestations_dir / model_id).glob("*.json"))]

    # ---------- replicas ----------

    def merge(self, other_root: Path) -> Dict[str, Any]:
        """Pull withdrawals, bundles and attestations from another replica; re-verify all of them."""
        other = Commons.open(other_root)
        if other.meta["pool_key"] != self.meta["pool_key"]:
            raise CommonsError(f"other replica is pool {other.meta['pool_key']}, this is {self.meta['pool_key']}")
        report: Dict[str, Any] = {"withdrawn": [], "added": [], "attestations": 0, "skipped": {}}
        for p in sorted(other.withdrawals_dir.glob("*.json")):
            try:
                if not self.withdraw(read_json(p)).get("already"):
                    report["withdrawn"].append(p.stem)
            except (CommonsError, ValueError) as e:
                report["skipped"][p.name] = str(e)
        st = self.state()
        for d in sorted(other.bundles_dir.glob("b_*")):
            if d.name in st["active"] or d.name in st["withdrawn"]:
                continue
            try:
                self.contribute(d)
                report["added"].append(d.name)
            except CommonsError as e:
                report["skipped"][d.name] = str(e)
        for p in sorted(other.attestations_dir.glob("*/*.json")):
            try:
                report["attestations"] += int(self.add_attestation(read_json(p)))
            except (CommonsError, ValueError) as e:
                report["skipped"][f"{p.parent.name}/{p.name}"] = str(e)
        return report

    # ---------- snapshots ----------

    def snapshot(self) -> Dict[str, Any]:
        st = self.state()
        pol = self.policy
        if not st["active"]:
            raise CommonsError("no active bundles")
        sources = {b["source"] for b in st["active"].values()}
        if len(sources) != 1:
            raise CommonsError(f"active bundles mix sources {sorted(sources)}; recorded and synthetic never share a snapshot")
        by_contrib: Dict[str, List[str]] = {}
        for bid, b in sorted(st["active"].items()):
            by_contrib.setdefault(b["contributor"], []).append(bid)
        rows = {c: [r for bid in bids for r in read_rows(self.bundles_dir / bid)] for c, bids in by_contrib.items()}
        # Screen before splitting, so a mislabelled contributor can neither train nor fill the test set.
        quarantined = [
            {"contributor": c, "reason": issue} for c in sorted(rows) if (issue := band_order_issue(rows[c]))
        ]
        out = {q["contributor"] for q in quarantined}
        contributors = sorted((c for c in by_contrib if c not in out), key=lambda c: (sha256_hex(c.encode()), c))
        if len(contributors) < pol["min_contributors"]:
            raise CommonsError(
                f"{len(contributors)} eligible contributors < policy.min_contributors {pol['min_contributors']}"
                + (f" ({len(out)} quarantined)" if out else "")
            )
        n_test = _n_test(len(contributors), pol)
        test, train = sorted(contributors[:n_test]), sorted(contributors[n_test:])

        clean_counts = {c: sum(1 for r in rows[c] if is_clean(r)) for c in train}
        cap = _share_cap(clean_counts, pol["max_contributor_share"])
        body = {
            "pool_key": self.meta["pool_key"],
            "source": sources.pop(),
            "bundles": sorted(st["active"]),
            "windows_sha256": {bid: st["active"][bid]["windows_sha256"] for bid in sorted(st["active"])},
            "train": train,
            "test": test,
            "bundle_contributor": {bid: st["active"][bid]["contributor"] for bid in sorted(st["active"])},
            "quarantined": quarantined,
            "train_cap": cap,
            "train_clean_counts": clean_counts,
            "policy": pol,
        }
        body = {"snapshot_id": "s_" + sha256_hex(canonical(body))[:16], **body}
        write_json(self.snapshots_dir / f"{body['snapshot_id']}.json", body)
        self._append("snapshot", {k: body[k] for k in ("snapshot_id", "pool_key", "source", "bundles", "train", "test", "quarantined", "train_cap")})
        return body

    def load_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        path = self.snapshots_dir / f"{snapshot_id}.json"
        if not path.exists():
            raise CommonsError(f"unknown snapshot {snapshot_id}")
        return read_json(path)

    def snapshot_issues(self, snapshot_id: str) -> List[str]:
        """Why a snapshot can no longer back a model: stale, leaked, tampered, missing."""
        st = self.state()
        if snapshot_id not in st["snapshots"]:
            return [f"snapshot {snapshot_id} is not in the ledger"]
        snap = self.load_snapshot(snapshot_id)
        errs: List[str] = []
        body = {k: v for k, v in snap.items() if k != "snapshot_id"}
        if "s_" + sha256_hex(canonical(body))[:16] != snapshot_id:
            errs.append("snapshot file does not hash to its id (edited)")
        gone = sorted(b for b in snap["bundles"] if b in st["withdrawn"])
        if gone:
            errs.append(f"stale: bundles withdrawn since snapshot: {gone}")
        leak = sorted(set(snap["train"]) & set(snap["test"]))
        if leak:
            errs.append(f"contributor leak: in both train and test: {leak}")
        for bid in snap["bundles"]:
            if bid in gone:
                continue
            p = self.bundles_dir / bid / "windows.jsonl"
            if not p.exists():
                errs.append(f"bundle {bid} files missing")
            elif sha256_hex(p.read_bytes()) != snap["windows_sha256"][bid]:
                errs.append(f"bundle {bid} windows changed since snapshot")
        return errs

    def snapshot_rows(self, snapshot_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
        """(train rows after the share cap, {test contributor: rows}). Rows are tagged with contributor."""
        errs = self.snapshot_issues(snapshot_id)
        if errs:
            raise CommonsError("; ".join(errs))
        snap = self.load_snapshot(snapshot_id)
        per: Dict[str, List[Dict[str, Any]]] = {}
        for bid in snap["bundles"]:
            c = snap["bundle_contributor"][bid]
            per.setdefault(c, []).extend({**r, "contributor": c} for r in read_rows(self.bundles_dir / bid))
        train: List[Dict[str, Any]] = []
        for c in snap["train"]:
            clean = [r for r in per.get(c, []) if is_clean(r)]
            keep = min(len(clean), snap["train_cap"])
            train.extend(clean[(j * len(clean)) // keep] for j in range(keep))
        test = {c: per.get(c, []) for c in snap["test"]}
        return train, test


def _n_test(n: int, pol: Dict[str, Any]) -> int:
    return max(1, int(math.floor(n * pol["test_fraction"] + 0.5)))


def _share_cap(counts: Dict[str, int], share: float) -> int:
    """Largest per-contributor window cap c with min(n_i, c) <= share × Σ min(n_j, c) for all i."""
    if not counts:
        raise CommonsError("no training contributors")
    c = max(counts.values())
    while True:
        total = sum(min(n, c) for n in counts.values())
        limit = int(math.floor(share * total + 1e-9))
        if all(min(n, c) <= limit for n in counts.values()):
            return c
        if limit < 1:
            raise CommonsError(f"cannot cap contributors at share {share} with counts {counts}")
        c = limit
