"""Authenticated positive replays, signed semantic failures and wire mutations."""

import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from . import receiver as r


def candidate(number):
    return r.canonical({"schema": "pcs.detector-table/v1", "admission": "jointChannel", "mask": number})


def review_fixture():
    # Fixture builder. The signed review owns IDs, measured labels, and the hard contract.
    return {
        "schema": "pcs.review-cases/v1", "challenge": "reviewer-fixture", "epoch": 7,
        "hard": [{"id": "hard-six", "packet": 6, "flag": False},
                 {"id": "hard-four", "packet": 4, "flag": True}],
        "measured": [{"id": "dev-two", "packet": 2, "flag": True},
                     {"id": "dev-three", "packet": 3, "flag": True},
                     {"id": "dev-five", "packet": 5, "flag": False}],
    }


def initial(key, review):
    return {
        "schema": "pcs.review-checkpoint/v1", "challenge": review["challenge"],
        "key_sha256": r.digest(key), "review_sha256": r.digest(r.canonical(review)),
        "hard_sha256": r.digest(r.canonical(review["hard"])), "rule_sha256": r.rule_digest(),
        "epoch": review["epoch"], "generation": 0, "champion_sha256": r.digest(candidate(18)),
        "last_receipt_sha256": "0" * 64,
    }


def issue(key, state, proposed, **changes):
    edge = {
        "schema": "pcs.review-edge/v1", "challenge": state["challenge"], "epoch": state["epoch"],
        "generation": state["generation"] + 1, "previous_checkpoint_sha256": r.digest(r.canonical(state)),
        "parent_sha256": state["champion_sha256"], "candidate_sha256": r.digest(proposed),
        "review_sha256": state["review_sha256"], "rule_sha256": state["rule_sha256"],
        **changes,
    }
    return {"edge": edge, "ed25519": key.sign(r.PREFIX + r.canonical(edge)).hex()}


@pytest.fixture(scope="module")
def kernel():
    with r.lean_kernel() as replay:
        yield replay


def test_published_lineage(kernel):
    fixture = json.loads((Path(__file__).parent / "signed_fixture.json").read_bytes())
    public = bytes.fromhex(fixture["public_key_hex"])
    state = fixture["seed"]
    transitions = zip((18, 22), (22, 30), fixture["envelopes"], strict=True)
    for old, new, envelope in transitions:
        state = r.evaluate((r.canonical(state), public, r.canonical(fixture["review"]),
                            r.canonical(envelope), candidate(old), candidate(new)), kernel)
    assert state == fixture["terminal"]
    assert state["generation"] == 2


@pytest.mark.parametrize("control,reason", [
    ("wrong-key", "key mismatch"), ("wrong-signer", "invalid review signature"),
    ("forged-edge", "invalid review signature"), ("old-parent", "mismatched edge"),
    ("old-generation", "mismatched edge"), ("bool-generation", "mismatched edge"),
    ("wrong-challenge", "mismatched edge"), ("wrong-epoch", "mismatched edge"),
    ("previous-receipt", "mismatched edge"), ("wrong-rule", "rule source mismatch"),
    ("changed-review", "review digest mismatch"), ("changed-hard", "hard contract mismatch"),
    ("missing-measurement", "review digest mismatch"), ("duplicate-case", "duplicate case id"),
    ("unknown-input", "invalid labeled packet"), ("invalid-label", "invalid labeled packet"),
    ("empty-suite", "invalid case count"), ("swapped-candidate", "source digest mismatch"),
    ("swapped-parent", "source digest mismatch"), ("duplicate-key", "invalid canonical JSON"),
    ("bad-class", "unsupported candidate"), ("overwide-mask", "unsupported candidate"),
    ("hard-regression", "semantic promotion rejected"), ("admission", "semantic promotion rejected"),
    ("tie", "semantic promotion rejected"), ("kernel-disagreement", "semantic replays disagree"),
    ("added-predictions", "unexpected fields"), ("wrong-review-rule", "mismatched edge"),
    ("wrong-review-hash", "mismatched edge"), ("stale-replay", "mismatched edge"),
    ("swap-hard-success", "semantic promotion rejected"), ("bad-checkpoint", "invalid checkpoint"),
    ("wire-too-large", "oversized"), ("empty-hard", "invalid case count"),
])
def test_negative_controls(control, reason, kernel):
    secret = Ed25519PrivateKey.generate()
    public = secret.public_key().public_bytes_raw()
    review = review_fixture()
    proposed = candidate(22)
    parent = candidate(18)
    changes = {}

    if control == "duplicate-case":
        review["measured"][0]["id"] = review["hard"][0]["id"]
    if control == "unknown-input":
        review["measured"][0]["packet"] = 8
    if control == "invalid-label":
        review["measured"][0]["flag"] = 1
    if control == "empty-suite":
        review["measured"] = []
    if control == "empty-hard":
        review["hard"] = []
    if control == "swap-hard-success":
        # Same hard count, different protected answer. The soft score still rises.
        review["hard"][0]["flag"] = True
        proposed = candidate(2 + 4 + 64)
    state = initial(public, review)
    if control == "bad-checkpoint":
        state["challenge"] = 1
    if control == "old-parent":
        changes["parent_sha256"] = "1" * 64
    if control == "old-generation":
        changes["generation"] = 0
    if control == "bool-generation":
        changes["generation"] = True
    if control == "wrong-epoch":
        changes["epoch"] = 8
    if control == "wrong-challenge":
        changes["challenge"] = "unrelated"
    if control == "previous-receipt":
        changes["previous_checkpoint_sha256"] = "1" * 64
    if control == "wrong-rule":
        state["rule_sha256"] = "1" * 64
    if control == "wrong-review-hash":
        changes["review_sha256"] = "1" * 64
    if control == "wrong-review-rule":
        changes["rule_sha256"] = "1" * 64
    if control == "changed-hard":
        state["hard_sha256"] = "1" * 64
    if control == "bad-class":
        proposed = proposed.replace(b"jointChannel", b"channel1Only")
    if control == "overwide-mask":
        proposed = candidate(256)
    if control == "hard-regression":
        proposed = candidate(2 + 4 + 8)
    if control == "admission":
        proposed = candidate(16 + 4 + 8)
    if control == "tie":
        proposed = parent
    if control == "duplicate-key":
        proposed = proposed.replace(b'"mask":22', b'"mask":19,"mask":22')
    if control == "added-predictions":
        changes["predictions"] = [True] * 3
    signer = Ed25519PrivateKey.generate() if control == "wrong-signer" else secret
    envelope = issue(signer, state, proposed, **changes)
    if control == "forged-edge":
        envelope["edge"]["generation"] += 1
    if control == "wrong-key":
        public = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
    if control == "swapped-candidate":
        proposed = candidate(30)
    if control == "swapped-parent":
        parent = candidate(2)
    if control == "changed-review":
        review["measured"][0]["flag"] = False
    if control == "missing-measurement":
        review["measured"].pop()
    if control == "stale-replay":
        state = r.evaluate((r.canonical(state), public, r.canonical(review), r.canonical(envelope),
                            parent, proposed), kernel)
    if control == "kernel-disagreement":
        kernel = lambda *_: "true 0 99 2 2"
    state_raw = r.canonical(state)
    if control == "wire-too-large":
        state_raw += b" " * r.LIMIT
    inputs = (state_raw, public, r.canonical(review), r.canonical(envelope), parent, proposed)
    with pytest.raises(r.Rejected, match=reason):
        r.evaluate(inputs, kernel)
