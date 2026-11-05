"""Real Lean binary framing controls. No affirmative verifier substitutes."""
import json
import os
from pathlib import Path
import struct
import subprocess

import pytest

HERE = Path(__file__).resolve().parents[1]


def actual_command():
    required = ("PCS_SCIENTIFIC_LEAN", "PCS_SCIENTIFIC_MAIN", "PCS_SCIENTIFIC_CWD")
    if any(not os.environ.get(name) for name in required):
        pytest.fail("Actual Lean transport tests require " + ", ".join(required) + " and its operator-configured LEAN_PATH")
    return [os.environ[required[0]], "--run", os.environ[required[1]]], os.environ[required[2]]


def execute(payload):
    command, cwd = actual_command()
    p = subprocess.run(command, cwd=cwd, input=payload, capture_output=True, timeout=60, check=True)
    assert p.stderr == b""
    return [json.loads(line) for line in p.stdout.splitlines()]


def frame(raw):
    return struct.pack(">I", len(raw)) + raw


@pytest.mark.parametrize("payload,error", [
    (b"\0", "truncated_header"),
    (b"\0\0\0", "truncated_header"),
    (struct.pack(">I", 3) + b"x", "truncated_body"),
    (struct.pack(">I", 8193), "oversize_frame"),
    (struct.pack(">I", 2**32-1), "oversize_frame"),
])
def test_real_transport_rejects_and_closes(payload, error):
    rows = execute(payload)
    assert len(rows) == 1
    assert rows[0]["accepted"] is False
    assert rows[0]["result"] is None
    assert rows[0]["error"] == error
    assert rows[0]["production_authority"] is False
    assert rows[0]["scientific_acceptance"] is False


def test_eof_between_frames_is_clean():
    assert execute(b"") == []


def test_real_mixed_frames_bind_exact_same_bytes():
    good = (HERE / "fixtures/multi-step-nonsingleton.wire").read_bytes()
    raws = [b"", b"\xff\x00", good, good + b"\n", good]
    rows = execute(b"".join(map(frame, raws)))
    assert [r["accepted"] for r in rows] == [False, False, True, False, True]
    assert [r["raw_hex"] for r in rows] == [r.hex() for r in raws]
    assert rows[2]["result"] == rows[4]["result"]


def test_oversize_header_does_not_consume_a_following_valid_frame():
    good = (HERE / "fixtures/one-step.wire").read_bytes()
    rows = execute(struct.pack(">I", 8193) + frame(good))
    assert len(rows) == 1
    assert rows[0]["error"] == "oversize_frame"


def test_fragmented_header_and_body():
    command, cwd = actual_command()
    raw = (HERE / "fixtures/one-step.wire").read_bytes()
    with subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
        assert p.stdin is not None
        payload = frame(raw)
        for offset in range(0, len(payload), 3):
            p.stdin.write(payload[offset:offset+3])
            p.stdin.flush()
        p.stdin.close()
        p.stdin = None
        stdout, stderr = p.communicate(timeout=60)
        assert p.returncode == 0 and stderr == b""
        rows = [json.loads(line) for line in stdout.splitlines()]
        assert len(rows) == 1 and rows[0]["accepted"] is True
        assert rows[0]["raw_hex"] == raw.hex()
