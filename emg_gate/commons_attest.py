"""Signed local-evaluation results: each person's own data is a test set nobody else holds.

A contributor evaluates a released model on the held-out donning in their own
pack, on their own machine, and publishes only the numbers plus a sha256
commitment of the rows they used. The signature ties the result to the same
key that signs their bundles, so a replica can tell a result from someone who
put real, verified data into this pool ("backed") from one by a stranger.
Nobody can check the numbers themselves without the rows; the commitment lets
the person prove them later if they choose to reveal. Scoreboards therefore
report the median and the worst backed result, never a single claim.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .commons_bundle import contributor_id, sign_body, signature_ok
from .jsonlite import errors as schema_errors
from .schemas import load_schema

PURPOSE = "attest"


def make_attestation(ident: Dict[str, str], body: Dict[str, Any]) -> Dict[str, Any]:
    body = {**body, "contributor": ident["contributor"], "pubkey": ident["pubkey"]}
    return {**body, "sig": sign_body(ident, PURPOSE, body)}


def verify_attestation(att: Dict[str, Any], *, expected_pool_key: Optional[str] = None) -> List[str]:
    errs = schema_errors(load_schema("commons_attestation"), att)
    if errs:
        return errs
    if att["contributor"] != contributor_id(att["pubkey"]):
        errs.append("contributor is not derived from pubkey")
    if expected_pool_key and att["pool_key"] != expected_pool_key:
        errs.append("attestation is for another pool")
    body = {k: v for k, v in att.items() if k != "sig"}
    if not signature_ok(att["pubkey"], PURPOSE, body, att["sig"]):
        errs.append("attestation signature does not verify")
    return errs
