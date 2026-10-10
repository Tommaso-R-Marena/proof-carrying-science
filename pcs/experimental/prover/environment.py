"""Replay-based Lean environment with structured observations and typed actions.

No model-supplied source, imports, tactics, executable, rewards or receipts are
accepted. This is a local trusted-code tool, not a sandbox for arbitrary Lean.
"""
from __future__ import annotations

from copy import deepcopy
import json
import hashlib
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import queue
import threading
import time

from .ir import digest, theorem

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "formal/PCSProofProbe.lean"
WORKER = ROOT / "formal/PCSProofWorker.lean"
SIMPLE = {"constructor": "constructor", "assumption": "assumption", "rfl": "rfl",
          "left": "left", "right": "right", "contradiction": "contradiction"}
LEMMAS = {"Nat.add_zero", "Nat.zero_add", "Nat.add_comm", "Nat.add_assoc",
          "Nat.mul_zero", "Nat.zero_mul", "Nat.mul_comm", "Nat.mul_one", "Nat.one_mul"}
REFERENCE = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,23}(?:\.[12]){0,3}\Z")


def render_action(action):
    if type(action) is not dict or set(action) != {"kind", "argument"}:
        raise ValueError("action must have exactly kind and argument")
    k, a = action["kind"], action["argument"]
    if k in SIMPLE and a is None:
        return SIMPLE[k]
    if k == "intro" and type(a) is str and re.fullmatch(r"h[0-9]{1,2}", a):
        return "intro " + a
    if k in {"exact", "apply", "cases", "rewrite"} and type(a) is str and REFERENCE.fullmatch(a) and a.split(".")[0] not in {"sorry", "admit", "axiom", "unsafe", "native_decide"}:
        return f"rw [{a}]" if k == "rewrite" else f"{k} {a}"
    if k == "lemma" and type(a) is str and a in LEMMAS:
        return "apply " + a
    if k == "simp" and a is None:
        return "simp only [Nat.add_zero, Nat.zero_add, Nat.mul_zero, Nat.zero_mul, Nat.mul_one, Nat.one_mul]"
    if k == "witness" and type(a) is int and 0 <= a <= 8:
        return f"refine ⟨{a}, ?_⟩"
    raise ValueError("unsupported proof action")


def act(kind, argument=None):
    obj = {"kind": kind, "argument": argument}
    render_action(obj)
    return obj


def candidates(state):
    if not state["goals"]:
        return []
    g = state["goals"][0]
    def head(expr):
        while expr["kind"] == "application": expr = expr["children"][0]
        return expr["value"].split(":")[0] if expr["kind"] == "constant" else ""
    def contains(expr, sought):
        return expr == sought or any(contains(child, sought) for child in expr["children"])
    def equality_left(expr):
        if head(expr) != "Eq" or expr["kind"] != "application": return None
        return expr["children"][0]["children"][1]
    target_head = head(g["expression"])
    result = [act("assumption")]
    if g["expression"]["kind"] == "forall":
        result.insert(0, act("intro", f"h{len(g['locals'])}"))
    if target_head in {"And", "Iff", "Eq"}:
        result.append(act("constructor"))
    if target_head in {"Eq", "Iff"}: result.append(act("rfl"))
    if target_head == "Or": result.extend([act("left"), act("right")])
    if any(l["type"] == "False" for l in g["locals"]): result.append(act("contradiction"))
    for local in g["locals"]:
        name = local["name"]
        if not REFERENCE.fullmatch(name):
            continue
        if local["type"] not in {"Prop", "Nat", "Int", "Nat → Nat", "Nat → Prop"}:
            for suffix in ["", ".1", ".2", ".1.1", ".1.2", ".2.1", ".2.2"]:
                if reference_expression(state, name + suffix) is not None:
                    result.append(act("exact", name + suffix))
                    if reference_expression(state, name + suffix)["kind"] == "forall":
                        result.append(act("apply", name + suffix))
            if head(local["expression"]) == "Or": result.append(act("cases", name))
            left_side = equality_left(local["expression"])
            if left_side is not None and contains(g["expression"], left_side):
                result.append(act("rewrite", name))
    if "Nat" in g["target"] or any(l["type"] == "Nat" for l in g["locals"]):
        if "+" in g["target"] or "*" in g["target"]: result.append(act("simp"))
        result.extend(act("lemma", n) for n in sorted(LEMMAS) if ("add" in n and "+" in g["target"]) or ("mul" in n and "*" in g["target"]))
        if "∃" in g["target"]:
            result.extend(act("witness", n) for n in [0, 1, 2])
    return result[:96]


