import copy
import json

import pytest

from research.lean_recursive_autoformalization_v1.qualification_ii.batch import pilot
from research.lean_recursive_autoformalization_v1.qualification_ii.batch import receiver as r


def material(name):
    return (r.HERE / (name + ".json")).read_bytes()


@pytest.fixture(scope="module")
def baseline():
    dev, base = material("development"), material("baseline")
    wire = r.response(dev, pilot.DEV, "development", base)
    return dev, base, wire


def test_original_extra_identifier_refuses_entire_recording():
    report = pilot.historical()
    assert report["accepted"] is False and (report["requested"], report["received"]) == (12, 13)
    assert "extra=['imp_dummy']" in report["reason"]


@pytest.mark.parametrize("invalid", [
    b"{}", b"{", b"\xff", b"null", b'{"items":[],"items":[]}', b"1.0", b"NaN",
    b"9999999", b"[" * 35 + b"]" * 35, b"x" * (r.MAX_BYTES + 1), b"{} []",
])
def test_invalid_bytes_are_bounded_and_fail_closed(baseline, invalid):
    dev, base, _ = baseline
    with pytest.raises(r.Rejected):
        r.receive(dev, pilot.DEV, "development", base, invalid)


def altered_wire(baseline, change):
    dev, base, wire = baseline
    packet = json.loads(wire)
    change(packet)
    return dev, base, r.canonical(packet)


@pytest.mark.parametrize("change", [
    lambda p: p["items"].append({**p["items"][0], "id": "imp_dummy"}),
    lambda p: p["items"].append(p["items"][0]),
    lambda p: p["items"].pop(),
    lambda p: p["items"].reverse(),
    lambda p: p["items"][0].update(id=[]),
    lambda p: p["items"][1].update(status="KERNEL_CHECKED"),
    lambda p: p["items"][1].update(contract={"raw_lean": "#eval true"}),
    lambda p: p["items"][1].update(source_sha256=p["items"][0]["source_sha256"]),
    lambda p: p["items"][0].update(contract=None),
    lambda p: p.update(reviewer={"accept": True}),
    lambda p: p.update(generation=False),
    lambda p: p.update(parent_sha256="0" * 63),
    lambda p: p.update(revision_sha256=p["cases_sha256"]),
    lambda p: p.update(model="external-unverified-v0"),
    lambda p: p.update(verifier_sha256="a" * 64),
])
def test_whole_batch_rejected_before_any_proof_search(baseline, change, monkeypatch):
    dev, base, wire = altered_wire(baseline, change)
    monkeypatch.setattr(r.algebra, "check_pair", lambda *_: pytest.fail("partial evaluation"))
    with pytest.raises(r.Rejected):
        r.receive(dev, pilot.DEV, "development", base, wire)


def test_semantically_forged_references_and_translator_fail_replay(baseline):
    dev, base, wire = baseline
    spoofed = r.decode(dev)
    spoofed["cases"][0]["reference"] = spoofed["cases"][2]["reference"]
    with pytest.raises(r.Rejected, match="anchor"):
        r.receive(r.canonical(spoofed), pilot.DEV, "development", base, wire)
    with pytest.raises(r.Rejected, match="provenance"):
        r.receive(dev, pilot.DEV, "development", material("synonym"), wire)
    with pytest.raises(r.Rejected, match="phrases"):
        r.open_revision(r.canonical({"schema":"set-batch/revision-v1", "model":"x",
                                     "rules":[[".*", "arbitrary code"]]}))
    with pytest.raises(r.Rejected, match="baseline revision"):
        r.replay(dev, pilot.DEV, pilot.CANDIDATE, [r.Submission(base, wire)])


@pytest.fixture(scope="module")
def evidence(baseline):
    dev, base, awire = baseline
    a = r.Submission(base, awire)
    prior = r.replay(dev, pilot.DEV, pilot.BASE, [a])
    head = r.digest(prior)
    new = material("synonym")
    b = r.Submission(new, r.response(dev, pilot.DEV, "development", new, head, 1))
    promoted = r.advance(dev, pilot.DEV, pilot.BASE, [a], head, b)
    return a, b, prior, promoted


