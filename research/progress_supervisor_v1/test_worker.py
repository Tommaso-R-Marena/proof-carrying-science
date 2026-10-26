"""Real worker processes, actual Lean builds, bounded OS-pipe framing."""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

from .broker import PUBLIC, parse_proposal
from .worker import FrameReader, FramingError, MAX_PROPOSAL


def command(out, *options):
    return [sys.executable, "-m", "research.progress_supervisor_v1", "serve", str(out), *options]


def observed(out):
    with sqlite3.connect(out / "effects.sqlite") as db:
        return db.execute("SELECT state,generation FROM meta").fetchone(), db.execute("SELECT value FROM public").fetchall()


def messages(run):
    assert not run.stderr, run.stderr
    return [json.loads(line) for line in run.stdout.splitlines()]


def test_real_worker_owns_ids_state_verifier_effects_and_replay(tmp_path):
    out = tmp_path / "worker"
    proposals = [
        b'{"action":5,"verifier":"ALLOW","state":3,"request_id":"repeat"}',
        b'{"action":4}', b'not JSON', b'{"action":65535}', b'{"action":5}',
    ]
    run = subprocess.run(command(out), input=b"\n".join(proposals) + b"\n", capture_output=True, timeout=300)
    assert run.returncode == 0, run.stderr
    events = messages(run)
    assert [e["status"] for e in events] == ["READY", "STEP", "STEP", "STEP", "STEP", "COMPLETE"]
    steps = events[1:-1]
    assert [e["request_id"] for e in steps] == [f"turn-{i:04d}" for i in range(4)]
    assert [e["record"]["action"] for e in steps] == [0, 1, 2, 3]
    assert observed(out) == ((4, 4), [(PUBLIC,)])
    complete = events[-1]
    assert complete["wire_proof"]["kernel_checked"] and complete["path_proof"]["kernel_checked"]
    assert all(e["pcs_authority"] is False for e in events)
    capsule = json.loads((out / "capture.json").read_text())
    assert len(capsule["samples"]) == 4  # Input after the goal never executes.
    replay = subprocess.run(
        [sys.executable, "-m", "research.progress_supervisor_v1", "replay", str(out / "capture.json"), str(tmp_path / "replay")],
        capture_output=True, timeout=300,
    )
    assert replay.returncode == 0, replay.stderr
    assert json.loads(replay.stdout)["replayed"]
    assert observed(tmp_path / "replay") == observed(out)


@pytest.mark.parametrize("kind", ["oversized", "unterminated", "limited"])
def test_real_worker_stops_without_extra_effects_on_boundary_failure(tmp_path, kind):
    out = tmp_path / kind
    first = b'{"action":5}\n'
    if kind == "oversized":
        raw, options, expected_state, exit_code = first + b"x" * (MAX_PROPOSAL + 1) + b"\n" + first * 4, [], (1, 1), 20
    elif kind == "unterminated":
        raw, options, expected_state, exit_code = first * 2 + b'{"action":3}', [], (2, 2), 20
    else:
        raw, options, expected_state, exit_code = first * 4, ["--max-requests", "2"], (2, 2), 21
    run = subprocess.run(command(out, *options), input=raw, capture_output=True, timeout=300)
    assert run.returncode == exit_code, run.stderr
    events = messages(run)
    assert events[0]["status"] == "READY"
    assert events[-1]["status"] == ("INCOMPLETE" if kind == "limited" else "REFUSED_OR_UNAVAILABLE")
    assert all(e["status"] != "COMPLETE" for e in events)
    assert observed(out) == (expected_state, [])
    assert not (out / "capture.json").exists() and not (out / "result.json").exists()


def test_real_worker_deadline_with_open_silent_producer(tmp_path):
    out = tmp_path / "timeout"
    with subprocess.Popen(command(out, "--frame-timeout", "0.05"), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        # Keep the pipe open: EOF must not be mistaken for an actual deadline.
        process.wait(timeout=300)
        process.stdin.close()
        output, error = process.stdout.read(), process.stderr.read()
        assert process.returncode == 20 and not error
    events = [json.loads(line) for line in output.splitlines()]
    assert events[-1]["reason"] == "TimeoutError"
    assert observed(out) == ((0, 0), [])


def test_real_worker_sqlite_failure_returns_structured_refusal_without_effects(tmp_path):
    out = tmp_path / "storage-fault"
    with subprocess.Popen(command(out), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        ready = json.loads(process.stdout.readline())
        assert ready["status"] == "READY"
        # A trusted-host storage fault, not a producer capability. It must not
        # turn a failed database read into authorization or a continuing loop.
        with sqlite3.connect(out / "effects.sqlite") as db:
            db.execute("DROP TABLE meta")
        output, error = process.communicate(b'{"action":0}\n', timeout=60)
        assert process.returncode == 20 and not error
    assert json.loads(output)["reason"] == "OperationalError"
    with sqlite3.connect(out / "effects.sqlite") as db:
        assert db.execute("SELECT COUNT(*) FROM events").fetchone() == (0,)
        assert db.execute("SELECT COUNT(*) FROM public").fetchone() == (0,)


def test_bounded_frame_reader_coalesced_frames_exact_limit_and_eof():
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, b"a\n\n" + b"x" * MAX_PROPOSAL + b"\n")
        os.close(write_fd)
        write_fd = None
        reader = FrameReader(read_fd, 1)
        assert reader.read() == b"a"
        assert reader.read() == b""
        assert reader.read() == b"x" * MAX_PROPOSAL
        assert reader.read() is None
    finally:
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)


def test_frame_deadline_partial_input_and_nonfinite_configurations():
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, b"{")
        reader = FrameReader(read_fd, 0.03)
        start = time.monotonic()
        with pytest.raises(TimeoutError):
            reader.read()
        assert time.monotonic() - start < 1
        for invalid in [True, 0, -1, float("nan"), float("inf"), 301]:
            with pytest.raises(ValueError):
                FrameReader(read_fd, invalid)
    finally:
        os.close(read_fd)
        os.close(write_fd)


def test_deeply_nested_json_is_malformed_fallback_not_an_uncaught_parser_crash():
    proposal = b"[" * 1500 + b"0" + b"]" * 1500
    assert parse_proposal(proposal) == (None, "MALFORMED_FALLBACK")