def _symbolic_priority(state, action):
    g = state["goals"][0]
    kind = action["kind"]
    if kind == "exact" and reference_expression(state, action["argument"]) == g["expression"]:
        return 12
    if kind == "exact": return -1
    if kind == "apply":
        premise = reference_expression(state, action["argument"])
        if premise and premise["kind"] == "forall" and premise["children"][1] == g["expression"]:
            return 11
    if kind == "intro":
        return 9 if g["expression"]["kind"] == "forall" else -5
    if kind == "constructor":
        return 8 if "∧" in g["target"] or "↔" in g["target"] else -3
    if kind == "lemma":
        for operation, word in [("+", "add"), ("*", "mul")]:
            pattern = r"([A-Za-z0-9_]+) " + re.escape(operation) + r" ([A-Za-z0-9_]+) = \2 " + re.escape(operation) + r" \1"
            if action["argument"] == "Nat." + word + "_comm" and re.fullmatch(pattern, g["target"]):
                return 11
    return {"assumption": 7, "exact": 6, "rfl": 5, "simp": 4, "apply": 2,
            "lemma": 1, "cases": 0, "rewrite": 3, "left": 1, "right": 1}.get(kind, -1)


def reference_expression(state, reference):
    """Structural local-premise retrieval; suggestions still require Lean checking."""
    parts = reference.split(".")
    value = next((l["expression"] for l in state["goals"][0]["locals"] if l["name"] == parts[0]), None)
    for projection in parts[1:]:
        if value is None or value["kind"] != "application":
            return None
        f, right = value["children"]
        if f["kind"] != "application":
            return None
        head, left = f["children"]
        if head["kind"] != "constant" or head["value"] != "And:[]":
            return None
        value = left if projection == "1" else right
    return value


