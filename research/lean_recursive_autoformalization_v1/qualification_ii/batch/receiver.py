"""Research receiver for complete batches and replayable, data-only translator revisions."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from ... import set_algebra as algebra

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
MAX_BYTES, MAX_DEPTH, MAX_CASES, MAX_SOURCE = 131072, 32, 12, 1024
DIGEST = re.compile(r"[0-9a-f]{64}")
ID = re.compile(r"[a-z][a-z0-9_-]{0,31}")
MODEL = re.compile(r"[A-Za-z0-9._-]{1,96}")
PHRASE = re.compile(r"[A-Za-z]+(?: [A-Za-z]+){0,5}")
GENESIS = "0" * 64


class Rejected(ValueError):
    """No batch receipt or promotion was issued."""


def require(ok, message):
    if not ok:
        raise Rejected(message)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, allow_nan=False,
                      separators=(",", ":")).encode("ascii")


def digest(value) -> str:
    return sha(canonical(value))


def _unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def _no_float(_):
    raise Rejected("integers only")


def _integer(s):
    require(len(s) <= 6, "integer limit")
    return int(s)


def decode(raw):
    """Bound bytes and nesting before the JSON decoder allocates nested objects."""
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, "wire size")
    try:
        s = raw.decode("utf-8", errors="strict")
        depth, quoted, escape = 0, False, False
        for c in s:
            if quoted:
                if escape:
                    escape = False
                elif c == "\\":
                    escape = True
                elif c == '"':
                    quoted = False
            elif c == '"':
                quoted = True
            elif c in "[{":
                depth += 1
                require(depth <= MAX_DEPTH, "JSON depth")
            elif c in "]}":
                depth -= 1
                require(depth >= 0, "JSON nesting")
        return json.loads(s, object_pairs_hook=_unique, parse_int=_integer,
                          parse_float=_no_float, parse_constant=_no_float)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Rejected("invalid UTF-8 JSON") from exc


def fields(obj, keys):
    require(type(obj) is dict and set(obj) == set(keys.split()), "object schema")


def exact_ids(requested, received):
    require(all(type(i) is str and ID.fullmatch(i) for i in received), "invalid id")
    require(len(received) == len(set(received)), "duplicate id")
    extra, missing = set(received) - set(requested), set(requested) - set(received)
    require(not extra and not missing, f"identifier coverage (extra={sorted(extra)}, missing={sorted(missing)})")


def validate(expr):
    try:
        algebra.validate(expr)
    except (TypeError, ValueError, KeyError, IndexError) as exc:
        raise Rejected("invalid typed set contract") from exc


def source_bytes(s):
    require(type(s) is str and 0 < len(s) <= MAX_SOURCE, "source limit")
    try:
        return s.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise Rejected("invalid source text") from exc


def open_cases(raw, anchor, split):
    """The anchor and split come from the reviewer's local policy."""
    require(sha(raw) == anchor and split in ("development", "final"), "reviewer anchor")
    obj = decode(raw)
    fields(obj, "schema split cases")
    require(obj["schema"] == "set-batch/cases-v1" and obj["split"] == split, "case split")
    cases = obj["cases"]
    require(type(cases) is list and 0 < len(cases) <= MAX_CASES, "case count")
    for case in cases:
        fields(case, "id source reference")
        source_bytes(case["source"])
        validate(case["reference"])
    ids = [c["id"] for c in cases]
    exact_ids(ids, ids)
    return cases


def open_revision(raw):
    rev = decode(raw)
    fields(rev, "schema model rules")
    require(rev["schema"] == "set-batch/revision-v1", "revision schema")
    require(type(rev["model"]) is str and MODEL.fullmatch(rev["model"]), "model id")
    rules = rev["rules"]
    require(type(rules) is list and len(rules) <= 8, "rule count")
    for rule in rules:
        require(type(rule) is list and len(rule) == 2 and
                all(type(p) is str and len(p) <= 48 and PHRASE.fullmatch(p) for p in rule),
                "revision phrases")
    return rev


def translate(source, rev):
    for before, after in rev["rules"]:
        source = re.sub(r"\b" + re.escape(before) + r"\b", after, source)
        require(len(source) <= MAX_SOURCE, "rewrite exceeds source limit")
    return algebra.parse_english(source)


def verifier_digest():
    # Local reviewer-owned sources. Never read a path supplied by a revision.
    paths = [Path(__file__), PROJECT / "set_algebra.py", PROJECT / "set_algebra_kernel.py",
             PROJECT / "lean/PCS/V2/SetAlgebra.lean", PROJECT / "lean/lean-toolchain"]
    return digest({str(p.relative_to(PROJECT)): sha(p.read_bytes()) for p in paths})


def context(raw_cases, raw_revision, cases, rev, parent, generation):
    require(type(parent) is str and DIGEST.fullmatch(parent), "parent digest")
    require(type(generation) is int and 0 <= generation <= 2 * MAX_CASES, "generation")
    sources = [(c["id"], sha(source_bytes(c["source"]))) for c in cases]
    return {"schema": "set-batch/response-v1", "cases_sha256": sha(raw_cases),
            "revision_sha256": sha(raw_revision), "model": rev["model"],
            "parent_sha256": parent, "generation": generation,
            "sources_sha256": digest(sources), "verifier_sha256": verifier_digest()}


