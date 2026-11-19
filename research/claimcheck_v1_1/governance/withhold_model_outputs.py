"""Licensing disposition of the recorded model outputs: an inventory, and (only on the owner's decision) withholding.

    python -m research.claimcheck_v1_1.governance.withhold_model_outputs --plan
    python -m research.claimcheck_v1_1.governance.withhold_model_outputs --inventory docs/integration/claimcheck/model_outputs_inventory.json
    python -m research.claimcheck_v1_1.governance.withhold_model_outputs --apply --groups N,C --decision "<owner decision reference>"

`--plan` (the default) writes nothing. It lists every recorded response with its group (G Gemini,
N Nemotron, C Cohere), its identity and the action the recommended disposition proposes.

`--inventory PATH` writes the same as JSON. It holds every file's SHA-256, size, model, finish
reason, prompt digest, token usage and the SHA-256 and length of the model text, but never the text.

`--apply` replaces, in the working tree only, each file of the named groups with a provenance stub:

* the same path;
* every identifying field of the original, and the original file's digest and size;
* the reason, and where the original is kept.

The cache key is kept as `cache_key`, not `key`. The frozen v1 cache lookup
(`claimcheck_v1.providers.complete`) serves any file whose `key` matches and then reads its text; a
stub with `key` would be served and crash the reader. Under `cache_key` the lookup misses, and with
network use off the frozen code reports "no cached response" and leaves that arm out.

It refuses to run without `--decision`, and it never touches Git history, frozen files or files
outside `results/*/model_responses/`. The originals must first be archived privately by the owner;
the stub's digest lets anyone with the archive verify it. Not run by the assistant.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PATTERN = "research/claimcheck_v1/benchmark/results/*/model_responses/*.json"
TERMS = {
    "G": {"provider_terms": "Gemini API Additional Terms of Service, effective 2026-03-23 (https://ai.google.dev/gemini-api/terms)",
          "status": "redistribution supported on the evidence", "action": "keep"},
    "N": {"provider_terms": "OpenRouter Terms of Service (last updated 2026-08-31) -> NVIDIA API Trial Terms of Service; model license OpenMDW-1.1 per NVIDIA NGC",
          "status": "not established: trial terms allow internal testing and evaluation, not production", "action": "withhold pending confirmation"},
    "C": {"provider_terms": "OpenRouter Terms of Service (last updated 2026-08-31) -> Cohere Terms of Use (last updated 2022-09-07)",
          "status": "not permitted on the evidence: publishing and distributing Content prohibited", "action": "withhold"},
}


def group(model: str) -> str:
    if model.startswith("gemini"):
        return "G"
    if model.startswith("nvidia/"):
        return "N"
    if model.startswith("cohere/"):
        return "C"
    raise SystemExit(f"unknown model {model!r}: classify it before any disposition")


KEEP = ("group", "provider", "model", "key", "prompt_sha256", "usage", "finish", "original_sha256", "original_bytes", "text_sha256",
        "text_characters", "request_identifier", "recorded_in_commit", "recorded_in_repository_utc", "provider_terms", "status")


def first_recorded(path: str) -> tuple[str | None, str | None]:
    """The commit that first added the file, and its commit time.  The client recorded no generation time, so this is an
    upper bound on when the response was generated."""
    try:
        rows = subprocess.check_output(["git", "log", "--diff-filter=A", "--format=%H %cI", "--", path], cwd=ROOT, text=True).split("\n")
    except (OSError, subprocess.CalledProcessError):
        return None, None
    rows = [r for r in rows if r.strip()]
    if not rows:
        return None, None
    commit, when = rows[-1].split(" ", 1)
    return commit, when


def records() -> list[dict]:
    out = []
    for name in sorted(glob.glob(str(ROOT / PATTERN))):
        raw = Path(name).read_bytes()
        d = json.loads(raw)
        rel = str(Path(name).relative_to(ROOT))
        if d.get("withheld"):                                      # a provenance stub: it carries every inventoried field
            out.append({"path": rel, "withheld": True, **{k: d.get(STUB_NAME.get(k, k)) for k in KEEP}, "split": Path(name).parts[-3],
                        "action": TERMS[d["group"]]["action"]})
            continue
        text = (d.get("text") or "").encode("utf-8")
        g = group(d.get("model", ""))
        commit, when = first_recorded(rel)
        out.append({"path": rel, "group": g, "provider": d.get("provider"), "model": d.get("model"),
                    "key": d.get("key"), "prompt_sha256": d.get("prompt_sha256"), "usage": d.get("usage"), "finish": d.get("finish"),
                    "original_sha256": hashlib.sha256(raw).hexdigest(), "original_bytes": len(raw),
                    "text_sha256": hashlib.sha256(text).hexdigest(), "text_characters": len(text.decode("utf-8")),
                    "request_identifier": d.get("id") or d.get("request_id") or "not recorded by the client",
                    "recorded_in_commit": commit, "recorded_in_repository_utc": when,
                    "split": Path(name).parts[-3], **{k: v for k, v in TERMS[g].items()}})
    return out


# the frozen cache lookup serves a file whose "key" matches; a stub must not match (module docstring)
STUB_NAME = {"key": "cache_key"}


def stub(rec: dict, decision: str) -> dict:
    return {"withheld": True, **{STUB_NAME.get(k, k): rec[k] for k in KEEP},
            "reason": "Rights to redistribute this model output are not established (see docs/integration/claimcheck/MODEL_OUTPUT_LICENSING.md).",
            "original": "kept privately by the owner; verify a copy against original_sha256",
            "decision": decision}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--inventory")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--groups", default="N,C")
    ap.add_argument("--decision")
    a = ap.parse_args(argv)
    recs = records()
    if a.inventory:
        Path(a.inventory).write_text(json.dumps({"what": "Inventory of the recorded model outputs (no model text). Generated by "
                                                         "research/claimcheck_v1_1/governance/withhold_model_outputs.py.",
                                                 "files": recs, "by_group": {g: sum(1 for r in recs if r.get("group") == g) for g in "GNC"}},
                                                indent=1) + "\n", encoding="utf-8")
    if a.apply:
        if not (a.decision and a.decision.strip()):
            raise SystemExit("--apply needs --decision: the owner's recorded decision (L2/L3)")
        groups = set(a.groups.split(","))
        for r in recs:
            if r.get("group") in groups and not r.get("withheld"):
                (ROOT / r["path"]).write_text(json.dumps(stub(r, a.decision.strip()), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if a.plan or not (a.inventory or a.apply):
        for g in "GNC":
            rs = [r for r in recs if r.get("group") == g]
            print(f"{g}: {len(rs)} files, action: {TERMS[g]['action']} ({TERMS[g]['status']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
