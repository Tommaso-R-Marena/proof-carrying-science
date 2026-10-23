"""Fixed-source ordinary Lean checking of typed scientific evidence.

A trusted host and pinned Mathlib dependency cache are required. Hashes do not
create an independently controlled immutable verifier root.
"""

import hashlib, json, os, re, shutil, subprocess
from pathlib import Path
from pcs.transport_kernel_v1 import _inventory
from research.trace_lab_v1.audit import pinned_tool
from .source_gate import check as source_gate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ALLOWED = {"propext", "Classical.choice", "Quot.sound"}
RISK_NAMES = [
    "risk_closed",
    "cert_ok",
    "classifier_correct",
    "optimal_safe_experiment",
    "exact_optimal_cost",
    "initial_risk_ambiguous",
    "no_assay_cert",
    "no_assay_impossible",
]


def digest(b):
    return hashlib.sha256(b).hexdigest()


def sources():
    result = {
        p.relative_to(HERE).as_posix(): digest(p.read_bytes())
        for p in sorted(HERE.rglob("*"))
        if p.is_file()
        and (
            p.suffix in {".lean", ".py"}
            or p.name in {"lakefile.toml", "lake-manifest.json", "lean-toolchain"}
        )
        and ".lake" not in p.parts
    }
    for name in [
        "pcs/jsonio.py",
        "pcs/transport_kernel_v1.py",
        "research/trace_lab_v1/audit.py",
        "scripts/audit_lean_source.py",
    ]:
        result["@root/" + name] = digest((ROOT / name).read_bytes())
    return result


def libraries():
    found = {}
    for root in [HERE / "vendor/prism", HERE / "vendor/aion", HERE / "formal"]:
        for p in root.rglob("*.lean"):
            rel = p.relative_to(root)
            if rel.parts[0] in {"PRISM", "RequestProject", "PCSScientific"}:
                found[".".join(rel.with_suffix("").parts)] = p
    return found


def headline_names():
    result = []
    for p in [
        HERE / "vendor/prism/PRISM/AxiomAudit.lean",
        HERE / "vendor/aion/RequestProject/AION/AxiomAudit.lean",
    ]:
        result.extend(re.findall(r"^#print axioms (\S+)", p.read_text(), re.M))
    # Concrete examples get their own full integration audit; the routine
    # runtime authority needs the proved core, not enormous example proof DAGs.
    result = [
        n
        for n in result
        if not n.startswith("PRISM.Generated.")
        and not any(
            n.startswith("AION.Examples." + e + ".")
            for e in ["BDcert", "GeneCert", "XYsmall", "XYmain"]
        )
    ]
    result.extend(
        "PCSScientific." + n
        for n in [
            "checked_model_interval",
            "model_envelope",
            "terminal_query_identified",
            "identified_risk_classification",
            "optimal_identified_risk",
            "posterior_risk_interval",
        ]
    )
    result.extend("PCSScientific.RiskDemo." + n for n in RISK_NAMES)
    return result


