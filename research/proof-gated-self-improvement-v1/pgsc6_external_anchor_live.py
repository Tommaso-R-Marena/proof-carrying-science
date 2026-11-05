"""Actual Lean V6 + independently held checkpoint end-to-end experiment.

First promote three real certificates with actual Lean, then rewind the
entire model store to a prior *internally valid* checkpoint while leaving
the external checkpoint untouched. Prove (empirically) that base-store
self-audit accepts the rewind but independent anchor refuses all serving
and future promotion.

No attacker OS privilege isolation is claimed by this single-process test.
"""
from pathlib import Path
import json
import shutil
import tempfile

from pgsc6_external_anchor import ExternallyAnchoredPGSC6
from pgsc6_pinned_store import RESEARCH, IntegrityFailure
from pgsc6_reference import decode_certificate

CERTS = tuple(
    (RESEARCH.parents[1] / "formal" / "fixtures" / "proof_gated" /
     "v6_certs" / f"step{i}.pgsc6").read_bytes() for i in (1, 2, 3)
)


def main() -> dict:
    with tempfile.TemporaryDirectory(prefix="pgsc6-live-external-") as d:
        root = Path(d)
        store_path, anchor_path = root / "store", root / "independent-anchor"
        s = ExternallyAnchoredPGSC6.initialize(store_path, anchor_path)
        head = s.audit()
        prior = None
        promotions = []
        for i, cert in enumerate(CERTS):
            if decode_certificate(cert).incumbent != s.snapshot().raw:
                raise AssertionError("current artifact mismatches certificate")
            next_head = s.promote(cert, head)  # actual Lean, no mock
            if next_head.generation != i+1 or s.audit() != next_head:
                raise AssertionError("committed generation/checkpoint mismatch")
            snapshot = s.snapshot(expected=next_head)
            if snapshot.raw != decode_certificate(cert).candidate:
                raise AssertionError("exact certified candidate not served")
            for x in (-10**9, -1000, -4, -1, 0, 1, 4, 1000, 10**9):
                if snapshot.predict(x) != snapshot.model.predict(x):
                    raise AssertionError("frozen byte model and served inference differ")
            promotions.append(next_head.generation)
            head = next_head
            if i == 0:
                prior = root / "prior-valid-full-store"
                shutil.copytree(store_path, prior)

        # With a well-formed older HEAD, entire receipt chain and objects,
        # the base store has no independent fact proving it ever reached gen3.
        final_gen = s.audit().generation
        shutil.rmtree(store_path)
        shutil.copytree(prior, store_path)
        base_recognized_old = s.store.audit()
        if base_recognized_old.generation != 1:
            raise AssertionError("failed to construct internally valid history rollback")
        refused = {}
        for opname, operation in [
            ("audit", s.audit),
            ("serve", s.snapshot),
            ("promote", lambda: s.promote(CERTS[1], base_recognized_old)),
        ]:
            try:
                operation()
            except IntegrityFailure:
                refused[opname] = True
            else:
                raise AssertionError("external anchor permitted reverted state: " + opname)

    result = {
        "result": "PASS",
        "actual_lean_certificates_accepted": len(promotions),
        "generations_reached": promotions,
        "last_generation_before_replay": final_gen,
        "model_store_accepts_complete_old_history": True,
        "external_anchor_rejected_rollback_on": sorted(refused),
        "independent_privilege_isolation": False,
        "production_root_of_trust": False,
        "proof_of_OS_semantics": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
