"""Preflight tests use untrusted claimed receipts, never positive Lean mocks.

Passing these structural tests establishes no authorization. Real native/SQL
authorization and independent replay are exercised by test_replay/test_worker.
"""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import importlib

import pytest

from .authority import packet
from .binding import SourceBinding, source_inventory
from .broker import PUBLIC, parse_proposal
from .certificate import encode, propose, sha
from .evidence import EXTERNAL_ORIGIN, CAPTURE_FORMAT
from .effects import Rows, PRIVATE, project, row_packet
from .example import model
from .intake import preflight


def claimed_fixture(*, pre=False):
    """Claimed structural data only: no verifier is invoked by this fixture."""
    raw = encode(model());cert = encode(propose(raw, [4]))
    binding = SourceBinding.capture(raw, cert)
    head, state, samples = binding.seed(pre), 0, []
    rows = Rows(PUBLIC if pre else PRIVATE, False, pre, ())
    actions = [0, 1, 3] if pre else [0, 1, 2, 3]
    ranks = {0: 4, 1: 3, 2: 2, 3: 1, 4: 0}
    proposal_raw = b'{"action":5}'
    for i, action in enumerate(actions):
        target = {0: 1, 1: 3 if pre else 2, 2: 3, 3: 4}[action]
        proposal, classification = parse_proposal(proposal_raw)
        event = dict(request_id=f"claim-{i}", generation=i + 1, source=state,
                     target=target, action=action, proposal=proposal,
                     proposal_classification=classification, body_sha256=sha(proposal_raw),
                     request_hex=packet(state, proposal).hex(),
                     reply_hex=bytes([1, 1, action, 0, ranks[state], 0]).hex(),
                     source_id=binding.source_id, previous_sha256=head, pcs_authority=False)
        _, after = project(state, action, rows)
        event["row_request_hex"] = row_packet(state, action, rows, target, after).hex()
        event["row_reply_hex"] = "0201"
        rows = after
        event["event_sha256"] = sha(encode(event))
        samples.append(dict(request_id=event["request_id"], proposal_hex=proposal_raw.hex(), record=event))
        state, head = target, event["event_sha256"]
    return dict(format=CAPTURE_FORMAT, data_origin=EXTERNAL_ORIGIN,
                sources=source_inventory(), model_hex=raw.hex(), certificate_hex=cert.hex(),
                pre_sanitized=pre, samples=samples,
                final=dict(state=4, transitions=len(actions), head=head, public=[PUBLIC], pcs_authority=False))


def rechain(cap):
    raw, cert = bytes.fromhex(cap["model_hex"]), bytes.fromhex(cap["certificate_hex"])
    head = SourceBinding.capture(raw, cert).seed(cap["pre_sanitized"])
    for sample in cap["samples"]:
        event = sample["record"]
        event["previous_sha256"] = head
        event["event_sha256"] = sha(encode({k: v for k, v in event.items() if k != "event_sha256"}))
        head = event["event_sha256"]
    cap["final"]["head"] = head


@pytest.mark.parametrize("pre", [False, True])
def test_structural_plan_is_immutable_and_does_not_assert_verification(pre):
    cap = claimed_fixture(pre=pre)
    plan = preflight(cap)
    assert plan.pre_sanitized is pre and len(plan.samples) == (3 if pre else 4)
    before = plan.samples[0].receipt_json
    cap["samples"][0]["record"]["action"] = 65535
    cap["sources"].clear()
    assert plan.samples[0].receipt_json == before and plan.sources
    with pytest.raises(FrozenInstanceError):
        plan.samples[0].request_id = "changed"
    assert not hasattr(plan, "kernel_checked")


ALIASES = [(i, field, kind) for i in range(4)
           for field in ["source", "target", "action", "generation", "proposal"]
           for kind in ["boolean", "float"]]


@pytest.mark.parametrize("index,field,kind", ALIASES)
def test_numeric_aliases_rejected_before_any_directory_verifier_or_effect(tmp_path, monkeypatch, index, field, kind):
    cap = claimed_fixture()
    value = cap["samples"][index]["record"][field]
    cap["samples"][index]["record"][field] = bool(value) if kind == "boolean" else float(value)
    module = importlib.import_module("research.progress_supervisor_v1.__main__")
    def forbidden(*args, **kwargs):
        pytest.fail("malformed capture reached a verifier/effect constructor")
    monkeypatch.setattr(module, "Broker", forbidden)
    output = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match="exact bounded integer"):
        module.execute(output, capture=cap)
    assert not output.exists()


@pytest.mark.parametrize("field", ["state", "transitions"])
@pytest.mark.parametrize("kind", ["boolean", "float"])
def test_final_numeric_aliases_rejected(field, kind):
    cap = claimed_fixture()
    cap["final"][field] = bool(cap["final"][field]) if kind == "boolean" else float(cap["final"][field])
    with pytest.raises(ValueError, match="exact bounded integer"):
        preflight(cap)


