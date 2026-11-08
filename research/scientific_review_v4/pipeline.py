"""Snapshot-only scientific review with bounded analysis and independent replay.

The unchanged v2 intake owns original bytes and its host-private check cache.
This additive package never executes imported code or treats prose as policy.
"""
from __future__ import annotations

import base64
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile

from pcs.jsonio import strict_json_loads
from research.scientific_intake_v1.intake import canonical, _regular, safe_name, MAX_FILE, MAX_TOTAL, MAX_FILES
from research.scientific_intake_v1.checks import bound_bytes
from research.scientific_understanding_v2 import pipeline as previous

FORMAT = "pcs-independent-scientific-review-package-v4"
MEMBERS = frozenset({"interpretation.json", "checks.json", "correspondence.json", "summary.json", "context.json", "review.html"})
MAX_REQUEST = 96 * 1024**2
MAX_RESPONSE = 64 * 1024**2
SHA = re.compile(r"[0-9a-f]{64}\Z")
STATUSES = frozenset({"UNKNOWN", "REFUTED", "SOURCE_DECLARATION_CHECKED", "SOURCE_REPORT_CHECKED", "SCOPED_EQUATION_CHECKED", "REPRODUCED_COMPUTATION", "REPRODUCED_ROUNDED_COMPUTATION", "KERNEL_CHECKED_ABSTRACT_RESIDUAL_SEMANTICS"})


def context():
    root = Path(__file__).resolve().parent
    return {"schema": "pcs-independent-scientific-review-context-v4", "parent": previous.context(),
            "sources": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob("*.py"))},
            "formal": {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root / "formal").rglob("*.lean"))},
            "authority": False, "training_policy": "DENIED_BY_DEFAULT"}


def _write(path, value):
    Path(path).write_bytes(canonical(value) + b"\n")


def stable(value):
    """Only measured timing and receipt timestamps are comparison-volatile."""
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items() if k not in {"seconds", "checked_at_utc", "checked_at", "duration_seconds", "elapsed_seconds"}}
    if isinstance(value, list):
        return [stable(v) for v in value]
    return value


def snapshot_artifacts(folder):
    inventory = previous.portable_inventory(Path(folder) / "intake")
    return inventory, {a["path"]: bound_bytes(a) for a in inventory["artifacts"]}


def _portable(inventory):
    # Snapshot paths are private host locations, never a portable contract.
    return {**inventory, "artifacts": [{k: v for k, v in a.items() if k != "snapshot_path"} for a in inventory["artifacts"]]}


def analyze_snapshots(artifacts, inventory, check=False, formal_check=False):
    """Fixed worker implementation; inputs are bound bytes, not source paths."""
    from . import semantics, documents, schema, grounding, correspondence, workflow, simulation
    from research.scientific_semantics_v3.checks import check_claim
    meaning = documents.augment(semantics.interpret_artifacts(artifacts), inventory)
    validation = schema.validate_interpretation(meaning, artifacts, inventory=inventory)
    if not validation.get("valid"):
        raise ValueError("invalid derived interpretation: " + json.dumps(validation.get("errors", []))[:2000])
    if any(not grounding.bound_source(c["source"], artifacts, inventory) for c in meaning["claims"]):
        raise ValueError("ungrounded interpretation claim")
    graph = correspondence.analyze(meaning, artifacts)
    checks = []
    if check:
        for claim in meaning["claims"]:
            if claim["source"].get("transformation", {}).get("kind") == "adapter_extracted_text":
                checks.append({"id": "check-" + claim["id"], "claim_id": claim["id"], "checker": "adapter-extracted-source-v4", "status": "UNKNOWN", "authority": False, "scientific_meaning": "OPEN", "source_sha256": claim["source"]["sha256"], "reason": "The quotation is bound to adapter-extracted text; no independent scientific or original-byte declaration checker supports this transformed claim."})
            else:
                checks.append(check_claim(claim, artifacts))
        checks.extend(workflow.analyze(artifacts)["checks"])
        checks.append(simulation.reconstruct(artifacts))
        if formal_check:
            from .formal import verify
            receipt = verify()
            if receipt.get("status") == "VERIFIED":
                receipt = {**receipt, "status": "KERNEL_CHECKED_ABSTRACT_RESIDUAL_SEMANTICS", "version": receipt.get("compiler_version", receipt.get("version", ""))}
            if receipt.get("status") not in {"KERNEL_CHECKED_ABSTRACT_RESIDUAL_SEMANTICS", "UNKNOWN", "REFUTED"}:
                raise ValueError("unrecognized formal verifier result")
            receipt["id"] = "formal-v4-residual-semantics"
            checks.append(receipt)
    _validate_checks(checks, check, formal_check)
    return {"interpretation": meaning, "correspondence": graph, "checks": checks}


