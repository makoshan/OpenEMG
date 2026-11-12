"""Data commons over git: an exchange repo that holds only self-verifying objects.

Layout of the shared repo (every path is named by content, so two people
adding different objects never touch the same file and git merges are clean):

    commons.json                          pool_key, hardware, data_license, format
    LICENSE                               the data license text (CDLA-Permissive-2.0 requires it)
    bundles/<bundle_id>/manifest.json     signed bundle
    bundles/<bundle_id>/windows.jsonl
    withdrawals/<bundle_id>.json          signed withdrawal; the bundle dir is removed
    attestations/<model_id>/<c>.json      signed local-evaluation result
    README.md, .gitattributes, .github/   optional, not data

Nothing else is allowed in: no identity files, snapshots, models or local
ledgers. `verify_repo` enforces the layout and re-verifies every object, so
the shared repo's own CI can run it on every pull request.

`git_sync` = pull (merge, if a remote exists) → import (merge into the local
replica, re-verifying) → export → verify → commit. It pushes only when
asked. The local ledger, snapshots and models stay in the replica.
"""

from __future__ import annotations

import filecmp
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import SCHEMA_VERSION
from .commons_attest import verify_attestation
from .commons_bundle import CommonsError, read_json, verify_bundle, verify_withdrawal, write_json
from .commons_ledger import Commons

FORMAT = "vibe-hw-commons-exchange/1"
LICENSE_DIR = Path(__file__).resolve().parent / "licenses"
_ALLOWED = [
    re.compile(p)
    for p in (
        r"^commons\.json$",
        r"^LICENSE$",
        r"^README\.md$",
        r"^\.gitattributes$",
        r"^\.github/.+$",
        r"^bundles/b_[0-9a-f]{16}/(manifest\.json|windows\.jsonl)$",
        r"^withdrawals/b_[0-9a-f]{16}\.json$",
        r"^attestations/m_[0-9a-f]{16}/c_[0-9a-f]{16}\.json$",
    )
]


def license_text(name: str) -> str:
    path = LICENSE_DIR / f"{name}.txt"
    if not path.exists():
        raise CommonsError(f"no license text shipped for {name}; the exchange repo must carry it")
    return path.read_text(encoding="utf-8")


def _files(repo: Path) -> List[str]:
    return sorted(
        p.relative_to(repo).as_posix()
        for p in repo.rglob("*")
        if p.is_file() and ".git" not in p.relative_to(repo).parts[:1]
    )


def _copy_if_changed(src: Path, dst: Path) -> bool:
    if dst.exists() and filecmp.cmp(src, dst, shallow=False):
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return True


def export_objects(commons: Commons, repo: Path) -> Dict[str, Any]:
    """Write this replica's shareable objects into the exchange repo's working tree."""
    repo = Path(repo)
    meta = commons.meta
    head = {
        "schema_version": SCHEMA_VERSION,
        "format": FORMAT,
        "pool_key": meta["pool_key"],
        "hardware": meta["hardware"],
        "data_license": meta["data_license"],
    }
    if (repo / "commons.json").exists():
        theirs = read_json(repo / "commons.json")
        if theirs.get("pool_key") != head["pool_key"] or theirs.get("data_license") != head["data_license"]:
            raise CommonsError(
                f"repo is pool {theirs.get('pool_key')} / {theirs.get('data_license')}, "
                f"this replica is {head['pool_key']} / {head['data_license']}"
            )
    else:
        write_json(repo / "commons.json", head)
    lic = repo / "LICENSE"
    text = license_text(meta["data_license"])
    if not lic.exists() or lic.read_text(encoding="utf-8") != text:
        lic.write_text(text, encoding="utf-8")

    st = commons.state()
    report = {"bundles": 0, "withdrawals": 0, "removed": 0, "attestations": 0}
    for bid in sorted(st["active"]):
        changed = [
            _copy_if_changed(commons.bundles_dir / bid / name, repo / "bundles" / bid / name)
            for name in ("manifest.json", "windows.jsonl")
        ]
        report["bundles"] += any(changed)
    for p in sorted(commons.withdrawals_dir.glob("*.json")):
        report["withdrawals"] += _copy_if_changed(p, repo / "withdrawals" / p.name)
        if (repo / "bundles" / p.stem).exists():
            shutil.rmtree(repo / "bundles" / p.stem)
            report["removed"] += 1
    for p in sorted(commons.attestations_dir.glob("*/*.json")):
        dst = repo / "attestations" / p.parent.name / p.name
        if dst.exists():
            ours, theirs = read_json(p), read_json(dst)
            if (theirs["made_on"], theirs["sig"]) >= (ours["made_on"], ours["sig"]):
                continue
        report["attestations"] += _copy_if_changed(p, dst)
    return report


