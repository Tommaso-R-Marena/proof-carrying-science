"""G2 dry run, a proposal (nothing is applied): files a pull request adds cannot run before the source-integrity gates check the tree.

    python -m research.claimcheck_v1_1.governance.prepare_g2 --out docs/integration/claimcheck/g2 \
        [--site ../proof-carrying-science-site] [--pytest-python PY]

Run it with the Python the workflows use (3.12). The proposal itself is described in `g2_isolation.py`.

Everything happens in throw-away worktrees, with a local placeholder tag; all are deleted at the end.

**Core.**
* A commit with G2's workflow is made on top of the branch head. C1's dry-run control commit is built
  from it with `prepare_core_admission.build`, which then carries G2's two control edits.
* *Positive:* G2's step, read from the workflow file and run with bash as GitHub runs it, passes.
  It gives the same report as the current invocation, and the protected suites pass.
* *Fail-closed:* at the branch head without C1, G2's step fails with the same error as the current
  invocation.
* *Compatibility:* C1 + G2 + C2b passes too.
* *Attacks:* each is committed on top, then run twice, through the current invocation and through
  G2's step. Every planted module writes a marker, prints a forged success report and exits 0. The
  current invocation must show the attack working; G2's step must never run the marker and must fail.
* *Outside G2:* an edit of the gate's own source still decides what runs (G1, review). So does the
  naive launcher that puts the repository on the path after the standard library: that is why G2's
  launcher does not.

**Site** (with `--site`). On protected `main`, G2's edit of `open-pr-reconciliation.yml` passes; with a
planted `scripts/json.py`, the current step is forged and G2's is not.

Writes into DIR:
* `g2-dry-run.json`;
* `proposed-g2-core-workflow.patch`;
* `proposed-g2-core-controls.patch`, against C1's two control files;
* `proposed-g2-site.patch`.

Not an approval.
"""
from __future__ import annotations

import argparse
import importlib.machinery
import importlib.util
import json
import os
import py_compile
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

from . import g2_isolation as G2
from . import prepare_c2b as C2B
from . import prepare_core_admission as P

STEP_NAME = "Exact reviewed combined-source contract"
SITE_WORKFLOW = ".github/workflows/open-pr-reconciliation.yml"
SITE_OLD_RUN = ('      - run: |\n'
                '          python scripts/test_reconciled_prs.py\n'
                '          python scripts/check_reconciled_prs.py --site "$PWD"\n')
SITE_NEW_RUN = ('      # G2: the gate first, in isolated mode (-I), before any repository code runs\n'
                '      - run: |\n'
                '          python -I scripts/check_reconciled_prs.py --site "$PWD"\n'
                '          python scripts/test_reconciled_prs.py\n')
FORGE = '''import os, sys
open({marker!r}, "w").write("ran")
sys.stdout.write('{{"passed": true, "source_review_complete": true, "forged_by": "{name}"}}\\n')
sys.stdout.flush()
os._exit(0)
'''
EXTENSION_C = r'''#include <Python.h>
#include <stdio.h>
#include <unistd.h>
PyMODINIT_FUNC PyInit_%(init)s(void) {
    FILE *f = fopen("%(marker)s", "w");
    if (f) { fputs("ran", f); fclose(f); }
    fputs("{\"passed\": true, \"source_review_complete\": true, \"forged_by\": \"%(name)s\"}\n", stdout);
    fflush(stdout);
    _exit(0);
}
'''
G1_PROPOSAL = "docs/integration/claimcheck/g1/gate-definition-guard.core.yml"


def g1_pathspec(text: str) -> list:
    """The paths G1's proposed guard compares (read from its workflow file, so the two cannot drift)."""
    lines = text.split("git diff --name-only --no-renames", 1)[1].split(")\"", 1)[0].splitlines()[1:]
    return [line.strip().rstrip("\\").strip().strip("'") for line in lines if line.strip().rstrip("\\").strip()]


def sh(cwd: Path, script: str, env: dict, shell=("bash", "--noprofile", "--norc", "-eo", "pipefail", "-c")) -> dict:
    proc = subprocess.run([*shell, script], cwd=cwd, capture_output=True, text=True, env=env)
    return outcome(proc)


