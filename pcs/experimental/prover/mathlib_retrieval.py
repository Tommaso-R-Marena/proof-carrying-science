"""Bounded retrieval from real Lean 4.28/Mathlib declarations and kernel checks.

Only fixed imports and elaborator-extracted theorem names can become actions.
Raw theorem strings here are developer-owned benchmark inputs, not a public
arbitrary Lean submission service. Every result retains exact library/source
identities. Structural scoring is an untrusted retrieval heuristic.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time

from .environment import ROOT
from .induction_ir import digest

MATHLIB_REVISION = "8f9d9cff6bd728b17a24e163c9402775d9e6a365"
IMPORTS = ("Mathlib.Data.Set.Function", "Mathlib.Algebra.Group.Basic",
           "Mathlib.Data.Nat.Factorial.Basic")
PREFIXES = ("Function.Injective", "Function.Surjective", "Set.image", "Set.preimage",
            "mul_inv", "inv_mul", "inv_inv", "mul_left_cancel", "mul_right_cancel",
            "Nat.factorial", "Nat.dvd_factorial")
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}

CATALOG_COMMAND = r'''
open Lean Elab Command Meta
syntax "#pcs_external_catalog" : command
elab_rules : command
  | `(#pcs_external_catalog) => do
    liftTermElabM do
      let env ← getEnv
      let mut entries := #[]
      let prefixes := ["Function.Injective", "Function.Surjective", "Set.image", "Set.preimage", "mul_inv", "inv_mul", "inv_inv", "mul_left_cancel", "mul_right_cancel", "Nat.factorial", "Nat.dvd_factorial"]
      for (name, info) in env.constants.toList do
        let isThm := match info with | .thmInfo _ => true | _ => false
        if isThm && prefixes.any (fun p => p.isPrefixOf (toString name)) then
          entries := entries.push <| Json.mkObj [
            ("name", toJson (toString name)),
            ("type", toJson (toString (← ppExpr info.type))),
            ("expression", PCSProofProbe.expression info.type)]
      IO.println s!"PCS_EXTERNAL_CATALOG:{(toJson entries).compress}"
'''


def symbols(expression):
    result = set()
    if expression.get("kind") == "constant":
        result.add(expression["value"].split(":")[0])
    for child in expression.get("children", []):
        result |= symbols(child)
    return result


def conclusion(expression):
    while expression.get("kind") == "forall":
        expression = expression["children"][1]
    return expression


def head_name(expression):
    expression = conclusion(expression)
    while expression.get("kind") == "application":
        expression = expression["children"][0]
    return expression["value"].split(":")[0] if expression.get("kind") == "constant" else ""


class MathlibRetriever:
    def __init__(self, *, cache=None, timeout=30):
        self.mathlib = ROOT / ".lake/packages/mathlib"
        revision = subprocess.check_output(["git", "-C", str(self.mathlib), "rev-parse", "HEAD"], text=True).strip()
        if revision != MATHLIB_REVISION:
            raise RuntimeError("exact approved Mathlib revision required")
        self.lean = subprocess.check_output(["lean", "--print-prefix"], text=True).strip() + "/bin/lean"
        self.version = subprocess.check_output([self.lean, "--version"], text=True).strip()
        if "version 4.28.0," not in self.version:
            raise RuntimeError("Lean 4.28.0 required")
        self.cache = Path(cache or ROOT / ".lake/pcs-prover")
        self.cache.mkdir(parents=True, exist_ok=True)
        if not (self.cache / "PCSProofProbe.olean").exists():
            from .memory_cost import MeasuredInductionEnvironment
            env = MeasuredInductionEnvironment(cache=self.cache)
            env.close()
        self.paths = [self.cache, self.mathlib / ".lake/build/lib/lean"]
        # The root Lake workspace materializes dependency builds alongside
        # Mathlib; nested package metadata can exist without its compiled files.
        self.paths += sorted((ROOT / ".lake/packages").glob("*/.lake/build/lib/lean"))
        self.paths += sorted(self.mathlib.glob(".lake/packages/*/.lake/build/lib/lean"))
        self.timeout = timeout
        self.calls = 0
        self.seconds = 0.0
        self.import_digests = {}
        for module in IMPORTS:
            path = self.mathlib / ".lake/build/lib/lean" / (module.replace(".", "/") + ".olean")
            if not path.exists():
                raise RuntimeError("missing approved Mathlib compiled module " + module)
            self.import_digests[module] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.source_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self.catalog = self._record(CATALOG_COMMAND + "\n#pcs_external_catalog\n", "PCS_EXTERNAL_CATALOG:")
        if len(self.catalog) > 512:
            raise RuntimeError("external theorem catalog exceeds bound")
        self.catalog.sort(key=lambda entry: entry["name"])
        self.catalog_sha256 = digest(self.catalog)

    def _record(self, text, prefix):
        header = "import PCSProofProbe\n" + "".join("import " + name + "\n" for name in IMPORTS)
        header += "set_option maxHeartbeats 200000\nset_option maxRecDepth 512\n"
        self.calls += 1
        start = time.monotonic()
        try:
            with tempfile.TemporaryDirectory(prefix="mathlib-request-", dir=self.cache) as directory:
                request = Path(directory) / "Request.lean"
                request.write_text(header + text)
                command = [self.lean, str(request)]
                if subprocess.run(["which", "prlimit"], capture_output=True).returncode == 0:
                    command = ["prlimit", "--as=8589934592", "--cpu=60", "--", *command]
                output = subprocess.run(command, cwd=ROOT,
                    env={"PATH": os.environ.get("PATH", ""), "LEAN_PATH": ":".join(map(str, self.paths))},
                    text=True, capture_output=True, timeout=self.timeout)
                output_bound = 8_000_000 if prefix == "PCS_EXTERNAL_CATALOG:" else 2_000_000
                if len(output.stdout) + len(output.stderr) > output_bound:
                    raise RuntimeError("external Lean output exceeds bound")
                if output.returncode:
                    diagnostic_lines = [line for line in (output.stdout + output.stderr).splitlines()
                                        if not line.startswith(("PCS_KERNEL:", "PCS_STATE:"))]
                    raise RuntimeError("\n".join(diagnostic_lines)[-2000:])
                records = [json.loads(line[len(prefix):]) for line in output.stdout.splitlines() if line.startswith(prefix)]
                if len(records) != 1:
                    raise RuntimeError("missing unique external Lean record")
                return records[0]
        except subprocess.TimeoutExpired:
            raise RuntimeError("Mathlib resource exhaustion") from None
        finally:
            self.seconds += time.monotonic() - start

    def state(self, statement):
        self._statement(statement)
        return self._record(f"#pcs_probe ({statement}) => []\n", "PCS_STATE:")["states"][0]

    @staticmethod
    def _statement(statement):
        if type(statement) is not str or len(statement) > 2000 or "\n" in statement:
            raise ValueError("bounded single theorem type required")
        if any(word in statement for word in (":=", ";", "--", "/-", "#", "\"", "`")):
            raise ValueError("declarations, comments and code are not accepted")
        if re.search(r"\b(?:by|sorry|admit|axiom|unsafe|import|set_option|theorem|def|let)\b", statement):
            raise ValueError("only a proposition type is accepted")

    def rank(self, state, *, mode="structural", limit=12):
        if mode not in {"structural", "lexical"} or type(limit) is not int or not 1 <= limit <= 32:
            raise ValueError("invalid retrieval settings")
        goal = state["goals"][0]
        goal_symbols = symbols(goal["expression"])
        local_symbols = set().union(*(symbols(local["expression"]) for local in goal["locals"])) if goal["locals"] else set()
        target_head = head_name(goal["expression"])
        words = set(re.findall(r"[A-Za-z][A-Za-z0-9_]*", goal["target"]))
        scores = []
        for entry in self.catalog:
            if mode == "lexical":
                score = len(words & set(re.findall(r"[A-Za-z][A-Za-z0-9_]*", entry["type"] + " " + entry["name"])))
            else:
                constants = symbols(entry["expression"])
                score = 3 * len(goal_symbols & constants) + len(local_symbols & constants)
                score -= len(constants - goal_symbols - local_symbols) / 4
                # Ranking only, exact Lean apply/rewrites remain authoritative.
                score += 2 * (target_head == head_name(entry["expression"]))
            scores.append((score, entry["name"], entry))
        return [{"score": score, **entry} for score, _, entry in sorted(scores, key=lambda row: (-row[0], row[1]))[:limit]]

    def solve(self, statement, *, mode="structural", limit=12, standard=False):
        self._statement(statement)
        start = time.monotonic()
        before = self.calls
        state = self.state(statement)
        binder_count = 0
        body = state["goals"][0]["expression"]
        while body["kind"] == "forall":
            binder_count += 1
            body = body["children"][1]
        introductions = "\n  ".join(["intro"] * binder_count)
        retrieval_start = time.monotonic()
        selected = self.rank(state, mode=mode, limit=limit)
        retrieval_seconds = time.monotonic() - retrieval_start
        proposals = [("standard_" + tactic, "repeat intro\n  " + tactic) for tactic in ("simp_all", "omega", "aesop")] if standard else []
        if not standard:
            # Apply is elaborator-controlled and exposes unmet premises. Rewrites
            # cannot certify a different proposition; final audit uses exact type.
            for entry in selected:
                name = entry["name"]
                proposals += [(name + ":apply", f"{introductions}\n  first | exact {name} | apply {name}\n  all_goals assumption"),
                              (name + ":rewrite", f"{introductions}\n  rw [{name}]\n  all_goals rfl")]
        attempts = []
        receipt = None
        for action, proof in proposals:
            try:
                kernel = self._record(f"theorem pcs_external_result : {statement} := by\n  {proof}\n#pcs_audit pcs_external_result\n", "PCS_KERNEL:")
                if not set(kernel["axioms"]) <= ALLOWED_AXIOMS:
                    raise RuntimeError("unapproved theorem axioms")
                # Fresh compiler independently reconstructs the same proposition.
                fresh = self._record(f"theorem pcs_external_replay : {statement} := by\n  {proof}\n#pcs_audit pcs_external_replay\n", "PCS_KERNEL:")
                if fresh != kernel:
                    raise RuntimeError("independent kernel audit differs")
                receipt = {"statement": statement, "proof": "  " + proof, "kernel": kernel,
                           "independent_kernel": fresh, "goal_sha256": digest(statement),
                           "mathlib_revision": MATHLIB_REVISION, "imports": list(IMPORTS),
                           "import_artifact_sha256": self.import_digests,
                           "catalog_sha256": self.catalog_sha256, "retrieval_source_sha256": self.source_sha256,
                           "winning_action": action, "lean": self.version, "pcs_scientific_authority": False}
                attempts.append({"action": action, "status": "verified"})
                break
            except RuntimeError as error:
                attempts.append({"action": action, "status": "failed", "error": str(error)[-1000:]})
        return {"status": "verified" if receipt else "unknown", "receipt": receipt,
                "mode": "standard_tactics" if standard else mode, "retrieved": [{"name": e["name"], "score": e["score"]} for e in selected],
                "attempts": attempts, "cost": {"physical_lean_calls": self.calls - before,
                "retrieval_seconds": retrieval_seconds, "wall_seconds": time.monotonic() - start},
                "pcs_scientific_authority": False}