def _worker_environment(root, temporary):
    # Import locations are discovered from installed dependencies. No imported
    # research project path, ambient Python path or credentials enter the child.
    paths = [str(root)]
    for name in ("numpy", "scipy"):
        spec = importlib.util.find_spec(name)
        if spec and spec.origin:
            location = str(Path(spec.origin).resolve().parent.parent)
            if location not in paths:
                paths.append(location)
    lean = shutil.which("lean")
    path = (str(Path(lean).resolve().parent) + os.pathsep if lean else "") + "/usr/bin:/bin"
    return {"PATH": path, "PYTHONPATH": os.pathsep.join(paths), "LANG": "C.UTF-8", "TMPDIR": temporary,
            "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "LEAN_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1"}


def bounded_stage(artifacts, inventory, check=False, formal_check=False):
    _authorize(check, formal_check)
    if type(artifacts) is not dict or len(artifacts) > MAX_FILES:
        raise ValueError("semantic file-count bound")
    total = 0
    for name, raw in artifacts.items():
        safe_name(name)
        if type(raw) is not bytes or len(raw) > MAX_FILE:
            raise ValueError("semantic file-byte bound")
        total += len(raw)
    if total > MAX_TOTAL:
        raise ValueError("semantic total-byte bound")
    payload = canonical({"artifacts": {n: base64.b64encode(raw).decode("ascii") for n, raw in artifacts.items()}, "inventory": _portable(inventory), "check": check, "formal_check": formal_check})
    if len(payload) > MAX_REQUEST:
        raise ValueError("semantic request bound")
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="pcs-review-v4-worker-") as temporary:
        process = subprocess.Popen([sys.executable, "-m", "research.scientific_review_v4.worker"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=root, env=_worker_environment(root, temporary), start_new_session=True)
        try:
            out, err = process.communicate(payload, timeout=100)
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
            raise
        if process.returncode or len(out) > MAX_RESPONSE:
            detail = err.decode("utf-8", errors="replace")[-1500:]
            raise ValueError("bounded v4 worker failed; no result accepted: " + detail)
        value = strict_json_loads(out.decode("utf-8"))
        if type(value) is not dict or set(value) != {"interpretation", "checks", "correspondence"} or type(value["interpretation"]) is not dict or type(value["correspondence"]) is not dict or type(value["checks"]) is not list:
            raise ValueError("invalid v4 worker result")
        _validate_checks(value["checks"], check, formal_check)
        return value


def _authorize(check, formal_check):
    if type(check) is not bool or type(formal_check) is not bool:
        raise ValueError("check authorizations must be Boolean")
    if formal_check and not check:
        raise ValueError("formal checks require check authorization")


def _validate_checks(checks, authorized, formal_authorized):
    _authorize(authorized, formal_authorized)
    if type(checks) is not list or (not authorized and checks):
        raise ValueError("unauthorized or malformed check list")
    ids = []
    for record in checks:
        if type(record) is not dict or not isinstance(record.get("id"), str) or record.get("status") not in STATUSES or record.get("authority") is not False or record.get("scientific_meaning") != "OPEN":
            raise ValueError("unrecognized check status or fabricated authority")
        if record.get("production_authority") not in (None, False, "NONE") or record.get("scientific_meanings_certified", 0) != 0:
            raise ValueError("fabricated scientific authority")
        ids.append(record["id"])
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate check record")
    if ("formal-v4-residual-semantics" in ids) != formal_authorized:
        raise ValueError("missing or unauthorized formal receipt")


def summary_for(meaning, checks, graph, authorized, formal_authorized=False):
    _authorize(authorized, formal_authorized)
    return {"schema": "pcs-independent-scientific-review-summary-v4", "artifacts": len(meaning["artifacts"]),
            "claims": len(meaning["claims"]), "symbols": len(meaning["symbols"]), "obligations": len(meaning["obligations"]), "unresolved": len(meaning["unresolved"]),
            "checks": dict(sorted(Counter(c["status"] for c in checks).items())),
            "correspondence_records": {k: len(v) for k, v in sorted(graph.items()) if isinstance(v, list)},
            "authorized_checks": authorized, "authorized_formal_checks": formal_authorized,
            "scientific_meanings_certified": 0, "authority": False, "training_examples_admitted": 0, "training_policy": "DENIED_BY_DEFAULT",
            "source_download_prefix": "parent/intake/objects/", "learned_routing": "disabled; deterministic interpretation",
            "researcher_action": "Review exact sources, extraction transformations, conditions and open scientific assumptions before relying on a conclusion."}


def _census(directory):
    """Reject symlinks and special files, including unlisted physical members."""
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("evidence root must be a regular directory")
    found = set()
    count = 0
    for root, dirs, files in os.walk(directory, followlinks=False):
        count += len(dirs) + len(files)
        if count > 4096:
            raise ValueError("evidence physical-census bound")
        for name in dirs + files:
            path = Path(root) / name
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise ValueError("symlink or special evidence member")
        for name in files:
            found.add((Path(root) / name).relative_to(directory).as_posix())
    return found


def run(source, output, *, check=False, formal_check=False, cache_dir=None):
    _authorize(check, formal_check)
    source, output = Path(source).absolute(), Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("refuse evidence overwrite")
    if output.resolve().is_relative_to(source.resolve()):
        raise ValueError("output cannot be inside source")
    if cache_dir and (Path(cache_dir).resolve().is_relative_to(source.resolve()) or Path(cache_dir).resolve().is_relative_to(output.resolve())):
        raise ValueError("cache must be host-owned outside source and evidence")
    initial_context = context()
    output.mkdir(parents=True, mode=0o700)
    previous.run(source, output / "parent", check=check, cache_dir=cache_dir)
    inventory, artifacts = snapshot_artifacts(output / "parent")
    result = bounded_stage(artifacts, inventory, check, formal_check)
    if context() != initial_context:
        raise ValueError("source or runtime context changed during analysis")
    meaning, checks, graph = result["interpretation"], result["checks"], result["correspondence"]
    summary = summary_for(meaning, checks, graph, check, formal_check)
    for name, value in [("interpretation", meaning), ("checks", checks), ("correspondence", graph), ("summary", summary), ("context", initial_context)]:
        _write(output / (name + ".json"), value)
    from .review import render
    (output / "review.html").write_text(render(meaning, checks, inventory, summary), encoding="utf-8")
    files = {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in sorted(_census(output))}
    _write(output / "manifest.json", {"format": FORMAT, "files": files, "authority": False, "training_policy": "DENIED_BY_DEFAULT"})
    return summary


def replay(directory, *, recheck=True, expected_manifest_sha256=None):
    if type(recheck) is not bool:
        raise ValueError("recheck must be Boolean")
    directory = Path(directory).absolute()
    census = _census(directory)
    raw = _regular(directory / "manifest.json", 2 * 1024**2)
    manifest_sha = hashlib.sha256(raw).hexdigest()
    if expected_manifest_sha256 is not None and expected_manifest_sha256 != manifest_sha:
        raise ValueError("pinned manifest changed")
    manifest = strict_json_loads(raw.decode("utf-8"))
    if type(manifest) is not dict or set(manifest) != {"format", "files", "authority", "training_policy"} or manifest["format"] != FORMAT or manifest["authority"] is not False or manifest["training_policy"] != "DENIED_BY_DEFAULT" or type(manifest["files"]) is not dict:
        raise ValueError("invalid v4 manifest")
    files = manifest["files"]
    if not MEMBERS <= files.keys() or "parent/manifest.json" not in files or len(files) > 1024 or census != set(files) | {"manifest.json"}:
        raise ValueError("evidence physical census mismatch")
    blobs, total = {}, 0
    for name, sha in files.items():
        safe_name(name)
        if name not in MEMBERS and not name.startswith("parent/"):
            raise ValueError("unknown v4 package member")
        if not isinstance(sha, str) or SHA.fullmatch(sha) is None:
            raise ValueError("invalid evidence digest")
        data = _regular(directory / name, 64 * 1024**2)
        total += len(data)
        if total > 512 * 1024**2 or hashlib.sha256(data).hexdigest() != sha:
            raise ValueError("changed or oversized evidence")
        blobs[name] = data
    # Re-extract every original through the unchanged parent before consuming
    # its inventory. No v4 result cache is read on either replay path.
    parent = previous.replay(directory / "parent", recheck=recheck, expected_manifest_sha256=files["parent/manifest.json"])
    nested = strict_json_loads(blobs["parent/manifest.json"].decode("utf-8"))
    if {name for name in files if name.startswith("parent/")} != {"parent/" + name for name in nested["files"]} | {"parent/manifest.json"}:
        raise ValueError("nested parent census mismatch")
    initial_context = context()
    if initial_context != strict_json_loads(blobs["context.json"].decode("utf-8")):
        raise ValueError("source or runtime context changed")
    summary = strict_json_loads(blobs["summary.json"].decode("utf-8"))
    checks = strict_json_loads(blobs["checks.json"].decode("utf-8"))
    if type(summary) is not dict:
        raise ValueError("invalid review summary")
    authorized, formal_authorized = summary.get("authorized_checks"), summary.get("authorized_formal_checks")
    _validate_checks(checks, authorized, formal_authorized)
    inventory, artifacts = snapshot_artifacts(directory / "parent")
    # Even integrity-only replay rederives the complete bounded v4 check set:
    # resealing hashes cannot turn a missing, forged or unsupported result into
    # an accepted record. The parent retains its historical recheck contract.
    fresh = bounded_stage(artifacts, inventory, authorized, formal_authorized)
    if context() != initial_context:
        raise ValueError("source or runtime context changed during replay")
    meaning, graph = fresh["interpretation"], fresh["correspondence"]
    if meaning != strict_json_loads(blobs["interpretation.json"].decode("utf-8")):
        raise ValueError("interpretation replay mismatch")
    if graph != strict_json_loads(blobs["correspondence.json"].decode("utf-8")):
        raise ValueError("correspondence replay mismatch")
    if stable(fresh["checks"]) != stable(checks):
        raise ValueError("independent v4 check replay mismatch or missing record")
    if summary != summary_for(meaning, checks, graph, authorized, formal_authorized):
        raise ValueError("summary replay mismatch")
    from .review import render
    if blobs["review.html"].decode("utf-8") != render(meaning, checks, inventory, summary):
        raise ValueError("review display replay mismatch")
    return {"status": "REPLAYED" if recheck and authorized else "INTEGRITY_ONLY", "replayed_checks": len(checks) if recheck and authorized else 0,
            "v4_checks_independently_recomputed": len(fresh["checks"]), "parent_replay": parent, "cache_used": False, "authority": False, "scientific_meaning": "OPEN", "manifest_sha256": manifest_sha}
