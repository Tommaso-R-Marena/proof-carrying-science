#!/usr/bin/env python3
"""Generate the PCS v3 stateful-authority fixtures (fixtures/semantic_authority_v3/).

Receipts are signed with the Python ``cryptography`` Ed25519 implementation (independent of the
Lean verifier) using PUBLIC TEST SEEDS.  A test-key receipt is evidence of nothing; in particular
a test-key proof receipt does not show that the Lean kernel checked anything.

Each fixture is (authority, request, ledger snapshot, expected outcome, expected receipt-phase
status/reason).  The expectations are checked by
  * ``tools/run_semantic_v3_fixture_tests.sh`` against the compiled binary, and
  * ``tools/CheckSemanticV3Fixtures.lean`` against the pure Lean function ``semanticCheckV3``.

Usage (from the project root):  python3 tools/gen_semantic_v3_fixtures.py
"""

from __future__ import annotations

import copy
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "python"))

from pcs_semantic.semantic_translation_v1 import canonical_json  # noqa: E402
from pcs_semantic import receipts_v3 as R  # noqa: E402

V2 = os.path.join(ROOT, "fixtures", "semantic_intelligence_v2")
OUT = os.path.join(ROOT, "fixtures", "semantic_authority_v3")

ENV_FINGERPRINT_FILE = os.path.join(ROOT, "fixtures", "semantic_authority_v3", "env_fingerprint.txt")

GENESIS, NOW, ISSUED, EXPIRES = 1000, 2000, 1500, 3000

K = {name: R.test_key("pcs-v3-test-" + name + "-seed") for name in
     ("confirmation", "confirmation2", "elaboration", "proof", "proof2", "attacker",
      "proof-retired", "proof-future")}


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def env_fingerprint() -> str:
    if os.path.exists(ENV_FINGERPRINT_FILE):
        with open(ENV_FINGERPRINT_FILE, encoding="utf-8") as f:
            return f.read().strip()
    return "unpinned-fixture-environment"


def base_authority(**over):
    reg = _load(os.path.join(V2, "authority.json"))["registry"]
    a = {"allowed_axioms": ["propext", "Classical.choice", "Quot.sound"],
         "confirmation_quorum": 1,
         "context": {"env_fingerprint": env_fingerprint(), "scope": "pcs-fixture-scope-v3",
                     "toolchain": "leanprover/lean4:v4.28.0"},
         "elaboration_quorum": 1,
         "keys": [
             {"key": K["confirmation"].public, "not_after": 10 ** 9, "not_before": 0, "role": "confirmation"},
             {"key": K["confirmation2"].public, "not_after": 10 ** 9, "not_before": 0, "role": "confirmation"},
             {"key": K["elaboration"].public, "not_after": 10 ** 9, "not_before": 0, "role": "elaboration"},
             {"key": K["proof"].public, "not_after": 10 ** 9, "not_before": 0, "role": "proof"},
             {"key": K["proof2"].public, "not_after": 10 ** 9, "not_before": 0, "role": "proof"},
             {"key": K["proof-retired"].public, "not_after": 1800, "not_before": 0, "role": "proof"},
             {"key": K["proof-future"].public, "not_after": 10 ** 9, "not_before": 2500, "role": "proof"},
         ],
         "proof_quorum": 1, "registry": reg, "require_elaboration": True, "require_proof": True,
         "revoked": [], "schema": R.AUTHORITY_V3_SCHEMA}
    a.update(over)
    return a


def v2_request(name):
    return _load(os.path.join(V2, "requests", name + ".json"))


AXIOMS = ["propext", "Quot.sound"]


def make_request(authority, v2name="pos_ai_safety_supplied_certificate", prefix="n",
                 roles=(("confirmation", "confirmation"), ("elaboration", "elaboration"), ("proof", "proof")),
                 axioms=AXIOMS, issued=ISSUED, expires=EXPIRES):
    core = R.legacy_free(v2_request(v2name))
    req = {"proof_axioms": list(axioms), "receipts": [], "request": core,
           "schema": R.REQUEST_V3_SCHEMA}
    for i, (role, keyname) in enumerate(roles):
        st = R.expected_statement(authority, req, role)
        req["receipts"].append(R.sign_envelope(K[keyname], role, st, f"{prefix}-{v2name}-{role}-{i}",
                                               issued, expires))
    return req


