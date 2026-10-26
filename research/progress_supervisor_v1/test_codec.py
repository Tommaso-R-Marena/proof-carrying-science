"""Actual native full-width IDs; these are not mock authorization tests."""
import time

from .authority import Authority, CODEC, DATA, PROGRESS, WIRE
from .certificate import encode, propose
from .example import model
from .test_progress import expected


def test_every_uint16_state_and_proposal_with_high_id_model(tmp_path, record_testsuite_property):
    mapped = [0, 1, 255, 256, 32767, 65534, 65535]
    # Exercise 65535 as an actually authorized reply, not merely an unknown or
    # denied proposal. The review fallback now carries both output bytes as FF.
    actions = [65535, 1, 255, 256, 32767, 65534, 0]
    m = model()
    for field in ["states", "initial", "safe"]:
        m[field] = sorted(mapped[n] for n in m[field])
    for field in ["actions", "forbidden"]:
        m[field] = sorted(actions[n] for n in m[field])
    triples = sorted((mapped[e["source"]], actions[e["action"]], mapped[e["target"]]) for e in m["transitions"])
    m["transitions"] = [dict(source=s, action=a, target=t) for s, a, t in triples]
    raw = encode(m)
    c = propose(raw, [mapped[4]])
    with Authority(raw, encode(c), tmp_path / "wide-native") as authority:
        assert len(authority.axioms) == len(PROGRESS + WIRE + CODEC + DATA)
        assert "PCSProgressData.wire_bounds" in authority.axioms
        assert authority.query(0, 65535) == dict(status="SELECTED", action=65535, rank=4)
        frames = []
        for n in range(65536):
            # All state IDs, then all proposed action IDs at a winning state.
            frames.append(bytes([1, n & 255, n >> 8, 0, 0, 0]))
            frames.append(bytes([1, 255, 0, 1, n & 255, n >> 8]))
        started = time.monotonic()
        for start in range(0, len(frames), 4096):
            chunk = frames[start:start + 4096]
            assert authority.query_raw(b"".join(chunk)) == b"".join(expected(f, c) for f in chunk)
        record_testsuite_property("full_width_native_frames", len(frames))
        record_testsuite_property("full_width_native_and_oracle_seconds", time.monotonic() - started)
        witnesses = frames[:8] + frames[-8:] + [
            bytes([1, 255, 0, 1, a & 255, a >> 8]) for a in mapped
        ]
        proof = authority.certify([(f, authority.query_raw(f)) for f in witnesses], "wide-wire")
        assert proof["kernel_checked"]
