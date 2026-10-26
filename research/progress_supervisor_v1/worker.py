"""Process-owned workflow, with a bounded action-only JSONL input channel.

The producer has no object reference to the broker or verifier. This is process
separation for the interface, not same-user OS isolation or a protected host root.
"""
from __future__ import annotations

import math
import os
import selectors
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from .broker import Broker
from .certificate import encode, sha
from .evidence import publish, sources, write

FORMAT = "pcs-progress-supervisor-session-v1"
MAX_PROPOSAL = 4096
MAX_TURNS = 256


class FramingError(ValueError):
    """A bad frame ends the session; never guess where the next frame begins."""


class FrameReader:
    """Bounded framing with a whole-frame deadline, including slow producers."""

    def __init__(self, fd, timeout):
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 300:
            raise ValueError("frame timeout must be finite in (0,300] seconds")
        self.fd, self.timeout, self.pending = fd, timeout, bytearray()

    def read(self):
        deadline = time.monotonic() + self.timeout
        with selectors.SelectSelector() as selector:
            selector.register(self.fd, selectors.EVENT_READ)
            while True:
                newline = self.pending.find(b"\n")
                if newline >= 0:
                    if newline > MAX_PROPOSAL:
                        raise FramingError("oversized proposal")
                    line = bytes(self.pending[:newline])
                    del self.pending[:newline + 1]
                    return line
                if len(self.pending) > MAX_PROPOSAL:
                    raise FramingError("oversized proposal")
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise TimeoutError("proposal frame deadline")
                # Never read or allocate an unbounded producer-controlled line.
                chunk = os.read(self.fd, MAX_PROPOSAL + 2 - len(self.pending))
                if not chunk:
                    if self.pending:
                        raise FramingError("unterminated proposal")
                    return None
                self.pending.extend(chunk)


def _emit(status, **fields):
    message = dict(format=FORMAT, status=status, pcs_authority=False, **fields)
    sys.stdout.buffer.write(encode(message) + b"\n")
    sys.stdout.buffer.flush()


def serve(output, *, pre_sanitized=False, max_requests=32, frame_timeout=30):
    """Run one fresh, bounded session. The trusted launch fixes its configuration.

    Input contains only raw action proposals. This process mints new request IDs
    and owns the true state, generation, native verifier and fixed SQL tools.
    EOF/limits/framing failures never assert completion. Goal completion closes
    the session; no further input can authorize effects in it.
    """
    if type(max_requests) is not int or not 1 <= max_requests <= MAX_TURNS:
        raise ValueError("request limit must be an exact integer in [1,256]")
    if type(pre_sanitized) is not bool:
        raise ValueError("trusted fixture mode must be Boolean")
    reader = FrameReader(sys.stdin.fileno(), frame_timeout)
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    before = sources()
    samples = []
    try:
        with Broker(out / "effects.sqlite", out / "authority", pre_sanitized=pre_sanitized) as broker:
            _emit("READY", model_sha256=sha(broker.model_raw),
                  certificate_sha256=sha(broker.cert_raw), sources=before,
                  max_proposal_bytes=MAX_PROPOSAL, max_requests=max_requests,
                  frame_timeout_seconds=frame_timeout)
            for turn in range(max_requests):
                raw = reader.read()
                if raw is None:
                    _emit("INCOMPLETE", reason="INPUT_CLOSED", final=broker.snapshot())
                    return 21
                request_id = f"turn-{turn:04d}"
                record = broker.step(raw, request_id)
                samples.append(dict(request_id=request_id, proposal_hex=raw.hex(), record=record))
                final = broker.snapshot()
                _emit("STEP", request_id=request_id, record=record, final=final)
                if final["state"] == 4:
                    result = publish(out, broker, samples, before,
                                     pre_sanitized=pre_sanitized, replayed=False)
                    write(out / "session.json", dict(
                        format=FORMAT, sources=before, max_requests=max_requests,
                        requests=len(samples), status="COMPLETE", pcs_authority=False,
                    ))
                    _emit("COMPLETE", final=result["final"],
                          wire_proof=result["captured_wire_proof"],
                          path_proof=result["captured_path_proof"])
                    return 0
            _emit("INCOMPLETE", reason="REQUEST_LIMIT", final=broker.snapshot())
            return 21
    except (OSError, ValueError, RuntimeError, sqlite3.Error, subprocess.SubprocessError) as error:
        # No positive verdict or continuation after a boundary failure. Exact
        # compiler diagnostics remain in the build logs; never echo input bytes.
        _emit("REFUSED_OR_UNAVAILABLE", reason=type(error).__name__)
        return 20