def state(consumed=(), revoked=(), genesis=GENESIS, now=NOW):
    return {"consumed": list(consumed), "genesis": genesis, "now": now, "revoked": list(revoked),
            "schema": R.LEDGER_STATE_SCHEMA}


def fixtures():
    A = base_authority()
    out = []

    def add(name, req, st, outcome, status, reason="", authority=A, aname="authority"):
        out.append((name, authority, aname, req, st, outcome, status, reason))

    good = make_request(A)
    add("pos_certified", good, state(), "CERTIFIED_TRANSLATION", "VALID")
    for v2name in ("pos_repro_supplied_certificate", "pos_bio_supplied_certificate",
                   "pos_ai_safety_identical"):
        add("pos_" + v2name, make_request(A, v2name), state(), "CERTIFIED_TRANSLATION", "VALID")
    # replay: the same request against a ledger that already consumed one of its nonces
    add("neg_replay_after_consumption", good, state(consumed=[good["receipts"][2]["nonce"]]),
        "RECEIPT_REJECTED", "INVALID", "REPLAY")
    # same nonce twice inside one request
    dup = copy.deepcopy(good)
    dup["receipts"][1] = R.sign_envelope(K["elaboration"], "elaboration",
                                         R.expected_statement(A, dup, "elaboration"),
                                         dup["receipts"][0]["nonce"], ISSUED, EXPIRES)
    add("neg_duplicate_nonce_in_request", dup, state(), "RECEIPT_REJECTED", "INVALID", "REPLAY")
    add("neg_expired", make_request(A, issued=1000, expires=1999), state(), "RECEIPT_REJECTED",
        "INVALID", "OUTSIDE_VALIDITY_WINDOW")
    add("neg_not_yet_valid", make_request(A, issued=2001, expires=3000), state(),
        "RECEIPT_REJECTED", "INVALID", "OUTSIDE_VALIDITY_WINDOW")
    add("neg_pre_genesis_after_ledger_reset", good, state(genesis=1600), "RECEIPT_REJECTED",
        "INVALID", "BEFORE_GENESIS")
    add("neg_revoked_in_config", good, state(), "RECEIPT_REJECTED", "INVALID", "REVOKED_KEY",
        authority=base_authority(revoked=[K["proof"].public]), aname="authority_revoked")
    add("neg_revoked_in_ledger", good, state(revoked=[K["confirmation"].public]),
        "RECEIPT_REJECTED", "INVALID", "REVOKED_KEY")
    add("neg_retired_key_rotation", make_request(A, roles=(("confirmation", "confirmation"),
        ("elaboration", "elaboration"), ("proof", "proof-retired"))), state(), "RECEIPT_REJECTED",
        "INVALID", "UNAUTHORIZED_KEY")
    add("neg_future_key_rotation", make_request(A, roles=(("confirmation", "confirmation"),
        ("elaboration", "elaboration"), ("proof", "proof-future"))), state(), "RECEIPT_REJECTED",
        "INVALID", "UNAUTHORIZED_KEY")
    add("neg_attacker_key", make_request(A, roles=(("confirmation", "confirmation"),
        ("elaboration", "elaboration"), ("proof", "attacker"))), state(), "RECEIPT_REJECTED",
        "INVALID", "UNAUTHORIZED_KEY")
    # role substitution: an elaboration key signs a *proof* envelope ("kernel proof" claimed by
    # an elaboration service)
    add("neg_false_kernel_proof_claim_wrong_role_key", make_request(A, roles=(("confirmation", "confirmation"),
        ("elaboration", "elaboration"), ("proof", "elaboration"))), state(), "RECEIPT_REJECTED",
        "INVALID", "UNAUTHORIZED_KEY")
    # role field changed after signing
    sub = copy.deepcopy(good)
    sub["receipts"][1]["role"] = "proof"
    sub["receipts"][1]["statement"] = R.expected_statement(A, sub, "proof")
    add("neg_role_field_substituted", sub, state(), "RECEIPT_REJECTED", "INVALID", "UNAUTHORIZED_KEY")
    # statement replacement inside a validly *formatted* envelope, re-signed by the right key
    rep = copy.deepcopy(good)
    st = R.expected_statement(A, rep, "proof")
    st["lean_source"] = st["lean_source"] + " ∧ True"
    rep["receipts"][2] = R.sign_envelope(K["proof"], "proof", st, rep["receipts"][2]["nonce"], ISSUED, EXPIRES)
    add("neg_statement_replacement", rep, state(), "RECEIPT_REJECTED", "INVALID", "STATEMENT_MISMATCH")
    # checker field changed: a record that does not claim a kernel check
    chk = copy.deepcopy(good)
    st = R.expected_statement(A, chk, "proof")
    st["checker"] = "lean-elaborator-only"
    chk["receipts"][2] = R.sign_envelope(K["proof"], "proof", st, chk["receipts"][2]["nonce"], ISSUED, EXPIRES)
    add("neg_proof_record_without_kernel_check", chk, state(), "RECEIPT_REJECTED", "INVALID",
        "STATEMENT_MISMATCH")
    # cross-environment reuse: receipts signed for another environment fingerprint
    otherA = base_authority(context=dict(A["context"], env_fingerprint="sha256:other-environment"))
    add("neg_cross_environment_reuse", make_request(otherA), state(), "RECEIPT_REJECTED",
        "INVALID", "STATEMENT_MISMATCH")
    otherS = base_authority(context=dict(A["context"], scope="another-authority-scope"))
    add("neg_cross_scope_reuse", make_request(otherS), state(), "RECEIPT_REJECTED", "INVALID",
        "STATEMENT_MISMATCH")
    # registry modified after the receipts were issued (adversarial registry edit)
    reg2 = copy.deepcopy(A["registry"])
    extra = copy.deepcopy(reg2["symbols"][0])
    extra["id"] = extra["id"] + "_injected"
    extra["lean_name"] = extra["lean_name"] + "Injected"
    reg2["symbols"].append(extra)
    add("neg_registry_modified_after_receipts", good, state(), "RECEIPT_REJECTED", "INVALID",
        "STATEMENT_MISMATCH", authority=base_authority(registry=reg2), aname="authority_registry_edited")
    # unknown protocol version
    ver = copy.deepcopy(good)
    ver["receipts"][0] = R.resign(K["confirmation"], dict(ver["receipts"][0], version="pcs-receipt-v9"))
    add("neg_unknown_version", ver, state(), "RECEIPT_REJECTED", "INVALID", "UNKNOWN_VERSION")
    # forged signature (bit flip)
    forged = copy.deepcopy(good)
    s = forged["receipts"][2]["signature"]
    forged["receipts"][2]["signature"] = ("A" if s[0] != "A" else "B") + s[1:]
    add("neg_forged_signature", forged, state(), "RECEIPT_REJECTED", "INVALID", "BAD_SIGNATURE")
    # nonce changed after signing (replay-avoidance attempt)
    nn = copy.deepcopy(good)
    nn["receipts"][2]["nonce"] = nn["receipts"][2]["nonce"] + "-fresh"
    add("neg_nonce_rewritten_after_signing", nn, state(), "RECEIPT_REJECTED", "INVALID", "BAD_SIGNATURE")
    # missing receipts
    add("neg_missing_confirmation", make_request(A, roles=(("elaboration", "elaboration"), ("proof", "proof"))),
        state(), "NEEDS_HUMAN_CLARIFICATION", "INVALID", "QUORUM_NOT_MET")
    add("neg_missing_proof", make_request(A, roles=(("confirmation", "confirmation"), ("elaboration", "elaboration"))),
        state(), "UNRESOLVED_PROOF_OBLIGATION", "INVALID", "QUORUM_NOT_MET")
    # quorums
    A2 = base_authority(proof_quorum=2)
    add("neg_proof_quorum_one_issuer", make_request(A2), state(), "UNRESOLVED_PROOF_OBLIGATION",
        "INVALID", "QUORUM_NOT_MET", authority=A2, aname="authority_quorum2")
    add("neg_proof_quorum_same_issuer_twice", make_request(A2, roles=(("confirmation", "confirmation"),
        ("elaboration", "elaboration"), ("proof", "proof"), ("proof", "proof"))), state(),
        "UNRESOLVED_PROOF_OBLIGATION", "INVALID", "QUORUM_NOT_MET", authority=A2, aname="authority_quorum2")
    add("pos_proof_quorum_two_issuers", make_request(A2, roles=(("confirmation", "confirmation"),
        ("elaboration", "elaboration"), ("proof", "proof"), ("proof", "proof2"))), state(),
        "CERTIFIED_TRANSLATION", "VALID", authority=A2, aname="authority_quorum2")
    # axioms
    add("neg_axiom_not_allowed", make_request(A, axioms=["propext", "sorryAx"]), state(),
        "RECEIPT_REJECTED", "INVALID", "AXIOM_NOT_ALLOWED")
    # legacy stateless receipts are not accepted in v3
    leg = copy.deepcopy(good)
    leg["request"] = v2_request("pos_ai_safety_supplied_certificate")
    add("neg_legacy_v1_receipts_present", leg, state(), "INVALID_PROPOSAL", "NOT_REACHED")
    # invalid authority: one key registered for two roles
    bad = base_authority()
    bad["keys"] = bad["keys"] + [{"key": K["confirmation"].public, "not_after": 10 ** 9,
                                  "not_before": 0, "role": "proof"}]
    add("neg_authority_key_in_two_roles", good, state(), "INVALID_AUTHORITY", "NOT_REACHED",
        authority=bad, aname="authority_key_two_roles")
    # semantic negatives with perfectly valid receipts: nothing is consumed
    add("neg_semantic_forall_to_exists_valid_receipts", make_request(A, "neg_forall_to_exists"),
        state(), "VERIFIED_COUNTEREXAMPLE", "NOT_REACHED")
    add("neg_semantic_high_confidence_valid_receipts",
        make_request(A, "neg_high_confidence_forall_to_exists"), state(), "VERIFIED_COUNTEREXAMPLE",
        "NOT_REACHED")
    add("neg_semantic_unresolved_ambiguity", make_request(A, "neg_unresolved_ambiguity"), state(),
        "NEEDS_HUMAN_CLARIFICATION", "NOT_REACHED")
    add("neg_semantic_forged_certificate", make_request(A, "neg_forged_certificate"), state(),
        "VERIFIED_COUNTEREXAMPLE", "NOT_REACHED")
    add("neg_semantic_unknown_symbol", make_request(A, "neg_unknown_symbol"), state(),
        "INVALID_PROPOSAL", "NOT_REACHED")
    return out


