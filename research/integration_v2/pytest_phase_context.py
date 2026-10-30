"""Run four unchanged historical source assertions in their declared Git context.

All other tests execute normally on the combined checkout. No verifier callback,
test assertion, model source inventory or captured evidence is replaced.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pytest

from . import reconcile
from .phase_contracts import PHASES

NODES = {
    "research/local_weights_v1/test_local.py::test_predecessor_sources_and_modes_are_unchanged": "local_weights_v1",
    "research/causal_firewall_v1/test_capture.py::test_predecessor_sources_and_modes_are_preserved": "causal_firewall_v1",
    "research/relational_release_v1/test_release.py::test_predecessor_blobs_preserved": "relational_release_v1",
    "research/compositional_disclosure_v1/test_ledger.py::test_predecessor_blobs_preserved": "compositional_disclosure_v1",
}


def run_original_test(node):
    if node not in NODES:
        raise ValueError("only four fixed historical source assertions are supported")
    commit = PHASES[NODES[node]][0]
    name = node.split("::", 1)[0]
    expected = reconcile._git(reconcile.ROOT, "show", commit + ":" + name)
    with tempfile.TemporaryDirectory(prefix="pcs-historical-source-test-") as folder:
        worktree = Path(folder) / "original"
        subprocess.run(["git", "worktree", "add", "--detach", str(worktree), commit],
                       cwd=reconcile.ROOT, check=True, capture_output=True, timeout=60)
        try:
            if (worktree / name).read_bytes() != expected:
                raise ValueError("historical test source differs from original Git object")
            env = {k: v for k, v in os.environ.items()
                   if k not in {"PYTEST_PLUGINS", "PYTEST_ADDOPTS", "PYTHONPATH"}}
            env["PYTHONPATH"] = str(worktree)
            report = Path(folder) / "tests.xml"
            process = subprocess.run([sys.executable, "-m", "pytest", "-q", node,
                                      "--junitxml=" + str(report)], cwd=worktree, env=env,
                                     capture_output=True, text=True, timeout=120)
            if process.returncode:
                raise RuntimeError("unchanged original source assertion failed:\n" + process.stdout + process.stderr)
            suites = list(ET.parse(report).getroot().iter("testsuite"))
            if (sum(len(s.findall("testcase")) for s in suites) != 1
                    or any(s.get(k) != "0" for s in suites for k in ("failures", "errors", "skipped"))
                    or (worktree / name).read_bytes() != expected):
                raise ValueError("one successful unchanged historical assertion required")
            return dict(historical_commit=commit, test_source_sha256=hashlib.sha256(expected).hexdigest(),
                        tests=1, failures=0, skipped=0, pcs_authority=False,
                        execution_context="ORIGINAL_GIT_TREE_NOT_COMBINED_TREE")
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)],
                           cwd=reconcile.ROOT, check=True, capture_output=True, timeout=60)


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    if pyfuncitem.nodeid not in NODES:
        return None
    manifest = reconcile.ROOT / reconcile.MANIFEST
    if not manifest.exists() and not manifest.is_symlink():
        return None  # Original phase source keeps its original behavior.
    before = reconcile.check(require_committed=True)
    result = run_original_test(pyfuncitem.nodeid)
    after = reconcile.check(require_committed=True)
    if before != after:
        raise ValueError("combined source contract changed during original assertion")
    pyfuncitem.user_properties.extend([
        ("pcs_source_assertion_context", result["execution_context"]),
        ("pcs_historical_commit", result["historical_commit"]),
        ("pcs_combined_manifest_sha256", before["manifest_sha256"]),
    ])
    return True
