"""Strict grammar of the generated part of a ClaimCheck proof file.  Standard library only.

A proof file is  CHECKER + MARKER + TAIL.  The kernel checks whatever TAIL says, so a TAIL that is
not exactly what the generator writes can define its own `run` and "prove" anything (see
../findings/RUNNER_TAIL_FORGERY.md).  `parse_tail` accepts exactly the language of
research/claimcheck_v1/lean.py::batch_tail and nothing else: one data numeral, claim records built
from literals only, one batch theorem, one fixed-form theorem per claim.  No other declaration,
command, comment or whitespace can occur.
"""
import re

NAT = r"(?:0|[1-9][0-9]*)"
INT = r"-?(?:0|[1-9][0-9]*)"
SAFE = r"[A-Za-z0-9 _.,:;()\[\]%/+\-#=<>&*!?@^|~]*"
BYTES = rf'(?:b "{SAFE}"|\[(?:{NAT}(?:, {NAT})*)?\])'
RAT = rf"\(\({INT} : Rat\) / [1-9][0-9]*\)"
CMP = r"\.(?:eq|ne|lt|le|gt|ge)"
COND = rf"(?:\.textEq \({BYTES}\) \({BYTES}\)|\.textNe \({BYTES}\) \({BYTES}\)|\.num \({BYTES}\) {CMP} {RAT})"
CONDS = rf"\[(?:{COND}(?:, {COND})*)?\]"
STAT = (rf"(?:\.count|\.sum|\.mean|\.median|\.min|\.max|\.varSample|\.sdSample|\.sdPop|\.sem|\.share {CONDS}"
        rf"|\.pearson \({BYTES}\)|\.olsSlope \({BYTES}\)|\.olsIntercept \({BYTES}\))")
COLUMN = rf"(?:none|some \({BYTES}\))"
NALIST = rf"\[(?:{BYTES}(?:, {BYTES})*)?\]"
VALUE = rf"(?:\(\.rat {RAT}\)|\(\.sqrt \({INT} : Int\) {RAT}\))"
OUTCOME = rf"(?:\.undefined \.[A-Za-z]+|\.checked \.(?:consistent|inconsistent) {VALUE} {NAT} {NAT})"

PREAMBLE = "open PCS.ClaimCheck\n\n"
SRC = re.compile(r"def pcs_src : Source := ⟨0x([0-9a-f]+), (0|[1-9][0-9]*)⟩\n\n")
OUTCOME_RE = re.compile(OUTCOME)
MAX_CLAIMS = 256
MAX_DATA_BYTES = 65536


class NotCanonical(ValueError):
    pass


def _claim(i: int):
    return re.compile(rf"def pcs_c{i} : Claim :=\n  \{{ column := {COLUMN},\n    filter := {CONDS},\n    stat := {STAT},\n"
                      rf"    naTokens := {NALIST},\n    scale := {RAT},\n    reported := {BYTES} \}}\n\n")


def parse_tail(tail: str):
    """Return (data bytes, [outcome literal per claim]) or raise NotCanonical."""
    if not tail.startswith(PREAMBLE):
        raise NotCanonical("the generated part does not start with the fixed preamble")
    pos = len(PREAMBLE)
    m = SRC.match(tail, pos)
    if not m:
        raise NotCanonical("no canonical data numeral")
    digits, size = m.group(1), int(m.group(2))
    if size > MAX_DATA_BYTES or not ((size == 0 and digits == "0") or (size > 0 and len(digits) == 2 * size)):
        raise NotCanonical("the data numeral is not the two-digits-per-byte dump of a file of the stated length")
    data = bytes.fromhex(digits) if size else b""
    pos = m.end()
    n = 0
    while n < MAX_CLAIMS:
        m = _claim(n).match(tail, pos)
        if not m:
            break
        pos, n = m.end(), n + 1
    if n == 0:
        raise NotCanonical("no claim in canonical form")
    head = "theorem pcs_batch : runAll pcs_src [" + ", ".join(f"pcs_c{i}" for i in range(n)) + "] =\n    ["
    if not tail.startswith(head, pos):
        raise NotCanonical("the batch theorem is missing or does not list exactly the claims defined")
    pos += len(head)
    outcomes = []
    for i in range(n):
        m = OUTCOME_RE.match(tail, pos)
        if not m:
            raise NotCanonical(f"outcome {i} of the batch theorem is not a literal outcome")
        outcomes.append(m.group(0))
        pos = m.end()
        sep = ",\n    " if i + 1 < n else "] := by decide +kernel\n\n"
        if not tail.startswith(sep, pos):
            raise NotCanonical("the batch theorem is not in canonical form")
        pos += len(sep)
    for i, outcome in enumerate(outcomes):
        theorem = (f"theorem pcs_claim_{i} : run pcs_src pcs_c{i} = {outcome} :=\n"
                   f"  run_of_runAll pcs_batch {i} rfl rfl\n#print axioms pcs_claim_{i}\n\n")
        if not tail.startswith(theorem, pos):
            raise NotCanonical(f"theorem pcs_claim_{i} is missing, altered or states another outcome than the batch theorem")
        pos += len(theorem)
    if pos != len(tail):
        raise NotCanonical("there is text after the last theorem")
    return data, outcomes
