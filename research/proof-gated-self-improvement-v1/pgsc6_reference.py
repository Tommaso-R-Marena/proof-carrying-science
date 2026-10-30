"""Independent PGSC6 witness-certificate reference parser and strong-gate replay.

EXPERIMENTAL ONLY: the checks are Python, not Lean kernel proofs.
The trusted verification policy must be independently pinned by the host;
a policy supplied by an untrusted proposer proves nothing about deployment.
No signature, hash authenticity, storage isolation, rollback protection or
promotion authority is provided.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from pgsi2_wide_runtime import Arch, Unit, Wide, WireReject, decode as decode_wide
from universal_relu import (
    Term, Net, universal_correctness_preserved, exact_interval_max_error,
)

_CANON = re.compile(rb"(?:0|-?[1-9][0-9]*)\Z", re.ASCII)
_TAG = b"PGSC6|"


class CertificateReject(ValueError):
    pass


@dataclass(frozen=True)
class Policy:
    arch: Arch
    target: Wide
    corpus: tuple[int, ...]
    low: int
    high: int

    def __post_init__(self) -> None:
        if type(self.arch) is not Arch or type(self.target) is not Wide:
            raise TypeError("expected independently pinned Arch and Wide")
        if type(self.corpus) is not tuple or not all(type(x) is int for x in self.corpus):
            raise TypeError("expected exact integer corpus")
        if type(self.low) is not int or type(self.high) is not int:
            raise TypeError("expected exact integer interval")


@dataclass(frozen=True)
class Cert:
    version: int
    predicate: int
    max_width: int
    bound: int
    generation: int
    low: int
    high: int
    gain: int
    incumbent_loss: int
    candidate_loss: int
    error_witness: int
    error_level: int
    corpus: tuple[int, ...]
    target: Wide
    incumbent: bytes
    candidate: bytes


def _integer(token: bytes) -> int:
    if not _CANON.fullmatch(token):
        raise CertificateReject("noncanonical ASCII integer")
    try:
        return int(token)
    except ValueError as error:
        raise CertificateReject("host integer conversion limit") from error


def _model(values: list[int]) -> Wide:
    if not values or (len(values) - 1) % 3:
        raise CertificateReject("invalid network parameter count")
    return Wide(tuple(Unit(*values[i:i + 3]) for i in range(1, len(values), 3)),
                values[0])


def decode_certificate(raw: bytes, *, max_bytes: int | None = None) -> Cert:
    if type(raw) is not bytes:
        raise TypeError("PGSC6 must be exact bytes")
    if max_bytes is not None:
        if type(max_bytes) is not int or max_bytes < 0:
            raise ValueError("bad host resource cap")
        if len(raw) > max_bytes:
            raise CertificateReject("host resource cap exceeded")
    if not raw.startswith(_TAG):
        raise CertificateReject("wrong PGSC6 tag")
    numbers = [_integer(part) for part in raw[len(_TAG):].split(b"|")]
    if len(numbers) < 16:
        raise CertificateReject("truncated certificate")
    fields, remainder = numbers[:12], numbers[12:]
    for i in (0, 1, 2, 3, 4, 8, 9, 11):
        if fields[i] < 0:
            raise CertificateReject("negative unsigned field")
    blocks = []
    for _ in range(4):
        if not remainder or remainder[0] < 0 or remainder[0] > len(remainder) - 1:
            raise CertificateReject("invalid length-prefixed block")
        length = remainder[0]
        blocks.append(remainder[1:length + 1])
        remainder = remainder[length + 1:]
    if remainder:
        raise CertificateReject("trailing fields")
    corpus, target_values, incumbent_values, candidate_values = blocks
    if any(z < 0 or z > 255 for z in incumbent_values + candidate_values):
        raise CertificateReject("embedded bytes out of range")
    return Cert(*fields, tuple(corpus), _model(target_values),
                bytes(incumbent_values), bytes(candidate_values))


def _reference(net: Wide) -> Net:
    return Net(tuple(Term(u.output, u.weight, u.bias) for u in net.units),
               net.output_bias)


def _loss(net: Wide, policy: Policy) -> int:
    return sum(abs(net.predict(x) - policy.target.predict(x)) for x in policy.corpus)


def reference_certificate_passes(raw: bytes, policy: Policy, generation: int,
                                 active: bytes) -> bool:
    """Fail-closed Python reference decision; NO protected authority claim.

    The witness's incumbent error is checked at one input and the candidate's
    exact interval maximum is recomputed independently. This corresponds to
    the witness logic of V6, but is not a proof of Python implementation.
    """
    if type(generation) is not int or generation < 0 or type(active) is not bytes:
        raise TypeError("trusted incumbent requires exact generation and bytes")
    try:
        cert = decode_certificate(raw)
        if (cert.version, cert.predicate, cert.max_width, cert.bound,
            cert.generation, cert.low, cert.high) != (
                6, 1, policy.arch.max_width, policy.arch.bound, generation,
                policy.low, policy.high):
            return False
        if cert.target != policy.target or cert.corpus != policy.corpus:
            return False
        if cert.incumbent != active:
            return False
        incumbent = decode_wide(cert.incumbent, policy.arch)
        candidate = decode_wide(cert.candidate, policy.arch)
        if cert.gain not in policy.corpus:
            return False
        if incumbent.predict(cert.gain) == policy.target.predict(cert.gain):
            return False
        if candidate.predict(cert.gain) != policy.target.predict(cert.gain):
            return False
        if _loss(incumbent, policy) != cert.incumbent_loss:
            return False
        if _loss(candidate, policy) != cert.candidate_loss:
            return False
        if cert.candidate_loss >= cert.incumbent_loss:
            return False
        old = _reference(incumbent)
        new = _reference(candidate)
        target = _reference(policy.target)
        if not universal_correctness_preserved(old, new, target).passes:
            return False
        if policy.low <= policy.high:
            if not policy.low <= cert.error_witness <= policy.high:
                return False
            if (abs(incumbent.predict(cert.error_witness) -
                    policy.target.predict(cert.error_witness)) != cert.error_level):
                return False
            if exact_interval_max_error(new, target, policy.low,
                                        policy.high)[0] > cert.error_level:
                return False
        return True
    except (WireReject, CertificateReject, ValueError, OverflowError):
        return False