def main():
    os.makedirs(os.path.join(OUT, "requests"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "states"), exist_ok=True)
    entries = []
    written_auth = {}
    for (name, auth, aname, req, st, outcome, status, reason) in fixtures():
        ab = canonical_json(auth)
        if aname in written_auth and written_auth[aname] != ab:
            raise SystemExit(f"authority name clash: {aname}")
        written_auth[aname] = ab
        with open(os.path.join(OUT, aname + ".json"), "wb") as f:
            f.write(ab)
        with open(os.path.join(OUT, "requests", name + ".json"), "wb") as f:
            f.write(canonical_json(req))
        with open(os.path.join(OUT, "states", name + ".json"), "wb") as f:
            f.write(canonical_json(st))
        # independent oracle agreement (only meaningful when the receipt phase is reached)
        if status != "NOT_REACHED":
            valid, why = R.oracle_receipts_valid(auth, req, st)
            exp_valid = status == "VALID"
            if valid != exp_valid or (not valid and why != reason):
                raise SystemExit(f"oracle disagrees on {name}: {valid} {why} vs {status} {reason}")
        entries.append({"authority": aname + ".json", "name": name, "outcome": outcome,
                        "reason": reason, "receipt_status": status,
                        "request": "requests/" + name + ".json", "state": "states/" + name + ".json"})
        print(f"wrote {name}: {outcome} {status} {reason}")
    with open(os.path.join(OUT, "expected.json"), "wb") as f:
        f.write(canonical_json({"fixtures": entries, "schema": "pcs-semantic-fixtures-v3"}))


if __name__ == "__main__":
    main()