def verify_repo(repo: Path) -> List[str]:
    """Every error that should stop a commit to, or a pull request against, the shared repo."""
    repo = Path(repo)
    errs: List[str] = []
    try:
        head = read_json(repo / "commons.json")
    except (OSError, ValueError) as e:
        return [f"commons.json unreadable: {e}"]
    if head.get("format") != FORMAT:
        errs.append(f"commons.json format is not {FORMAT}")
    pk, lic = head.get("pool_key"), head.get("data_license")
    try:
        if (repo / "LICENSE").read_text(encoding="utf-8") != license_text(lic):
            errs.append(f"LICENSE is not the {lic} text")
    except (OSError, CommonsError) as e:
        errs.append(f"LICENSE: {e}")

    for rel in _files(repo):
        if not any(p.match(rel) for p in _ALLOWED):
            errs.append(f"not allowed in the exchange repo: {rel}")
        if rel.endswith(".json") and not rel.startswith(".github/"):
            try:
                obj = json.loads((repo / rel).read_text(encoding="utf-8"))
            except ValueError:
                errs.append(f"{rel}: not JSON")
                continue
            if isinstance(obj, dict) and ("seed" in obj or "withdraw_secret" in obj):
                errs.append(f"{rel}: looks like a private identity file; never commit it")

    withdrawn = set()
    for p in sorted((repo / "withdrawals").glob("*.json")):
        try:
            notice = read_json(p)
        except ValueError:
            continue  # already reported as "not JSON" above
        e = verify_withdrawal(notice, expected_pool_key=pk)
        if isinstance(notice, dict) and p.stem != notice.get("bundle_id"):
            e.append("file name is not its bundle_id")
        errs.extend(f"withdrawals/{p.name}: {x}" for x in e)
        withdrawn.add(p.stem)
    for d in sorted((repo / "bundles").glob("*")):
        if d.name in withdrawn:
            errs.append(f"bundles/{d.name}: present although its contributor withdrew it")
            continue
        rep = verify_bundle(d, expected_pool_key=pk, expected_license=lic)
        errs.extend(f"bundles/{d.name}: {x}" for x in rep["errors"])
        if rep["manifest"] and rep["manifest"].get("bundle_id") != d.name:
            errs.append(f"bundles/{d.name}: directory name is not its bundle_id")
    for p in sorted((repo / "attestations").glob("*/*.json")):
        try:
            att = read_json(p)
        except ValueError:
            continue
        e = verify_attestation(att, expected_pool_key=pk)
        if not e and (att["model_id"] != p.parent.name or att["contributor"] != p.stem):
            e.append("path does not match model_id / contributor")
        errs.extend(f"attestations/{p.parent.name}/{p.name}: {x}" for x in e)
    return errs


def _git(repo: Path, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=os.environ.copy()
        )
    except subprocess.CalledProcessError as e:
        raise CommonsError(f"git {' '.join(args)} failed: {(e.stderr or e.stdout).strip()}") from e
    return out.stdout


def git_sync(commons: Commons, repo: Path, *, push: bool = False, message: Optional[str] = None) -> Dict[str, Any]:
    """Pull → import → export → verify → commit (→ push only when asked)."""
    repo = Path(repo)
    if not (repo / ".git").exists():
        raise CommonsError(f"{repo} is not a git working tree; clone the shared commons repo first")
    has_remote = bool(_git(repo, "remote").strip())
    if has_remote and _git(repo, "ls-remote", "--heads", "origin").strip():
        _git(repo, "pull", "--no-rebase", "--no-edit", "origin", _git(repo, "branch", "--show-current").strip())
    imported: Dict[str, Any] = {"withdrawn": [], "added": [], "attestations": 0, "skipped": {}}
    if (repo / "commons.json").exists():
        imported = commons.merge(repo)
    exported = export_objects(commons, repo)
    errs = verify_repo(repo)
    if errs:
        raise CommonsError("refusing to commit, exchange repo does not verify: " + "; ".join(errs[:10]))
    _git(repo, "add", "-A")
    committed = bool(_git(repo, "status", "--porcelain").strip())
    if committed:
        msg = message or (
            f"commons: {exported['bundles']} bundles, {exported['withdrawals']} withdrawals "
            f"({exported['removed']} removed), {exported['attestations']} attestations"
        )
        _git(repo, "commit", "-q", "-m", msg)
    pushed = False
    if push and has_remote:
        _git(repo, "push", "-q", "origin", "HEAD")
        pushed = True
    return {"imported": imported, "exported": exported, "committed": committed, "pushed": pushed}


def share(
    pack: Path,
    hardware: Dict[str, Any],
    root: Path,
    repo: Path,
    *,
    tiers: tuple = ("features",),
    push: bool = False,
    identity_path: Optional[Path] = None,
    policy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """One command for a contributor: bundle the pack, put it in the local replica, sync the git repo.

    Re-running it after new sessions adds a new bundle; re-running with no new
    data changes nothing. The identity file stays in the pack. Push only with push=True.
    """
    from .commons_bundle import build_bundle

    root = Path(root)
    commons = Commons.open(root) if (root / "commons.json").exists() else Commons.init(root, hardware, policy=policy)
    tmp = root / "outbox"
    if tmp.exists():
        shutil.rmtree(tmp)
    man = build_bundle(pack, tmp, hardware, tiers=tiers, identity_path=identity_path)
    added = man["bundle_id"] not in commons.state()["active"]
    if added:
        commons.contribute(tmp)  # copies into bundles/; a rejection leaves outbox/ for inspection
    shutil.rmtree(tmp)
    sync = git_sync(commons, repo, push=push)
    return {"bundle_id": man["bundle_id"], "contributor": man["contributor"], "added": added, **sync}