def py(cwd: Path, args: list, env: dict) -> dict:
    return outcome(subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True, env=env))


def outcome(proc) -> dict:
    try:
        out = json.loads(proc.stdout)
    except ValueError:                    # several reports (a step of two commands): the last one
        try:
            out = json.loads((proc.stdout.strip().splitlines() or ["{}"])[-1])
        except ValueError:
            out = {}
    forged = isinstance(out, dict) and "forged_by" in out
    genuine = (isinstance(out, dict) and not forged
               and (out.get("source_review_complete") is True or out.get("passed") is True))
    tail = ((proc.stderr or "").strip().splitlines() or [""])[-1][:240]
    return {"exit": proc.returncode, "reported_success": proc.returncode == 0 and (genuine or forged), "forged": forged,
            "genuine_success": proc.returncode == 0 and genuine,
            "error": out.get("error") if isinstance(out, dict) and out.get("error") else (tail or None),
            "prs_checked": out.get("prs_checked") if isinstance(out, dict) else None, "_json": out}


def after_future(text: str, code: str) -> str:
    """Insert code where a module's own statements start (after `from __future__ ...`, which must come first)."""
    line = "from __future__ import annotations\n"
    return text.replace(line, line + code, 1) if line in text else code + text


def step_script(text: str, job: str, match) -> tuple[str, str]:
    """The `run` text of a step, as GitHub's YAML parser reads it (PyYAML; else a plain-text reading)."""
    try:
        import yaml
    except ImportError:
        yaml = None
    if yaml is not None:
        for st in yaml.safe_load(text)["jobs"][job]["steps"]:
            if match(st):
                return st["run"], "PyYAML " + yaml.__version__
        raise KeyError("step not found")
    raise SystemExit("PyYAML is needed to read the workflow as GitHub does")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--site", help="a clone of the site repository (its protected main and retained-source tag)")
    ap.add_argument("--pytest-python", default=sys.executable)
    args = ap.parse_args(argv)
    out = P.ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    if P.git(P.ROOT, "status", "--porcelain"):
        raise SystemExit("commit your work first")
    head = P.git(P.ROOT, "rev-parse", "HEAD")
    work = Path(tempfile.mkdtemp(prefix="pcs-g2-dry-run-"))
    wt, markers, bindir = work / "wt", work / "markers", work / "bin"
    markers.mkdir()
    bindir.mkdir()
    (bindir / "python").symlink_to(sys.executable)            # `python` in a step is this interpreter, as setup-python's is in CI
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    env["PATH"] = f"{bindir}{os.pathsep}{env.get('PATH', '')}"
    report: dict = {"what": "DRY RUN of proposal G2 in throw-away worktrees (core: on top of C1's dry-run control commit; site: on "
                            "protected main). Nothing in either branch changed; nothing pushed; only a local placeholder tag, deleted at the "
                            "end. Not an approval.",
                    "generated_from_commit": head, "python": sys.version.split()[0]}
    site_wt = None
    try:
        P.git(P.ROOT, "worktree", "add", "--detach", str(wt), head)
        # ---- C1 + G2, built the way C1 would be built if G2 is chosen -------------------------------------------------------
        old_wf = P.show(wt, P.V22_COMMIT, G2.WORKFLOW)
        (wt / G2.WORKFLOW).write_bytes(G2.successor(old_wf))
        P.git(wt, "commit", "-q", "-am", "DRY RUN: G2's workflow on the source branch (never pushed)", env=P.FIXED)
        source = P.git(wt, "rev-parse", "HEAD")
        (out / "proposed-g2-core-workflow.patch").write_text(P.git(wt, "diff", head, source) + "\n", encoding="utf-8")
        v22_raw = (wt / P.V22).read_bytes()
        v22 = json.loads(v22_raw)
        tracked = set(P.git(wt, "ls-files", "-z").split("\0")) - {""}
        added = {n: P.identity(wt, n) for n in sorted(tracked - set(v22["snapshot"]) - set(v22["control_paths"]))}
        retained = P.retained_commit(wt, source, "clean")
        intake = retained["commit"]
        with_g2 = P.build(wt, source, intake, P.DRY_TAG, v22, v22_raw, added)
        plain = P.build(wt, head, intake, P.DRY_TAG, v22, v22_raw, added)           # C1 alone, for the control patch
        report["c1_includes_g2_only_when_the_source_carries_its_workflow"] = {
            "source_with_g2_workflow": G2.carried(wt, P.V22_COMMIT, source), "branch_head": G2.carried(wt, P.V22_COMMIT, head),
            "control_files_differ_only_in_the_gate_and_its_test": sorted(n for n in with_g2 if with_g2[n] != plain[n]) == sorted([P.GATE, P.GATE_TEST]),
            "v23_identical_with_and_without_g2": with_g2[P.V23] == plain[P.V23]}
        P.write(wt, with_g2)
        P.git(wt, "add", "-A")
        P.git(wt, "commit", "-q", "-m", "DRY RUN: C1 control commit with G2 (never pushed)", env=P.FIXED)
        base = P.git(wt, "rev-parse", "HEAD")
        # the control patch: C1's two files, then G2's edits (written from a scratch commit with C1 alone)
        P.git(wt, "checkout", "-q", "--detach", source)
        P.write(wt, {P.GATE: plain[P.GATE], P.GATE_TEST: plain[P.GATE_TEST]})
        P.git(wt, "commit", "-q", "-am", "scratch: C1's two control files alone", env=P.FIXED)
        c1_only = P.git(wt, "rev-parse", "HEAD")
        P.git(wt, "checkout", "-q", "--detach", base)
        (out / "proposed-g2-core-controls.patch").write_text(P.git(wt, "diff", c1_only, base, "--", P.GATE, P.GATE_TEST) + "\n", encoding="utf-8")
        numstat = [line.split() for line in P.git(wt, "diff", "--numstat", c1_only, base, "--", P.GATE, P.GATE_TEST).splitlines()]
        report["patches"] = {
            "proposed-g2-core-workflow.patch": {"applies_to": "the ClaimCheck branch, before C1 is regenerated", "files": [G2.WORKFLOW],
                                                "old_sha256": G2.OLD_SHA256, "new_sha256": P.sha(G2.successor(old_wf))},
            "proposed-g2-core-controls.patch": {"applies_on_top_of": "C1's reconcile.py and test_reconcile.py (built in by prepare_core_admission)",
                                                "lines_added_and_removed": {n[2]: [int(n[0]), int(n[1])] for n in numstat}}}
        P.git(P.ROOT, "tag", "-f", "-a", P.DRY_TAG, intake, "-m", "G2 dry run, local only, deleted at the end", env=P.FIXED)

        wf_text = (wt / G2.WORKFLOW).read_text(encoding="utf-8")
        g2_step, parser = step_script(wf_text, "source-policy", lambda st: st.get("name") == STEP_NAME)
        report["g2_step_as_read_from_the_workflow"] = {"parser": parser, "equals_the_reviewed_launcher": G2.LAUNCHER in g2_step,
                                                       "shell": "bash --noprofile --norc -eo pipefail (GitHub's `shell: bash`)"}

        def g2_gate(e=env):
            return sh(wt, g2_step, e)

        def old_gate(e=env):
            return py(wt, ["-m", "research.integration_v2.reconcile", "--require-committed"], e)

        def old_retained(e=env):
            return py(wt, ["scripts/check_reconciled_prs.py", "--core", str(wt)], e)

        def isolated_retained(e=env):
            return py(wt, ["-I", "scripts/check_reconciled_prs.py", "--core", str(wt)], e)

        def reset(commit=base):
            P.git(wt, "checkout", "-q", "-f", "--detach", commit)
            P.git(wt, "clean", "-qfdx")

        # ---- positive --------------------------------------------------------------------------------------------------
        reset()
        pos_g2, pos_old = g2_gate(), old_gate()
        report["positive_c1_plus_g2"] = {
            "g2_step": {k: v for k, v in pos_g2.items() if k != "_json"},
            "current_invocation": {k: v for k, v in pos_old.items() if k != "_json"},
            "same_report": pos_g2["_json"] == pos_old["_json"],
            "isolated_retained_source_gate": {k: v for k, v in isolated_retained().items() if k != "_json"},
            "gate_tests": P.suite([args.pytest_python, "-m", "pytest", "-q", "-p", "no:cacheprovider", P.GATE_TEST], wt),
            "retained_source_gate_tests": P.suite([sys.executable, "scripts/test_reconciled_prs.py"], wt)}
        reset()
        # ---- fail-closed: without C1 the gate fails, through G2's step as through the current invocation ----------------
        reset(head)
        f_g2, f_old = g2_gate(), old_gate()
        report["fail_closed_at_the_branch_head_without_c1"] = {
            "g2_step": {k: v for k, v in f_g2.items() if k != "_json"}, "current_invocation": {k: v for k, v in f_old.items() if k != "_json"},
            "same_error": f_g2["error"] == f_old["error"] and f_g2["exit"] == f_old["exit"] == 1}
        # ---- C1 + G2 + C2b ------------------------------------------------------------------------------------------------
        reset()
        g3, t3 = C2B.apply_c2b(with_g2[P.GATE].decode("utf-8"), with_g2[P.GATE_TEST].decode("utf-8"))
        (wt / P.GATE).write_text(g3, encoding="utf-8")
        (wt / P.GATE_TEST).write_text(t3, encoding="utf-8")
        P.git(wt, "commit", "-q", "-am", "DRY RUN: C2b on top of C1 + G2 (never pushed)", env=P.FIXED)
        c2b = g2_gate()
        report["compatible_with_c2b"] = {"g2_step": {k: v for k, v in c2b.items() if k != "_json"},
                                         "retained_source_reported": (c2b["_json"].get("retained_source") or {}).get("passed") is True,
                                         "gate_tests": P.suite([args.pytest_python, "-m", "pytest", "-q", "-p", "no:cacheprovider", P.GATE_TEST], wt)}
        reset()

        # ---- attacks -------------------------------------------------------------------------------------------------------
        pkg = wt / "research" / "integration_v2"

        def forge(name):
            return FORGE.format(marker=str(markers / name), name=name)

        def plant_files(files):
            def apply():
                for rel, data in files.items():
                    (wt / rel).parent.mkdir(parents=True, exist_ok=True)
                    (wt / rel).write_bytes(data if isinstance(data, bytes) else data.encode())
                return list(files)
            return apply

        def plant_pyc(name, checked):
            def apply():
                src = pkg / "reconcile.py"
                cfile = Path(importlib.util.cache_from_source(str(src)))
                cfile.parent.mkdir(parents=True, exist_ok=True)
                if checked:          # a "checked" cache entry carrying the genuine source's hash, and other code
                    from importlib import _bootstrap_external as be
                    code = compile(forge(name), str(src), "exec")
                    cfile.write_bytes(be._code_to_hash_pyc(code, importlib.util.source_hash(src.read_bytes()), checked=True))
                else:
                    tmp = work / f"{name}.py"
                    tmp.write_text(forge(name))
                    py_compile.compile(str(tmp), cfile=str(cfile), invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
                return [str(cfile.relative_to(wt))]
            return apply

        def plant_extension(name, target, init):
            def apply():
                c = work / f"{name}.c"
                c.write_text(EXTENSION_C % {"init": init, "marker": str(markers / name), "name": name})
                subprocess.run(["gcc", "-shared", "-fPIC", "-I" + sysconfig.get_paths()["include"], "-o", str(target), str(c)], check=True,
                               capture_output=True)
                return [str(target.relative_to(wt))]
            return apply

        def plant_sourceless(name, target):
            def apply():
                tmp = work / f"{name}.py"
                tmp.write_text(forge(name))
                py_compile.compile(str(tmp), cfile=str(target))
                return [str(target.relative_to(wt))]
            return apply

        pathspec = g1_pathspec((wt / G1_PROPOSAL).read_text(encoding="utf-8"))
        report["g1_pathspec_compared"] = pathspec

        def plant_pre_gate_script():
            name = "pre_gate_script_plants_bytecode"
            script = wt / "scripts" / "check_repository_integrity.py"
            cache = Path(importlib.util.cache_from_source(str(pkg / "reconcile.py")))
            tmp = work / f"{name}.py"
            tmp.write_text(forge(name))
            payload = (f"import py_compile, os\nos.makedirs({str(cache.parent)!r}, exist_ok=True)\n"
                       f"py_compile.compile({str(tmp)!r}, cfile={str(cache)!r}, invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)\n")
            script.write_text(after_future(script.read_text(), payload))
            return ["scripts/check_repository_integrity.py"]

        def run_attack(name, apply, old, kind="vulnerable", env_extra=None):
            reset()
            try:
                files = apply()
            except subprocess.CalledProcessError as exc:
                return {"not_run": f"could not build: {exc.stderr.decode()[-200:] if exc.stderr else exc}"}
            for f in files:
                P.git(wt, "add", "-f", f)
            P.git(wt, "commit", "-q", "-m", f"DRY RUN attack: {name}", env=P.FIXED)
            commit = P.git(wt, "rev-parse", "HEAD")
            flagged_by_g1 = bool(P.git(wt, "diff", "--name-only", "--no-renames", f"{base}...{commit}", "--", *pathspec))
            e = {**env, **(env_extra or {})}
            marker = markers / name
            marker.unlink(missing_ok=True)
            current = old(e)
            current_ran = marker.exists()
            marker.unlink(missing_ok=True)
            reset(commit)
            if name == "pre_gate_script_plants_bytecode":            # G2's job: the gate step, and only if it passes the steps after it
                isolated = g2_gate(e)
                if isolated["exit"] == 0:
                    py(wt, ["scripts/check_repository_integrity.py"], e)
            else:
                isolated = (isolated_retained if old is old_retained else g2_gate)(e)
            g2_ran = marker.exists()
            row = {"files": files, "env": sorted(env_extra) if env_extra else [], "kind": kind, "flagged_by_g1_paths": flagged_by_g1,
                   "current": {"planted_code_ran": current_ran, **{k: v for k, v in current.items() if k in ("exit", "reported_success", "forged")}},
                   "g2": {"planted_code_ran": g2_ran, **{k: v for k, v in isolated.items() if k in ("exit", "reported_success", "forged", "error")}}}
            if kind == "vulnerable":
                row["as_expected"] = current_ran and current["forged"] and not g2_ran and isolated["exit"] != 0 and not isolated["reported_success"]
            elif kind == "not_a_vector":
                row["as_expected"] = not current_ran and not g2_ran and isolated["exit"] != 0
            elif kind == "outside_g2":
                row["as_expected"] = g2_ran                         # shown, not prevented: G1 or review covers it
            return row

        attacks = {}
        for mod in ("json", "argparse", "hashlib", "subprocess", "pathlib", "re"):
            attacks[f"root_{mod}"] = run_attack(f"root_{mod}", plant_files({f"{mod}.py": forge(f"root_{mod}")}), old_gate)
        attacks["root_research_py"] = run_attack("root_research_py", plant_files({"research.py": forge("root_research_py")}), old_gate)
        attacks["research_init"] = run_attack("research_init", plant_files({"research/__init__.py": forge("research_init")}), old_gate)
        attacks["root_nt_fallback"] = run_attack("root_nt_fallback", plant_files({"nt.py": forge("root_nt_fallback")}), old_gate)
        attacks["gate_bytecode_unchecked"] = run_attack("gate_bytecode_unchecked", plant_pyc("gate_bytecode_unchecked", False), old_gate)
        attacks["gate_bytecode_checked_genuine_hash"] = run_attack("gate_bytecode_checked_genuine_hash",
                                                                   plant_pyc("gate_bytecode_checked_genuine_hash", True), old_gate)
        attacks["gate_init_extension"] = run_attack("gate_init_extension", plant_extension(
            "gate_init_extension", pkg / ("__init__" + importlib.machinery.EXTENSION_SUFFIXES[0]), "integration_v2"), old_gate)
        attacks["root_package_json"] = run_attack("root_package_json", plant_files({"json/__init__.py": forge("root_package_json")}), old_gate)
        attacks["root_sourceless_json_pyc"] = run_attack("root_sourceless_json_pyc", plant_sourceless("root_sourceless_json_pyc", wt / "json.pyc"),
                                                         old_gate)
        attacks["root_extension_json"] = run_attack("root_extension_json", plant_extension(
            "root_extension_json", wt / ("json" + importlib.machinery.EXTENSION_SUFFIXES[0]), "json"), old_gate)
        attacks["gate_package_shadow"] = run_attack("gate_package_shadow", plant_files({
            "research/integration_v2/reconcile/__init__.py": "", "research/integration_v2/reconcile/__main__.py": forge("gate_package_shadow")}), old_gate)
        attacks["scripts_json_retained_gate"] = run_attack("scripts_json_retained_gate",
                                                           plant_files({"scripts/json.py": forge("scripts_json_retained_gate")}), old_retained)
        envdir = work / "pythonpath"
        envdir.mkdir()
        (envdir / "json.py").write_text(forge("env_pythonpath"))
        attacks["env_pythonpath"] = run_attack("env_pythonpath", plant_files({"research/claimcheck_v1_1/ENV_PROBE.txt": "x\n"}), old_gate,
                                               env_extra={"PYTHONPATH": str(envdir)})
        attacks["pre_gate_script_plants_bytecode"] = run_attack("pre_gate_script_plants_bytecode", plant_pre_gate_script,
                                                                lambda e: (py(wt, ["scripts/check_repository_integrity.py"], e), old_gate(e))[1])
        for hook in ("sitecustomize", "usercustomize"):
            attacks[f"root_{hook}"] = run_attack(f"root_{hook}", plant_files({f"{hook}.py": forge(f"root_{hook}")}), old_gate, kind="not_a_vector")
        attacks["root_pth"] = run_attack("root_pth", plant_files({"probe.pth": f"import os; open({str(markers / 'root_pth')!r}, 'w').write('ran')\n"}),
                                         old_gate, kind="not_a_vector")
        attacks["edit_of_the_gate_itself"] = run_attack("edit_of_the_gate_itself", plant_files({
            "research/integration_v2/reconcile.py": after_future((pkg / "reconcile.py").read_text(), forge("edit_of_the_gate_itself"))}),
            old_gate, kind="outside_g2")
        report["attacks"] = attacks

        # ---- why the launcher does not put the repository on the path, even after the standard library --------------------
        naive = ("import runpy, sys\nsys.path.append(sys.argv.pop(1))\n"
                 "runpy.run_module('research.integration_v2.reconcile', run_name='__main__', alter_sys=True)\n")
        pitfall = {}
        for name, files in (("naive_nt", {"nt.py": None}), ("naive_research_py", {"research.py": None}),
                            ("naive_research_init", {"research/__init__.py": None})):
            reset()
            for rel in files:
                (wt / rel).parent.mkdir(parents=True, exist_ok=True)
                (wt / rel).write_text(forge(name))
                P.git(wt, "add", "-f", rel)
            P.git(wt, "commit", "-q", "-m", f"DRY RUN pitfall: {name}", env=P.FIXED)
            r = outcome(subprocess.run([sys.executable, "-I", "-B", "-c", naive, str(wt), "--require-committed"], cwd=wt,
                                       capture_output=True, text=True, env=env))
            pitfall[name] = {"planted_code_ran": (markers / name).exists(), "forged": r["forged"]}
        report["naive_launcher_appending_the_repository"] = {**pitfall, "all_defeated_as_expected": all(v["planted_code_ran"] for v in pitfall.values())}
        reset()

        # ---- site ------------------------------------------------------------------------------------------------------------
        if args.site:
            site = Path(args.site).resolve()
            site_wt = work / "site"
            P.git(site, "worktree", "add", "--detach", str(site_wt), "origin/main")
            site_main = P.git(site_wt, "rev-parse", "HEAD")
            text = (site_wt / SITE_WORKFLOW).read_text(encoding="utf-8")
            (site_wt / SITE_WORKFLOW).write_text(G2._once(text, SITE_OLD_RUN, SITE_NEW_RUN), encoding="utf-8")
            P.git(site_wt, "commit", "-q", "-am", "DRY RUN: G2 for the site (never pushed)", env=P.FIXED)
            site_g2 = P.git(site_wt, "rev-parse", "HEAD")
            (out / "proposed-g2-site.patch").write_text(P.git(site_wt, "diff", site_main, site_g2) + "\n", encoding="utf-8")
            job = "original-pr-ancestry-and-production-preservation"
            new_step, _ = step_script((site_wt / SITE_WORKFLOW).read_text(), job, lambda st: "check_reconciled_prs.py" in st.get("run", ""))
            old_step, _ = step_script(text, job, lambda st: "check_reconciled_prs.py" in st.get("run", ""))
            default_shell = ("bash", "-e", "-c")                    # GitHub's default `run` shell on Linux
            positive = sh(site_wt, new_step, env, default_shell)
            # the attack: a planted scripts/json.py on top of G2's commit; the current step (tests first, then the gate) and G2's
            (site_wt / "scripts" / "json.py").write_text(forge("site_scripts_json"))
            P.git(site_wt, "add", "-f", "scripts/json.py")
            P.git(site_wt, "commit", "-q", "-m", "DRY RUN attack: scripts/json.py (site)", env=P.FIXED)
            marker = markers / "site_scripts_json"
            cur = sh(site_wt, old_step, env, default_shell)
            cur_ran = marker.exists()
            marker.unlink(missing_ok=True)
            iso = sh(site_wt, new_step, env, default_shell)
            report["site"] = {
                "protected_main": site_main,
                "control_file_only": P.git(site_wt, "diff", "--name-only", site_main, site_g2).splitlines() == [SITE_WORKFLOW],
                "positive_g2_step_on_main": {k: v for k, v in positive.items() if k != "_json"},
                "attack_scripts_json": {"current": {"planted_code_ran": cur_ran, "exit": cur["exit"], "forged": cur["forged"]},
                                        "g2": {"planted_code_ran": marker.exists(), "exit": iso["exit"], "reported_success": iso["reported_success"],
                                               "error": iso["error"]}}}
            a = report["site"]["attack_scripts_json"]
            report["site"]["all_as_expected"] = (report["site"]["control_file_only"] and positive["exit"] == 0 and positive["genuine_success"]
                                                 and a["current"]["planted_code_ran"] and a["current"]["forged"]
                                                 and not a["g2"]["planted_code_ran"] and a["g2"]["exit"] != 0)

        pos = report["positive_c1_plus_g2"]
        inc = report["c1_includes_g2_only_when_the_source_carries_its_workflow"]
        report["all_as_expected"] = bool(
            inc["source_with_g2_workflow"] is True and inc["branch_head"] is False
            and inc["control_files_differ_only_in_the_gate_and_its_test"] and inc["v23_identical_with_and_without_g2"]
            and report["g2_step_as_read_from_the_workflow"]["equals_the_reviewed_launcher"]
            and pos["g2_step"]["genuine_success"] and pos["g2_step"]["prs_checked"] == 72 and pos["current_invocation"]["genuine_success"]
            and pos["same_report"] and pos["isolated_retained_source_gate"]["genuine_success"]
            and pos["gate_tests"]["exit"] == 0 and pos["retained_source_gate_tests"]["exit"] == 0
            and report["fail_closed_at_the_branch_head_without_c1"]["same_error"]
            and report["compatible_with_c2b"]["g2_step"]["genuine_success"] and report["compatible_with_c2b"]["retained_source_reported"]
            and report["compatible_with_c2b"]["gate_tests"]["exit"] == 0
            and all(v.get("as_expected") for v in attacks.values())
            and report["naive_launcher_appending_the_repository"]["all_defeated_as_expected"]
            and (not args.site or report["site"]["all_as_expected"]))
    finally:
        subprocess.run(["git", "tag", "-d", P.DRY_TAG], cwd=P.ROOT, capture_output=True)
        subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=P.ROOT, capture_output=True)
        if site_wt is not None:
            subprocess.run(["git", "worktree", "remove", "--force", str(site_wt)], cwd=Path(args.site).resolve(), capture_output=True)
    (out / "g2-dry-run.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    summary = {k: report.get(k) for k in ("generated_from_commit", "all_as_expected")}
    summary["attacks"] = {k: v.get("as_expected") for k, v in report.get("attacks", {}).items()}
    print(json.dumps(summary, indent=1))
    return 0 if report["all_as_expected"] else 1


if __name__ == "__main__":
    sys.exit(main())