class Authority:
    def __init__(self, out):
        source_gate()
        self.out = Path(out).resolve()
        self.out.mkdir(parents=True, exist_ok=False)
        self.frozen = sources()
        self.executions = []
        lean = shutil.which("lean")
        if not lean:
            raise ValueError("Pinned Lean4.28.0 required")
        self.lean = Path(lean).resolve()
        self.tool_sha = pinned_tool("lean", self.lean)
        pins = json.loads((HERE / "vendor/prism/lake-manifest.json").read_text())[
            "packages"
        ]
        self.packages = (ROOT / ".lake/packages").resolve()
        self.dependencies = {}
        paths = [str(self.out)]
        for p in pins:
            folder = self.packages / p["name"]
            actual = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=folder, text=True
            ).strip()
            dirty = subprocess.check_output(
                ["git", "status", "--porcelain", "--untracked-files=no"],
                cwd=folder,
                text=True,
            ).strip()
            if actual != p["rev"] or dirty:
                raise ValueError("Pinned dependency source mismatch: " + p["name"])
            self.dependencies[p["name"]] = actual
            paths.append(str(folder / ".lake/build/lib/lean"))
        self.env = {
            "PATH": str(self.lean.parent) + ":/usr/bin:/bin",
            "LEAN_PATH": ":".join(paths),
            "LANG": "C.UTF-8",
        }
        modules = libraries()
        self.modules = modules

        def core(n):
            return not (
                "Generated." in n
                or n.endswith("AxiomAudit")
                or n == "RequestProject.Main"
                or any(
                    n.endswith("." + x)
                    for x in ["BDcert", "GeneCert", "XYsmall", "XYmain"]
                )
            )

        todo = {n for n in modules if core(n)}
        done = set()

        def build(n):
            if n in done:
                return
            for dep in re.findall(
                r"^(?:public )?import (\S+)", modules[n].read_text(), re.M
            ):
                if dep in todo:
                    build(dep)
            rel = Path(*n.split(".")).with_suffix(".lean")
            p = self.out / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(modules[n].read_bytes())
            self._run(
                [
                    self.lean,
                    "-j1",
                    "-M8192",
                    "--root=" + str(self.out),
                    "-o",
                    rel.with_suffix(".olean"),
                    rel,
                ],
                240,
            )
            done.add(n)

        for n in sorted(todo):
            build(n)
        names = headline_names()
        text = (
            "import PCSScientific.RiskDemo\nimport PRISM.Examples.Families\nimport PRISM.Abstraction.Nuisance\nimport PRISM.Probabilistic.AnytimeValid\nimport RequestProject.AION.PathSemantics\nimport RequestProject.AION.NegativeResults\nimport RequestProject.AION.Examples.BirthDeath\n"
            + "\n".join("#print axioms " + n for n in names)
            + "\n"
        )
        (self.out / "Audit.lean").write_text(text)
        log = self._run(
            [self.lean, "-j1", "-M8192", "--root=" + str(self.out), "Audit.lean"], 600
        )
        self.axioms = _inventory(log, names)
        self.artifacts = {
            p.relative_to(self.out).as_posix(): digest(p.read_bytes())
            for p in self.out.rglob("*")
            if p.is_file()
        }
        self.check()
        self._save(
            "build.json",
            dict(
                sources=self.frozen,
                tool_sha256=self.tool_sha,
                dependency_revisions=self.dependencies,
                axiom_closures=self.axioms,
                host_correspondence_proved=False,
                dependency_cache_trusted=True,
                production_authority=False,
            ),
        )

    def _save(self, name, d):
        (self.out / name).write_text(json.dumps(d, indent=2) + "\n")

    def _run(self, cmd, timeout):
        p = subprocess.run(
            list(map(str, cmd)),
            cwd=self.out,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        self.executions.append(
            dict(
                command=list(map(str, cmd)),
                returncode=p.returncode,
                stdout=p.stdout,
                stderr=p.stderr,
            )
        )
        self._save("executions.json", self.executions)
        if p.returncode:
            raise ValueError(
                "Actual Lean rejected: " + p.stdout[-2000:] + p.stderr[-1000:]
            )
        return p.stdout

    def check(self):
        if self.frozen != sources() or pinned_tool("lean", self.lean) != self.tool_sha:
            raise ValueError("Reviewed source/proof-tool changed")
        if hasattr(self, "artifacts") and any(
            digest((self.out / n).read_bytes()) != h
            for n, h in self.artifacts.items()
            if n != "executions.json"
        ):
            raise ValueError("Staged source or compiled library changed")

    def _prove(self, source, names, label):
        if not re.fullmatch("[a-z][a-z0-9_]{0,79}", label):
            raise ValueError("Fresh proof label required")
        # This private method is called only by the numeric emitter in the typed
        # verifier. Neither CLI nor evidence packages accept source or tool paths.
        p = self.out / (label + ".lean")
        if p.exists():
            raise ValueError("Refusing to overwrite proof evidence")
        with p.open("x") as f:
            f.write(source)
        self.check()
        self._run(
            [
                self.lean,
                "-j1",
                "-M8192",
                "--root=" + str(self.out),
                "-o",
                p.with_suffix(".olean"),
                p,
            ],
            600,
        )
        if p.read_text() != source:
            raise ValueError("Proof bytes changed")
        object_sha = digest(p.with_suffix(".olean").read_bytes())
        audit = self.out / ("audit_" + label + ".lean")
        text = (
            "import "
            + label
            + "\n"
            + "\n".join("#print axioms " + n for n in names)
            + "\n"
        )
        audit.write_text(text)
        log = self._run(
            [self.lean, "-j1", "-M8192", "--root=" + str(self.out), audit], 600
        )
        if audit.read_text() != text:
            raise ValueError("Audit source changed")
        axioms = _inventory(log, names)
        self.check()
        if digest(p.with_suffix(".olean").read_bytes()) != object_sha:
            raise ValueError("Proof object changed during audit")
        if any(set(v) - ALLOWED for v in axioms.values()):
            raise ValueError("Forbidden proof assumptions")
        return dict(
            kernel_checked=True,
            proof_sha256=digest(source.encode()),
            proof_file=p.name,
            object_sha256=object_sha,
            audit_sha256=digest(text.encode()),
            axiom_closures=axioms,
        )