def test_kernel_proof_correspondence_and_abstention_are_separate(evidence):
    _, _, prior, promoted = evidence
    assert [row["credit"] for row in prior["outcomes"]] == [2, 0, 1]
    assert [row["credit"] for row in promoted["outcomes"]] == [2, 2, 1]
    assert prior["outcomes"][1]["review"]["proof"] == "NOT_CHECKED"
    for row in promoted["outcomes"]:
        review = row["review"]
        if row["credit"] == 2:
            assert r.DIGEST.fullmatch(review["lean_sha256"]) and review["axioms"] is not None


def test_higher_score_cannot_erase_previous_semantic_case(baseline, evidence):
    dev, _, _ = baseline
    a, _, prior, _ = evidence
    corrupt = r.decode(material("synonym"))
    corrupt["rules"].append(["is a subset of B", "is a subset of A"])
    new = r.canonical(corrupt)
    head = r.digest(prior)
    wire = r.response(dev, pilot.DEV, "development", new, head, 1)
    scored = r.receive(dev, pilot.DEV, "development", new, wire, head, 1)
    assert scored["score"] > prior["score"]
    assert scored["outcomes"][2]["credit"] == 0
    with pytest.raises(r.Rejected, match="case regression"):
        r.advance(dev, pilot.DEV, pilot.BASE, [a], head, r.Submission(new, wire))


def test_replay_forgery_stale_champion_and_noop(baseline, evidence):
    dev, base, _ = baseline
    a, b, prior, promoted = evidence
    head = r.digest(prior)
    with pytest.raises(r.Rejected, match="stale champion"):
        r.advance(dev, pilot.DEV, pilot.BASE, [a], r.digest(promoted), b)
    with pytest.raises(r.Rejected, match="provenance"):
        r.replay(dev, pilot.DEV, pilot.BASE, [a, b, b])
    with pytest.raises(r.Rejected, match="no certified gain"):
        noop = r.Submission(base, r.response(dev, pilot.DEV, "development", base, head, 1))
        r.advance(dev, pilot.DEV, pilot.BASE, [a], head, noop)
    forged = copy.deepcopy(promoted)
    forged["outcomes"][2]["review"]["proof"] = "KERNEL_CHECKED"
    with pytest.raises(r.Rejected, match="disagrees"):
        r.verify_receipt(r.canonical(forged), dev, pilot.DEV, pilot.BASE, [a,b])
    assert r.verify_receipt(r.canonical(promoted), dev, pilot.DEV, pilot.BASE, [a,b]) == promoted


def test_final_split_never_qualifies_for_promotion_and_disallows_exact_overlap(baseline, evidence):
    dev, _, _ = baseline
    a, _, prior, _ = evidence
    with pytest.raises(r.Rejected, match="case split"):
        r.replay(material("final"), pilot.FINAL, pilot.BASE, [a])
    renamed = r.decode(dev)
    renamed["split"] = "final"
    overlapping = r.canonical(renamed)
    with pytest.raises(r.Rejected, match="overlaps"):
        r.measure_final(overlapping, r.sha(overlapping), dev, pilot.DEV, pilot.BASE, [a], r.digest(prior))


def test_equivalent_but_noncanonical_response_bytes_fail_before_replay(baseline, monkeypatch):
    dev, base, wire = baseline
    monkeypatch.setattr(r, "translate", lambda *_: pytest.fail("unexpected translator call"))
    with pytest.raises(r.Rejected, match="noncanonical response"):
        r.receive(dev, pilot.DEV, "development", base, wire + b"\n")


def test_unavailable_kernel_cannot_manufacture_a_weak_baseline(baseline, monkeypatch):
    dev, base, wire = baseline
    monkeypatch.setattr(r.algebra, "check_pair", lambda *_: {
        "correspondence": "UNKNOWN", "proof": "UNKNOWN", "elaborated": False})
    with pytest.raises(r.Rejected, match="kernel review incomplete"):
        r.receive(dev, pilot.DEV, "development", base, wire)