@pytest.mark.parametrize("attack", [
    "receipt-digest", "body-digest", "source-id", "previous-head", "generation-gap",
    "native-request", "native-reply", "unsafe-target", "false-fixture-outcome",
    "uppercase-hex", "hex-whitespace", "wrong-model", "wrong-certificate",
    "fake-authority", "fake-final-authority", "extra-root", "extra-receipt",
    "missing-receipt-field", "unexpected-status", "wrong-final-head", "wrong-public-row",
    "reordered-events", "duplicate-id-different-bytes", "invalid-request-id",
])
def test_corruption_rejected_even_with_recomputed_hash_chain(attack):
    cap = claimed_fixture();event = cap["samples"][0]["record"]
    if attack == "receipt-digest":event["event_sha256"] = "0" * 64
    elif attack == "body-digest":event["body_sha256"] = "0" * 64;rechain(cap)
    elif attack == "source-id":event["source_id"] = "0" * 64;rechain(cap)
    elif attack == "previous-head":event["previous_sha256"] = "0" * 64;event["event_sha256"] = sha(encode({k:v for k,v in event.items() if k!="event_sha256"}))
    elif attack == "generation-gap":event["generation"] = 2;rechain(cap)
    elif attack == "native-request":event["request_hex"] = packet(3, 5).hex();rechain(cap)
    elif attack == "native-reply":event["reply_hex"] = "010105000400";rechain(cap)
    elif attack == "unsafe-target":event["target"] = 5;rechain(cap)
    elif attack == "false-fixture-outcome":cap = claimed_fixture(pre=True);cap["pre_sanitized"] = False;rechain(cap)
    elif attack == "uppercase-hex":cap["model_hex"] = cap["model_hex"].upper()
    elif attack == "hex-whitespace":cap["samples"][0]["proposal_hex"] += " "
    elif attack == "wrong-model":cap["model_hex"] = "00"
    elif attack == "wrong-certificate":cap["certificate_hex"] = "00"
    elif attack == "fake-authority":event["pcs_authority"] = 0;rechain(cap)
    elif attack == "fake-final-authority":cap["final"]["pcs_authority"] = 0
    elif attack == "extra-root":cap["verifier"] = "ALLOW"
    elif attack == "extra-receipt":event["approved"] = True
    elif attack == "missing-receipt-field":del event["source_id"]
    elif attack == "unexpected-status":cap["samples"][0]["record"] = dict(status="HALTED", state=0, generation=0, pcs_authority=False)
    elif attack == "wrong-final-head":cap["final"]["head"] = "0" * 64
    elif attack == "wrong-public-row":cap["final"]["public"] = ["PRIVATE"]
    elif attack == "reordered-events":cap["samples"][0],cap["samples"][1] = cap["samples"][1],cap["samples"][0]
    elif attack == "duplicate-id-different-bytes":cap["samples"].insert(1,deepcopy(cap["samples"][0]));cap["samples"][1]["proposal_hex"] = b'{"action":0}'.hex()
    elif attack == "invalid-request-id":cap["samples"][0]["request_id"] = "../../outside"
    with pytest.raises(ValueError):preflight(cap)


def test_retry_and_post_goal_observations_keep_committed_path_length():
    cap = claimed_fixture();cap["samples"].insert(1, deepcopy(cap["samples"][0]))
    cap["samples"].append(dict(request_id="halt", proposal_hex="", record=dict(status="HALTED", state=4, generation=4, pcs_authority=False)))
    assert len(preflight(cap).samples) == 6


@pytest.mark.parametrize("attack", ["depth", "nodes", "string", "cycle", "fixture-type", "unsupported-type"])
def test_resource_and_non_json_inputs_fail_closed(attack):
    cap = claimed_fixture()
    if attack == "depth":
        nested = None
        for _ in range(20):nested = [nested]
        cap["final"] = nested
    elif attack == "nodes":cap["samples"] = [None] * 65
    elif attack == "string":cap["model_hex"] = "0" * 8193
    elif attack == "cycle":cap["final"] = cap
    elif attack == "fixture-type":cap["pre_sanitized"] = 1
    else:cap["final"] = object()
    with pytest.raises(ValueError):preflight(cap)


@pytest.mark.parametrize('attack', ['legacy', 'row-request', 'row-reply', 'row-whitespace', 'row-trailing'])
def test_versioned_row_receipts_refuse_even_with_recomputed_chain(attack):
    cap = claimed_fixture()
    record = cap['samples'][0]['record']
    if attack == 'legacy':cap['format'] = 'pcs-progress-supervisor-capture-v1'
    elif attack == 'row-request':
        raw = bytearray.fromhex(record['row_request_hex']);raw[13] = 1
        record['row_request_hex'] = raw.hex()
    elif attack == 'row-reply':record['row_reply_hex'] = '0200'
    elif attack == 'row-whitespace':record['row_request_hex'] += ' '
    else:record['row_request_hex'] += '00'
    rechain(cap)
    with pytest.raises(ValueError):preflight(cap)
