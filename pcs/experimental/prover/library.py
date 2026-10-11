"""Kernel-checked reusable lemmas, reconstructed from typed goals and actions.

No serialized receipt, proposed declaration, imported code or success flag is
trusted. Each library is rebuilt and axiom-audited in a fresh Lean process. Its
definitions are replayed before each independent request, including final proof
checking. Library construction is experimental and grants no PCS authority.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time

from .data import structural_fingerprint
from .environment import LeanEnvironment, candidates, render_action, _symbolic_priority, ROOT
from .induction_ir import digest, theorem

FORMAT = "pcs-checked-lemma-library-v1"
PREFIX = "PCSReuseL"
LICENSES = {"Apache-2.0", "MIT", "BSD-3-Clause", "CC0-1.0"}


def reuse_priority(state, options):
    """Deterministic grounded retrieval baseline; it never decides applicability."""
    def head(expr):
        while expr["kind"] == "forall": expr = expr["children"][1]
        while expr["kind"] == "application": expr = expr["children"][0]
        return expr["value"].split(":")[0] if expr["kind"] == "constant" else ""
    catalog = {e["name"]: head(e["expression"]) for e in state.get("available_lemmas", [])}
    target = state["goals"][0]["expression"] if state["goals"] else None
    variable_binder = target and target["kind"] == "forall" and target["children"][0]["kind"] in {"sort", "constant"}
    def score(a):
        if a["kind"] == "intro" and variable_binder: return 14.0
        if a["kind"] == "witness": return 13.0
        if a["kind"] == "rfl": return 12.5
        if a["kind"] == "apply" and a["argument"] in catalog:
            expected = catalog[a["argument"]]
            return 10.0 if expected and expected == head(target) else 8.0 if not expected else -2.0
        return float(_symbolic_priority(state, a))
    return [score(a) for a in options]


def validate_library(value, heldout=()):
    if type(value) is not dict or set(value) != {"format", "entries"} or value["format"] != FORMAT:
        raise ValueError("invalid checked library envelope")
    if type(value["entries"]) is not list or len(value["entries"]) > 16:
        raise ValueError("library capacity exceeded")
    forbidden = {structural_fingerprint(t["goal"]) for t in heldout}
    seen = set()
    for index, entry in enumerate(value["entries"]):
        if type(entry) is not dict or set(entry) != {"goal", "actions", "license", "source_revision"}:
            raise ValueError("invalid lemma entry; receipts and producer flags are not accepted")
        theorem(entry["goal"])
        identity = structural_fingerprint(entry["goal"])
        if identity in forbidden or identity in seen:
            raise ValueError("evaluation theorem, alpha duplicate or duplicate library lemma")
        seen.add(identity)
        if entry["license"] not in LICENSES or type(entry["source_revision"]) is not str or not entry["source_revision"]:
            raise ValueError("cleared source provenance required")
        actions = entry["actions"]
        if type(actions) is not list or not 1 <= len(actions) <= 24:
            raise ValueError("bounded proof actions required")
        def inspect(expr):
            if expr.get("op") == "var" and expr["name"].startswith(PREFIX):
                raise ValueError("reserved library namespace")
            if expr.get("op") in {"forall", "exists"} and expr["name"].startswith(PREFIX):
                raise ValueError("reserved library namespace")
            for child in expr.values():
                if type(child) is dict: inspect(child)
        if any(b["name"].startswith(PREFIX) for b in entry["goal"]["binders"]):
            raise ValueError("reserved library namespace")
        inspect(entry["goal"]["body"])
        for action in actions:
            render_action(action)
            arg = action["argument"]
            if type(arg) is str and arg.startswith(PREFIX) and arg not in {f"{PREFIX}{i}" for i in range(index)}:
                raise ValueError("forward, cyclic or unknown lemma reference")
    return value


class LibraryEnvironment(LeanEnvironment):
    """A fixed checked library generation; untrusted actions cannot append entries."""

    def __init__(self, library, *, heldout=(), **kwargs):
        started = time.monotonic()
        library = deepcopy(validate_library(deepcopy(library), heldout))
        self._library_json = json.dumps(library, sort_keys=True, separators=(",", ":"))
        self.library_sha256 = digest(library)
        self._declarations = ""
        self.catalog = []
        self._compiled = False
        super().__init__(**kwargs)
        try:
            for i, entry in enumerate(library["entries"]):
                name = f"{PREFIX}{i}"
                proof = "\n".join("  " + render_action(a) for a in entry["actions"])
                self._declarations += f"theorem {name} : {theorem(entry['goal'])} := by\n{proof}\n"
                # _source starts a new compiler process, reconstructing preceding
                # declarations. A proof carrying sorryAx/custom axioms is rejected.
                audit = self._source(f"#pcs_audit {name}\n", "PCS_KERNEL:")
                if not set(audit["axioms"]) <= {"propext", "Classical.choice", "Quot.sound"}:
                    raise ValueError("unapproved lemma axioms")
                self.catalog.append({"name": name, "goal": entry["goal"], "kernel": audit,
                                     "proof_steps": len(entry["actions"]), "statement": theorem(entry["goal"])})
            # Compile once after every entry was independently audited. Requests
            # import this fixed module instead of elaborating the same proofs
            # repeatedly. No producer-supplied olean is ever loaded.
            self._module_dir = self.cache / ("reuse-" + self.library_sha256)
            self._module_dir.mkdir(exist_ok=True)
            self._module_source = self._module_dir / "PCSReuseActive.lean"
            self._module_olean = self._module_dir / "PCSReuseActive.olean"
            source = "import PCSProofProbe\nset_option maxHeartbeats 100000\nset_option maxRecDepth 512\n" + self._declarations
            with tempfile.NamedTemporaryFile(mode="w", dir=self._module_dir, delete=False) as temporary:
                temporary.write(source)
                staged_source = Path(temporary.name)
            staged_source.replace(self._module_source)
            with tempfile.TemporaryDirectory(prefix="module-build-", dir=self._module_dir) as build_dir:
                staged_olean = Path(build_dir) / "PCSReuseActive.olean"
                self._run(["--root=" + str(self._module_dir), "-o", str(staged_olean), str(self._module_source)], build=True)
                staged_olean.replace(self._module_olean)
            self._source_digest = hashlib.sha256(self._module_source.read_bytes()).hexdigest()
            self._olean_digest = hashlib.sha256(self._module_olean.read_bytes()).hexdigest()
            self._worker_digest = hashlib.sha256((ROOT / "formal/PCSReuseWorker.lean").read_bytes()).hexdigest()
            self._compiled = True
        except BaseException:
            self.close()
            raise
        self.construction_invocations = self.invocations + 1  # Audits plus module compilation.
        self.construction_seconds = time.monotonic() - started

    @property
    def library(self):
        return json.loads(self._library_json)

    def _source(self, text, prefix):
        if not self._compiled:
            result = super()._source(self._declarations + text, prefix)
        else:
            self._check_artifacts()
            if prefix == "PCS_STATE:":
                result = self._worker_source(text)
            else:
                with tempfile.TemporaryDirectory(prefix="checked-request-", dir=self.cache) as folder:
                    request = Path(folder) / "Request.lean"
                    request.write_text("import PCSReuseActive\nset_option maxHeartbeats 100000\nset_option maxRecDepth 512\n" + text)
                    raw = self._run([str(request)])
                    records = [json.loads(s[len(prefix):]) for s in raw.splitlines() if s.startswith(prefix)]
                    if len(records) != 1: raise RuntimeError("missing or duplicate checked-library Lean record")
                    result = records[0]
        if prefix == "PCS_STATE:":
            for state in result["states"]:
                state["available_lemmas"] = [{"name": e["name"], "expression": deepcopy(e["kernel"]["expression"])}
                                              for e in self.catalog]
        return result

    def _check_artifacts(self):
        for path, sha in [(self._module_source, self._source_digest), (self._module_olean, self._olean_digest),
                          (ROOT / "formal/PCSReuseWorker.lean", self._worker_digest)]:
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                self.close()
                raise RuntimeError("checked library source, compiled artifact or receiver changed")

    def _lean_path(self):
        if not self._compiled: return super()._lean_path()
        return str(self._module_dir) + os.pathsep + super()._lean_path()

    def _worker_file(self):
        return ROOT / "formal/PCSReuseWorker.lean" if self._compiled else super()._worker_file()

    def candidates(self, state):
        basic = candidates(state)
        if not state["goals"]:
            return basic
        # Actual applicability is decided by Lean, never by this retrieval list.
        # Global names cannot collide with a researcher-provided binder/local.
        locals_ = {l["name"] for g in state["goals"] for l in g["locals"]}
        return basic + [{"kind": "apply", "argument": e["name"]}
                        for e in self.catalog if e["name"] not in locals_]

    def observe(self, goal, actions):
        self._check_artifacts()
        return super().observe(goal, actions)

    def verify(self, goal, actions):
        result = super().verify(goal, actions)
        result.update(library_sha256=self.library_sha256,
                      library=self.library, library_declarations=self._declarations)
        return result


def collect_library(env, tasks, *, rank=None, budget=192, heldout=(), source_revision):
    """Search training tasks, independently recheck successes and freeze a library."""
    from .environment import search
    entries, records = [], []
    forbidden = {structural_fingerprint(t["goal"]) for t in heldout}
    for task in tasks:
        if task["split"] != "train" or structural_fingerprint(task["goal"]) in forbidden:
            raise ValueError("library collection may use training tasks only")
        result = search(env, task["goal"], rank, budget=budget, beam=4)
        records.append({**deepcopy(task), "result": result})
        if result["status"] == "verified":
            checked = env.verify(task["goal"], result["receipt"]["actions"])
            entries.append({"goal": deepcopy(task["goal"]), "actions": checked["actions"],
                            "license": task["license"], "source_revision": source_revision})
    library = {"format": FORMAT, "entries": entries}
    validate_library(library, heldout)
    return library, records


def replay_library_receipt(goal, receipt, *, cache=None):
    """Independent reload; reject altered library identity before final kernel replay."""
    if type(receipt) is not dict or "library" not in receipt or receipt.get("library_sha256") != digest(receipt["library"]):
        raise ValueError("receipt library identity mismatch")
    if receipt.get("goal_sha256") != digest(goal) or receipt.get("statement") != theorem(goal):
        raise ValueError("receipt does not bind the original typed goal")
    with_library = LibraryEnvironment(receipt["library"], cache=cache, timeout=30)
    try:
        fresh = with_library.verify(goal, receipt["actions"])
        for field in ["proof", "adapter_sha256", "lean", "library_sha256", "library_declarations"]:
            if fresh[field] != receipt.get(field):
                raise ValueError("receipt provenance, proof or library mismatch")
        return fresh
    finally:
        with_library.close()
