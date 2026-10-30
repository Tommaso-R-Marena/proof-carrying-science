"""Real V6 Lean-authorized PGSC6 recovery over interrupted commits.

No Lean mock. The actual V6 certificate checker authorizes all promotions;
in two failure windows, the authority re-runs real Lean against exact
trusted old bytes before reanchoring or clearing a pending intent.
"""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from pgsc6_journaled_recovery import JournaledPGSC6
from pgsc6_pinned_store import RESEARCH, IntegrityFailure, StaleHead
from pgsc6_reference import decode_certificate

CERTS = tuple(
    (RESEARCH.parents[1] / "formal" / "fixtures" / "proof_gated" /
     "v6_certs" / f"step{i}.pgsc6").read_bytes() for i in (1, 2, 3)
)


def crash_at(where: str):
    def fail(phase: str):
        if phase == where:
            raise RuntimeError("simulated crash after " + phase)
    return fail


def main():
    with tempfile.TemporaryDirectory(prefix="pgsc6-live-recover-") as tmp:
        d = Path(tmp)
        controller = JournaledPGSC6.initialize(d/"store", d/"authority")
        original = controller.audit()
        if controller.recover() != "clean":
            raise AssertionError("new journal should be clean")

        with patch.object(controller, "_phase_hook",
                          side_effect=crash_at("intent_durable")):
            try:
                controller.promote(CERTS[0], original)
                raise AssertionError("expected simulated crash before store commit")
            except RuntimeError:
                pass
        if controller.recover() != "aborted_before_commit":
            raise AssertionError("pending-but-uncommitted intent not safely abandoned")
        if controller.audit() != original:
            raise AssertionError("pre-commit failure changed the protected head")

        with patch.object(controller, "_phase_hook",
                          side_effect=crash_at("store_committed")):
            try:
                controller.promote(CERTS[0], original)
                raise AssertionError("expected simulated crash after model-store commit")
            except RuntimeError:
                pass
        if controller.store.audit().generation != 1:
            raise AssertionError("model commit missing")
        try:
            controller.audit()
        except IntegrityFailure:
            pass
        else:
            raise AssertionError("unresolved journal must block serving")
        if controller.recover() != "completed_one_committed_step":
            raise AssertionError("real Lean recovery failed to reauthorize model commit")
        first = controller.audit()
        if first.generation != 1:
            raise AssertionError("journal reanchor did not advance generation")

        with patch.object(controller, "_phase_hook",
                          side_effect=crash_at("anchor_committed")):
            try:
                controller.promote(CERTS[1], first)
                raise AssertionError("expected simulated crash after anchor commit")
            except RuntimeError:
                pass
        if controller.recover() != "cleaned_committed_intent":
            raise AssertionError("cannot replay verified commit to clear journal")
        second = controller.audit()
        if second.generation != 2:
            raise AssertionError("second accepted generation missing")
        third = controller.promote(CERTS[2], second)
        if third.generation != 3:
            raise AssertionError("third promotion failed")

        for i, cert in enumerate(CERTS):
            if i == 2:
                if controller.snapshot(expected=third).raw != decode_certificate(cert).candidate:
                    raise AssertionError("served bytes not the final V6-certified artifact")

        try:
            controller.promote(CERTS[0], original)
            raise AssertionError("stale replay authorized")
        except StaleHead:
            pass
        if controller.audit() != third or controller.recover() != "clean":
            raise AssertionError("clean post-recovery state did not persist")

    print(json.dumps({
        "result": "PASS",
        "actual_lean_authorized_generations": [1,2,3],
        "precommit_intent_aborted": True,
        "post_store_commit_rechecked_by_actual_lean": True,
        "post_anchor_commit_rechecked_by_actual_lean": True,
        "final_served_bytes_match_V6_candidate": True,
        "same_privilege_attacker_protection": False,
        "atomic_cross_store_transaction": False,
        "machine_checked_host_refinement": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