class LeanEnvironment:
    format = "pcs-lean-environment-v1"

    def __init__(self, cache=None, timeout=10, max_steps=24):
        self.lean = shutil.which("lean")
        if not self.lean:
            raise RuntimeError("Lean 4.28 is required")
        self.version = subprocess.check_output([self.lean, "--version"], text=True).strip()
        if "version 4.28.0," not in self.version:
            raise RuntimeError("exact Lean 4.28.0 required")
        self.lean = str(Path(subprocess.check_output([self.lean, "--print-prefix"], text=True).strip()) / "bin/lean")
        self.cache = Path(cache or ROOT / ".lake/pcs-prover")
        self.cache.mkdir(parents=True, exist_ok=True)
        self.timeout, self.max_steps = timeout, max_steps
        self.source_sha = digest(SOURCE.read_text())
        compiled = self.cache / "PCSProofProbe.olean"
        pin = self.cache / "source.json"
        expected = {"source": self.source_sha, "lean": self.version}
        previous = json.loads(pin.read_text()) if pin.exists() else {}
        if (not compiled.exists() or any(previous.get(k) != v for k, v in expected.items()) or
                previous.get("olean_sha256") != hashlib.sha256(compiled.read_bytes()).hexdigest()):
            self._run(["-o", str(compiled), str(SOURCE)], build=True)
            pin.write_text(json.dumps({**expected, "olean_sha256": hashlib.sha256(compiled.read_bytes()).hexdigest()}))
        self.observations = {}
        self.invocations = 0
        self.seconds = 0.
        self.worker = None

    def close(self):
        if self.worker is not None:
            self.worker.terminate()
            try:
                self.worker.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.worker.kill()
                self.worker.wait()
            self.worker = None

    def _worker_source(self, text):
        if self.worker is None:
            command = [self.lean, "--run", str(WORKER)]
            limiter = shutil.which("prlimit")
            if limiter:
                command = [limiter, "--as=8589934592", "--cpu=1800", "--", *command]
            self.worker = subprocess.Popen(command,
                cwd=ROOT, env={"PATH": os.environ.get("PATH", ""), "LEAN_PATH": str(self.cache)},
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1)
            self.lines = queue.Queue()
            def read(stream, lines):
                for line in stream:
                    lines.put(line)
                lines.put(None)
            threading.Thread(target=read, args=(self.worker.stdout, self.lines), daemon=True).start()
        started = time.monotonic()
        self.worker.stdin.write(json.dumps(text) + "\n")
        self.worker.stdin.flush()
        records, size = [], 0
        while True:
            try:
                line = self.lines.get(timeout=max(.01, self.timeout - (time.monotonic() - started)))
            except queue.Empty:
                self.close()
                raise RuntimeError("Lean resource exhaustion") from None
            if line is None:
                self.close()
                raise RuntimeError("Lean worker terminated")
            size += len(line)
            if size > 2_000_000:
                self.close()
                raise RuntimeError("Lean output exceeds bound")
            if line.startswith("PCS_STATE:"):
                records.append(json.loads(line[len("PCS_STATE:"):]))
            if line.startswith("PCS_END:"):
                end = json.loads(line[len("PCS_END:"):])
                self.invocations += 1
                self.seconds += time.monotonic() - started
                if len(records) == 1 and records[0]["status"] == "invalid":
                    return records[0]
                if end["errors"] or len(records) != 1:
                    raise RuntimeError(str(end["errors"]))
                return records[0]

    def _run(self, arguments, build=False):
        # Credentials are not inherited by Lean, and submitted data never selects
        # a binary, imports or filesystem location. No privilege assertion is made.
        env = {"PATH": os.environ.get("PATH", ""), "LEAN_PATH": str(self.cache)}
        started = time.monotonic()
        try:
            command = [self.lean, *arguments]
            limiter = shutil.which("prlimit")
            if limiter:
                command = [limiter, "--as=8589934592", "--cpu=60", "--", *command]
            result = subprocess.run(command, cwd=SOURCE.parent if build else self.cache, env=env,
                                    text=True, capture_output=True, timeout=60 if build else self.timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError("Lean resource exhaustion") from None
        if len(result.stdout) + len(result.stderr) > 2_000_000:
            raise RuntimeError("Lean output exceeds bound")
        if result.returncode:
            raise RuntimeError((result.stdout + result.stderr)[-4000:])
        if not build:
            self.invocations += 1
            self.seconds += time.monotonic() - started
        return result.stdout

    def _source(self, text, prefix):
        if prefix == "PCS_STATE:":
            return self._worker_source(text)
        with tempfile.TemporaryDirectory(prefix="request-", dir=self.cache) as folder:
            p = Path(folder) / "Request.lean"
            p.write_text("import PCSProofProbe\nset_option maxHeartbeats 100000\nset_option maxRecDepth 512\n" + text)
            raw = self._run([str(p)])
            records = [json.loads(s[len(prefix):]) for s in raw.splitlines() if s.startswith(prefix)]
            if len(records) != 1:
                raise RuntimeError("missing or duplicate structured Lean record")
            return records[0]

    def observe(self, goal, actions):
        statement = theorem(goal)
        if type(actions) is not list or len(actions) > self.max_steps:
            raise ValueError("proof length exceeds budget")
        tactics = [render_action(a) for a in actions]
        key = digest([goal, actions])
        if key not in self.observations:
            self.observations[key] = self._source(
                f"#pcs_probe ({statement}) => [{', '.join(tactics)}]\n", "PCS_STATE:")
        return deepcopy(self.observations[key])

    def verify(self, goal, actions):
        statement = theorem(goal)
        if len(actions) > self.max_steps:
            raise ValueError("proof length exceeds budget")
        proof = "\n".join("  " + render_action(a) for a in actions)
        result = self._source(f"theorem pcs_result : {statement} := by\n{proof}\n#pcs_audit pcs_result\n", "PCS_KERNEL:")
        # The elementary fragment permits standard Lean logical foundations only.
        if not set(result["axioms"]) <= {"propext", "Classical.choice", "Quot.sound"}:
            raise RuntimeError("unapproved proof axioms")
        return {"format": "pcs-prover-proof-v1", "goal_sha256": digest(goal),
                "statement": statement, "actions": deepcopy(actions), "proof": proof,
                "kernel": result, "lean": self.version, "adapter_sha256": self.source_sha,
                "pcs_scientific_authority": False}

    def reset(self, goal):
        self._goal = deepcopy(goal)
        self._goal_hash = digest(goal)
        self._actions = []
        self._done = False
        self._state = self.observe(self._goal, [])
        return deepcopy(self._state["states"][-1]), {"goal_sha256": self._goal_hash}

    def step(self, action):
        if self._done:
            raise ValueError("episode has terminated")
        if digest(self._goal) != self._goal_hash:
            raise RuntimeError("immutable goal changed")
        proposal = self._actions + [deepcopy(action)]
        before = len(self._state["states"][-1]["goals"])
        try:
            observation = self.observe(self._goal, proposal)
        except RuntimeError as ex:
            self._done = True
            return deepcopy(self._state["states"][-1]), -0.2, False, True, {"status": "resource_exhaustion", "error": str(ex)}
        valid = observation["status"] != "invalid"
        receipt = None
        verified = False
        if valid and observation["status"] == "closed":
            try:
                receipt = self.verify(self._goal, proposal)
                verified = True
            except RuntimeError:
                valid = False
        if valid:
            self._actions, self._state = proposal, observation
        exhausted = len(proposal) >= self.max_steps
        self._done = verified or not valid or exhausted
        after = len(self._state["states"][-1]["goals"])
        reward = 1.0 if verified else (-0.2 if not valid else -0.01 + 0.02 * max(0, before - after))
        return deepcopy(self._state["states"][-1]), reward, verified or not valid, exhausted and not verified, {
            "status": "verified" if verified else "invalid" if not valid else "exhausted" if exhausted else "open",
            "receipt": receipt, "error": observation["error"]}


def search(env, goal, rank=None, budget=96, depth=18, beam=8):
    """Breadth layers, ranked actions, beam pruning; each expansion costs Lean replay."""
    goal = deepcopy(goal)
    if type(budget) is not int or not 1 <= budget <= 4096 or not 1 <= depth <= 24 or not 1 <= beam <= 32:
        raise ValueError("invalid search budget")
    initial = env.observe(goal, [])
    frontier, seen, attempts = [([], initial["states"][-1])], set(), []
    start_calls, start_time = env.invocations, time.monotonic()
    for _ in range(depth):
        next_frontier = []
        for path, state in frontier:
            options = candidates(state)
            scores = rank(deepcopy(state), deepcopy(options)) if rank else [_symbolic_priority(state, a) for a in options]
            if len(scores) != len(options) or any(type(v) not in {float, int} or not math.isfinite(v) for v in scores):
                raise ValueError("invalid policy scores")
            for index in sorted(range(len(options)), key=lambda i: (-scores[i], i))[:beam]:
                if len(attempts) >= budget:
                    break
                action = options[index]
                try:
                    observed = env.observe(goal, path + [action])
                except RuntimeError as ex:
                    attempts.append({"path": path, "action": action, "status": "resource_exhaustion", "error": str(ex)})
                    continue
                attempts.append({"path": path, "state": state, "action": action, "status": observed["status"]})
                if observed["status"] == "invalid":
                    continue
                after = observed["states"][-1]
                if observed["status"] == "closed":
                    receipt = env.verify(goal, path + [action])
                    return {"status": "verified", "receipt": receipt, "states": observed["states"],
                            "attempts": attempts, "expansions": len(attempts),
                            "lean_invocations": env.invocations - start_calls,
                            "wall_seconds": time.monotonic() - start_time}
                # Pretty goals/context are used only to suppress loops, never authorize.
                signature = digest([[g["target"], [(l["name"], l["type"]) for l in g["locals"]]] for g in after["goals"]])
                if signature not in seen:
                    seen.add(signature)
                    next_frontier.append((scores[index], path + [action], after))
            if len(attempts) >= budget:
                break
        frontier = [(p, s) for _, p, s in sorted(next_frontier, key=lambda x: -x[0])[:beam]]
        if not frontier or len(attempts) >= budget:
            break
    return {"status": "unknown", "receipt": None, "attempts": attempts,
            "expansions": len(attempts), "lean_invocations": env.invocations - start_calls,
            "wall_seconds": time.monotonic() - start_time}
