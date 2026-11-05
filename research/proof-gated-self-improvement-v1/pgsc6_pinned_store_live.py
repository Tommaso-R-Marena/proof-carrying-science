"""Live PGSC6 host-state promotion using actual Lean 4.28.0, no mocks.

Never claimed to establish OS attacker isolation or a proved Python refinement.
Uses the V6 exact fixtures and runs three honest model promotions.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

from pgsc6_pinned_store import (
    PinnedPGSC6Store, RESEARCH, POLICY, INITIAL_BYTES,
    StaleHead, ProposalRejected, IntegrityFailure,
)
from pgsc6_reference import decode_certificate

FIXTURES = RESEARCH.parents[1] / "formal" / "fixtures" / "proof_gated" / "v6_certs"


def main():
    certs = [(FIXTURES / f"step{i}.pgsc6").read_bytes() for i in (1, 2, 3)]
    with tempfile.TemporaryDirectory(prefix="pgsc6-live-") as tmp:
        root = Path(tmp) / "store"
        store = PinnedPGSC6Store.initialize(root)
        genesis = store.audit()
        if store.snapshot().raw != INITIAL_BYTES:
            raise AssertionError("incorrect fixed-policy genesis")
        head = genesis
        reports = []
        for generation, cert in enumerate(certs):
            if decode_certificate(cert).incumbent != store.snapshot().raw:
                raise AssertionError("certificate's incumbent diverges from store")
            try:
                store.promote(cert + b"\n", head)
                raise AssertionError("noncanonical mutated cert promoted")
            except ProposalRejected:
                pass
            now = store.audit()
            if now != head:
                raise AssertionError("failed proposal changed state")
            next_head = store.promote(cert, head)  # ACTUAL Lean V6, no mock
            if next_head.generation != generation+1:
                raise AssertionError("generation was not monotonic")
            if store.audit() != next_head:
                raise AssertionError("audited store differs after commit")
            snapshot = store.snapshot(expected=next_head)
            if snapshot.raw != decode_certificate(cert).candidate:
                raise AssertionError("committed bytes differ from authorized candidate")
            for x in (-1000000000, -100, -12, -4, -1, 0, 1, 4, 12, 100,
                      1000000000):
                if snapshot.predict(x) != snapshot.model.predict(x):
                    raise AssertionError("served snapshot not mathematical interpreter")
            reports.append({
                "generation": next_head.generation,
                "active_digest": next_head.active_sha256,
                "receipt": next_head.last_receipt_sha256,
            })
            head = next_head

        for bad, expected in ((certs[0], genesis), (certs[0], head)):
            try:
                store.promote(bad, expected)
                raise AssertionError("stale replay was accepted")
            except (StaleHead, ProposalRejected):
                pass
        if store.audit() != head:
            raise AssertionError("failed replay changed head")
        final = store.snapshot()
        if final.predict(20) != 5:
            raise AssertionError("incorrect final PGSI2-WIDE inference")

    result = {
        "result": "PASS",
        "real_lean_checker_promotions": 3,
        "negative_mutated_certificates_rejected": 3,
        "stale_replays_rejected": 2,
        "candidate_snapshot_checked": True,
        "compiled_policy_overridden_by_proposer": False,
        "production_security": False,
        "same_privilege_adversary_resistance": False,
        "full_rollback_detection": False,
        "generations": reports,
    }
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
