"""G2, a proposal (nothing is applied): no file a pull request adds can run before a source-integrity gate has checked the tree.

**The weakness** (independent review F2, reproduced; widened here). The CI steps run the gates in a way that
lets repository files run first:

* the manifest gate runs as `python -m research.integration_v2.reconcile` from the repository root, so the
  root is first on Python's import path;
* the retained-source gate runs as `python scripts/check_reconciled_prs.py`, so `scripts/` is first;
* in the core's required `source-policy` job, four repository scripts run before the gate.

Any of these lets a pull request make the gate report success without changing any gate file:

* a module named like one the gate imports (`json.py`, `argparse.py`, `hashlib.py`, `pathlib.py`,
  `re.py`, `subprocess.py`) at the root or in `scripts/`;
* a `research.py` at the root, or a `research/__init__.py`;
* a module the standard library tries and misses on Linux, for example `nt.py` (`pathlib` imports
  `ntpath`, which tries `nt`). This one runs even with the root placed *after* the standard library;
* cached bytecode in `research/integration_v2/__pycache__/`, which Python runs instead of the reviewed
  source;
* a compiled module beside the gate's sources, such as `__init__.<tag>.so`, which takes precedence over
  `__init__.py`;
* an edit to a script that runs before the gate.

**The smallest correction.**

* *Core, `source-policy`.* The gate becomes the job's first step after checkout and setup-python. It runs
  as `python -I -B -X pycache_prefix="$(mktemp -d)"`, through a fixed launcher of a few lines:
  * the launcher first refuses to go on unless it really runs that way;
  * isolated mode: no script directory or working directory on the path, no `PYTHON*` variables, no
    user site;
  * no bytecode read from, or written to, the repository;
  * the launcher refuses any entry beside the gate's sources other than `*.py`, `README.md` and
    `__pycache__`;
  * it puts on the import path one new directory that holds only `research/integration_v2`, a link to
    the gate's sources, so no other file of the repository can be imported.

  Two control files change, and V23 (or V22) does not:
  * `reconcile.py`, one exact reviewed successor of the workflow, bound like the receiver test repair
    (`_current_expected`, original and new SHA-256), and the `combined_source` transformation that
    inserts the new step;
  * `test_reconcile.py`, three new tests. The existing test that freezes every adapted workflow at its
    reviewed bytes now states this one change explicitly.
* *Site.* `open-pr-reconciliation.yml`, a control file of the site's retained-source gate, runs the gate
  first and as `python -I`, then the tests.

**What G2 does not cover.** A pull request that edits the workflow, or the gate's own files
(`research/integration_v2/*.py`, `scripts/check_reconciled_prs.py`), still decides what runs, because a
`pull_request` workflow runs the pull request's definition. Review, the pre-merge check, or G1 covers
that. G2 shrinks that list to those files.

**Order.** The workflow edit is part of the tree C1 admits, so the decision belongs before C1's final
regeneration:

* `prepare_core_admission.build` includes G2's control edits when, and only when, the source commit
  carries G2's workflow;
* any other change to that workflow is refused.

After C1, G2 would need a new intake of its own.
"""
from __future__ import annotations

import hashlib
import subprocess

WORKFLOW = ".github/workflows/pcs-public-full-verification.yml"
PREDECESSOR = "docs/integration/2026-10-28/predecessor/workflows/pcs-public-full-verification.yml"
OLD_SHA256 = "bb920a828812bcf3db3df4620b883a2595294db9dd9e64d11d4a0dc6b52567cf"     # V22's identity of WORKFLOW
OLD_STEP = ("      - name: Exact reviewed combined-source contract\n"
            "        run: python -m research.integration_v2.reconcile --require-committed\n")
OLD_NEEDLE = "      - name: Exercise disclosure-audit unit tests\n"
NEW_NEEDLE = "      - name: Audit revision, repository governance, and Python source\n"

# The launcher, read by `python -I -B -X pycache_prefix=<new empty directory> -` from the step's here-document.  No blank line (YAML block).
LAUNCHER = '''import os, runpy, sys, tempfile
# Refuse unless isolated (-I), not writing bytecode (-B) and reading cached bytecode only from a new, empty
# directory (-X pycache_prefix): without that, cached bytecode beside the gate's sources could replace them.
prefix = sys.pycache_prefix
if not (sys.flags.isolated and sys.flags.dont_write_bytecode and prefix and os.path.isdir(prefix) and not os.listdir(prefix)):
    sys.exit("source contract refused before the gate ran: not isolated, or no new empty bytecode directory")
root = sys.argv.pop(1)
gate = os.path.join(root, "research", "integration_v2")
# Only the gate's reviewed sources may run before it has checked the tree. A compiled module or a package
# beside them would be imported in their place, so refuse it; __pycache__ is never read (-X pycache_prefix).
unexpected = sorted(n for n in os.listdir(gate) if not n.endswith(".py") and n not in ("README.md", "__pycache__"))
if unexpected:
    sys.exit("source contract refused before the gate ran: %s beside the gate's sources" % unexpected)
# One new directory on the import path, holding only research/integration_v2 (a link to the gate's sources):
# no other file of the repository can be imported, so none can replace a module the gate imports.
view = tempfile.mkdtemp()
os.mkdir(os.path.join(view, "research"))
os.symlink(gate, os.path.join(view, "research", "integration_v2"))
sys.path.append(view)
runpy.run_module("research.integration_v2.reconcile", run_name="__main__", alter_sys=True)
'''
INVOCATION = 'python -I -B -X pycache_prefix="$(mktemp -d)" - "$PWD" --require-committed <<\'PY\'\n'