def response(raw_cases, anchor, split, raw_revision, parent=GENESIS, generation=0):
    """Convenience producer. Does not send trusted references to the translator."""
    cases = open_cases(raw_cases, anchor, split)
    rev = open_revision(raw_revision)
    header = context(raw_cases, raw_revision, cases, rev, parent, generation)
    items = [{"id": c["id"], "source_sha256": sha(source_bytes(c["source"])),
              "contract": translate(c["source"], rev)} for c in cases]
    return canonical({**header, "items": items})


def receive(raw_cases, anchor, split, raw_revision, raw_response, parent=GENESIS, generation=0):
    """Issue one receipt only after the entire response validates and replays."""
    obj = decode(raw_response)
    require(canonical(obj) == raw_response, "noncanonical response bytes")
    cases = open_cases(raw_cases, anchor, split)
    rev = open_revision(raw_revision)
    header = context(raw_cases, raw_revision, cases, rev, parent, generation)
    fields(obj, " ".join([*header, "items"]))
    # JSON true and 1 compare equal in Python. Compare canonical types as well.
    require(canonical({k: obj[k] for k in header}) == canonical(header), "response provenance")
    items = obj["items"]
    require(type(items) is list and len(items) <= MAX_CASES, "item count")
    for item in items:
        fields(item, "id source_sha256 contract")
    requested, received = [c["id"] for c in cases], [row["id"] for row in items]
    exact_ids(requested, received)
    require(requested == received, "noncanonical item order")
    for c, row in zip(cases, items, strict=True):
        require(row["source_sha256"] == sha(source_bytes(c["source"])), "stale source")
        if row["contract"] is not None:
            validate(row["contract"])
    for c, row in zip(cases, items, strict=True):
        actual = translate(c["source"], rev)
        require(canonical(row["contract"]) == canonical(actual), "revision output mismatch")
    outcomes = []
    for c, row in zip(cases, items, strict=True):
        candidate = row["contract"]
        if candidate is None:
            review = {"correspondence": "ABSTAIN", "proof": "NOT_CHECKED"}
        else:
            review = algebra.check_pair(c["reference"], candidate)
            require(review["elaborated"] is True and review["correspondence"] in ("EQUIVALENT", "DIFFERENT"),
                    f"kernel review incomplete for {c['id']}")
        corresponds = review["correspondence"] == "EQUIVALENT"
        credit = int(corresponds) + int(corresponds and review["proof"] == "KERNEL_CHECKED")
        outcomes.append({"id": c["id"], "source_sha256": row["source_sha256"],
                         "reference_sha256": digest(c["reference"]),
                         "candidate_sha256": digest(candidate), "review": review, "credit": credit})
    return {"schema": "set-batch/receipt-v1", "request": header, "response_sha256": sha(raw_response),
            "outcomes": outcomes, "score": sum(row["credit"] for row in outcomes)}


@dataclass(frozen=True)
class Submission:
    revision: bytes
    response: bytes


def check_improvement(previous, current):
    require(current["score"] > previous["score"], "no certified gain")
    require(all(a["id"] == b["id"] and a["credit"] <= b["credit"]
                for a, b in zip(previous["outcomes"], current["outcomes"], strict=True)),
            "case regression")


def replay(raw_cases, anchor, baseline_revision_anchor, history):
    """Replay all submissions from the trusted baseline. No supplied status is used."""
    require(type(history) in (list, tuple) and 1 <= len(history) <= 2 * MAX_CASES + 1,
            "history length")
    require(sha(history[0].revision) == baseline_revision_anchor, "baseline revision")
    previous, parent = None, GENESIS
    for generation, submission in enumerate(history):
        current = receive(raw_cases, anchor, "development", submission.revision,
                          submission.response, parent, generation)
        if previous is not None:
            check_improvement(previous, current)
        parent, previous = digest(current), current
    return previous


def verify_receipt(expected_receipt, raw_cases, anchor, baseline_revision_anchor, history):
    """Detached exact receipt check. Any modified review or digest rejects."""
    actual = replay(raw_cases, anchor, baseline_revision_anchor, history)
    require(canonical(actual) == expected_receipt, "supplied receipt disagrees with replay")
    return actual


def advance(raw_cases, anchor, baseline_revision_anchor, history, current_head, proposal):
    """The caller supplies its independently retained current development receipt digest."""
    previous = replay(raw_cases, anchor, baseline_revision_anchor, history)
    require(digest(previous) == current_head, "stale champion")
    candidate = receive(raw_cases, anchor, "development", proposal.revision, proposal.response,
                        current_head, len(history))
    check_improvement(previous, candidate)
    return candidate


def measure_final(final_cases, final_anchor, dev_cases, dev_anchor, baseline_anchor, history, head):
    """Independently measure the verified champion. Final scores never enter promotion."""
    champion = replay(dev_cases, dev_anchor, baseline_anchor, history)
    require(digest(champion) == head, "stale champion")
    development = open_cases(dev_cases, dev_anchor, "development")
    reserved = open_cases(final_cases, final_anchor, "final")
    require({c["id"] for c in development}.isdisjoint(c["id"] for c in reserved) and
            {c["source"] for c in development}.isdisjoint(c["source"] for c in reserved),
            "final overlaps development")
    revision = history[-1].revision
    wire = response(final_cases, final_anchor, "final", revision, head, len(history) - 1)
    return receive(final_cases, final_anchor, "final", revision, wire, head, len(history) - 1)