def step(launcher: str = LAUNCHER) -> str:
    return ("      - name: Exact reviewed combined-source contract\n"
            "        shell: bash\n"
            "        run: |\n"
            "          " + INVOCATION
            + "".join("          " + line for line in launcher.splitlines(True))
            + "          PY\n")


def _once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"expected exactly one occurrence of {old[:70]!r}")
    return text.replace(old, new)


def successor(old: bytes) -> bytes:
    """G2's source-policy workflow, from V22's bytes: the gate step moves to the front and becomes isolated; nothing else changes."""
    if hashlib.sha256(old).hexdigest() != OLD_SHA256:
        raise ValueError("source-policy workflow is not V22's")
    text = _once(old.decode("utf-8"), OLD_STEP, "")
    return _once(text, NEW_NEEDLE, step() + NEW_NEEDLE).encode("utf-8")


def included(old: bytes, current: bytes) -> bool:
    """False for V22's workflow, True for G2's successor; any other bytes are refused (not a reviewed change)."""
    if current == old:
        return False
    if current == successor(old):
        return True
    raise SystemExit(f"{WORKFLOW} differs from both V22 and G2's reviewed successor: not admitted")


def carried(cwd, base: str, head: str) -> bool:
    """Whether commit `head` carries G2's workflow, `base` being the protected commit with V22's: read from Git objects."""
    def blob(commit):
        return subprocess.run(["git", "cat-file", "blob", f"{commit}:{WORKFLOW}"], cwd=cwd, capture_output=True, check=True).stdout
    entry = subprocess.run(["git", "ls-tree", head, "--", WORKFLOW], cwd=cwd, capture_output=True, check=True, text=True).stdout.split()
    if entry[:2] != ["100644", "blob"]:
        raise SystemExit(f"{WORKFLOW} at {head} is not a regular non-executable file: not admitted")
    return included(blob(base), blob(head))


# ---- the two control files (on top of C1's versions; the same edits apply to main's) -------------------------------

GATE_CONSTANTS = '''
# G2: one exact reviewed CI successor. In source-policy the gate runs first, before any repository code, in
# Python's isolated mode through a fixed launcher, so that no file a pull request adds can run before the tree
# is checked: a json.py at the root, a research/__init__.py, or a compiled or cached module beside these
# sources. V22 keeps the original identity; every other job and step of the workflow is unchanged.
SOURCE_POLICY_WORKFLOW = ".github/workflows/pcs-public-full-verification.yml"
SOURCE_POLICY_OLD = "{old}"
SOURCE_POLICY_NEW = "{new}"
ISOLATED_GATE_LAUNCHER = """{launcher}"""
ISOLATED_GATE_STEP = ("      - name: Exact reviewed combined-source contract\\n"
                      "        shell: bash\\n"
                      "        run: |\\n"
                      "          " + {invocation!r}
                      + "".join("          " + line for line in ISOLATED_GATE_LAUNCHER.splitlines(True))
                      + "          PY\\n")
'''

GATE_TEST = '''

def test_g2_source_policy_runs_the_gate_first_through_the_isolated_launcher():
    """G2: the gate is the first step after checkout and setup-python, through the launcher; nothing runs before it."""
    raw = (gate.ROOT / gate.SOURCE_POLICY_WORKFLOW).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == gate.SOURCE_POLICY_NEW
    job = raw.decode().split("\\n  source-policy:\\n", 1)[1].split("\\n  core-full-gate:\\n", 1)[0]
    assert job.count(gate.ISOLATED_GATE_STEP) == 1
    before = job[:job.index(gate.ISOLATED_GATE_STEP)]
    assert before.count("\\n      - ") == 2 and "actions/checkout@" in before and "actions/setup-python@" in before and "run:" not in before
    assert "python -m research.integration_v2.reconcile" not in raw.decode()


@pytest.mark.parametrize("recorded", [{{"sha256": "0" * 64, "mode": "100644"}}, {{"sha256": gate.SOURCE_POLICY_OLD, "mode": "100755"}}])
def test_g2_workflow_successor_requires_the_exact_original_identity(recorded):
    with pytest.raises(ValueError, match="predecessor"):
        gate._current_expected(gate.SOURCE_POLICY_WORKFLOW, recorded)


def test_g2_launcher_runs_only_the_gate_sources(tmp_path):
    """The launcher on a stand-in gate: files planted where `python -m` would import them never run; the exit code passes through."""
    import sys
    pkg = tmp_path / "research" / "integration_v2"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "reconcile.py").write_text("import json, sys\\nprint(json.dumps(sys.argv[1:]))\\nraise SystemExit(7)\\n")
    marker = tmp_path / "MARKER"
    for planted in ("json.py", "research.py", "nt.py", "research/__init__.py"):
        (tmp_path / planted).write_text("open(%r, 'a').write(%r)\\n" % (str(marker), planted))

    def launch(*flags):
        return subprocess.run([sys.executable, *flags, "-", str(tmp_path), "--require-committed"],
                              input=gate.ISOLATED_GATE_LAUNCHER, capture_output=True, text=True)

    def fresh():                      # a new, empty bytecode directory for each run, as mktemp -d gives in CI
        cache = tmp_path / ("cache%d" % len(list(tmp_path.glob("cache*"))))
        cache.mkdir()
        return "pycache_prefix=" + str(cache)
    run = launch("-I", "-B", "-X", fresh())
    assert run.returncode == 7 and json.loads(run.stdout) == ["--require-committed"] and not marker.exists()
    # not isolated; writing bytecode; an empty prefix (as when mktemp fails); no prefix
    for flags in (("-B", "-X", fresh()), ("-I", "-X", fresh()), ("-I", "-B", "-X", "pycache_prefix="), ("-I", "-B")):
        run = launch(*flags)
        assert run.returncode == 1 and "no new empty bytecode directory" in run.stderr and not marker.exists(), flags
    (pkg / "__init__.abi3.so").write_bytes(b"")
    run = launch("-I", "-B", "-X", fresh())
    assert run.returncode == 1 and "beside the gate's sources" in run.stderr and not marker.exists()
'''


FROZEN_WORKFLOWS_OLD = (
    '        expected=previous.replace(b"leanprover/lean-action@24581d74d674803a25a81b10b059c5c0cdd344c6",b"leanprover/lean-action@fe408643ea7367d8c0404a8be3975bb145f5fb64") if name.startswith(".github/") else previous\n'
    '        assert (gate.ROOT/name).read_bytes()==expected\n')
FROZEN_WORKFLOWS_NEW = (
    '        expected=previous.replace(b"leanprover/lean-action@24581d74d674803a25a81b10b059c5c0cdd344c6",b"leanprover/lean-action@fe408643ea7367d8c0404a8be3975bb145f5fb64") if name.startswith(".github/") else previous\n'
    '        if name==gate.SOURCE_POLICY_WORKFLOW:   # G2, the one reviewed successor: the gate step moves first and runs isolated\n'
    '            step=b"      - name: Exact reviewed combined-source contract\\n        run: python -m research.integration_v2.reconcile --require-committed\\n"\n'
    '            first=b"      - name: Audit revision, repository governance, and Python source\\n"\n'
    '            assert expected.count(step)==1 and expected.count(first)==1\n'
    '            expected=expected.replace(step,b"").replace(first,gate.ISOLATED_GATE_STEP.encode()+first)\n'
    '            assert hashlib.sha256(expected).hexdigest()==gate.SOURCE_POLICY_NEW\n'
    '        assert (gate.ROOT/name).read_bytes()==expected\n')


def controls(gate_text: str, test_text: str, old: bytes) -> tuple[str, str]:
    """G2's edits of reconcile.py and test_reconcile.py: exact, single-occurrence replacements."""
    new = hashlib.sha256(successor(old)).hexdigest()
    anchor = 'RECEIVER_CLEANUP_NEW = "1952bd78f5f9a787a5fd1617e45dd2c75fe9d4188e87535e017e2e72317b4aba"\n'
    g = _once(gate_text, anchor, anchor + GATE_CONSTANTS.format(old=OLD_SHA256, new=new, launcher=LAUNCHER, invocation=INVOCATION))
    g = _once(g, '''def _current_expected(name, recorded):
    """Bind the reviewed test repair without changing historical classifications."""
    if name != RECEIVER_CLEANUP_TEST:''', '''def _current_expected(name, recorded):
    """Bind the reviewed test repair and G2's workflow successor without changing historical classifications."""
    if name == SOURCE_POLICY_WORKFLOW:
        if recorded != {"sha256": SOURCE_POLICY_OLD, "mode": "100644"}:
            raise ValueError("source-policy workflow successor predecessor identity differs")
        return {"sha256": SOURCE_POLICY_NEW, "mode": "100644"}
    if name != RECEIVER_CLEANUP_TEST:''')
    g = _once(g, '''        needle = "      - name: Exercise disclosure-audit unit tests\\n"
        if text.count(needle) != 1:
            raise ValueError("exact public CI source-step insertion point required")
        text = text.replace(needle, "      - name: Exact reviewed combined-source contract\\n        run: python -m research.integration_v2.reconcile --require-committed\\n" + needle)''',
              '''        needle = "      - name: Audit revision, repository governance, and Python source\\n"
        if text.count(needle) != 1:
            raise ValueError("exact public CI source-step insertion point required")
        text = text.replace(needle, ISOLATED_GATE_STEP + needle)''')
    # the protected test that freezes every adapted workflow at its reviewed bytes states G2's one change explicitly
    t = _once(test_text, FROZEN_WORKFLOWS_OLD, FROZEN_WORKFLOWS_NEW)
    return g, t.rstrip("\n") + "\n" + GATE_TEST.format()
