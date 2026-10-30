"""Source-control tests using real disposable Git fixtures, never verifier verdicts."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from . import reconcile as gate


@pytest.fixture
def fixture(tmp_path):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path)
    git("init", "-q")
    git("-c", "user.name=PCS fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "--allow-empty", "-qm", "Empty source-control fixture")
    base = git("rev-parse", "HEAD").decode().strip()
    source = tmp_path / "src/module.py"
    source.parent.mkdir()
    source.write_text("value = 1\n")
    git("add", ".")
    git("-c", "user.name=PCS fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "-qm", "Source-control test fixture; no implementation commit")
    head = git("rev-parse", "HEAD").decode().strip()
    identity = gate._identity(tmp_path, "src/module.py")
    prs = [dict(number=n, head=head, base=base,
                disposition="HELD" if n == 117 else "EXACT_SOURCE_COVERAGE", review="",
                files=[dict(path="src/module.py", location="src/module.py",
                            historical=identity, candidate=identity, relation="EXACT")])
           for n in [*range(1, 70), 117]]
    return tmp_path, dict(format="pcs-source-reconciliation-v12", prs=prs)


def test_real_git_bindings_do_not_confer_release_or_semantic_authority(fixture):
    root, manifest = fixture
    result = gate._verify(root, manifest)
    assert result["source_review_complete"] is True
    assert result["source_bindings_checked"] == 70
    assert result["held_prs"] == [117]
    assert result["release_ready"] is result["pcs_authority"] is result["semantic_equivalence_proved"] is False


@pytest.mark.parametrize("attack", ["missing_pr", "duplicate_pr", "missing_file", "duplicate_file",
    "historical_hash", "historical_mode", "changed_source", "source_mode", "symlink",
    "parent_symlink", "escape_path", "false_equality", "unreviewed_change", "empty_review", "erase_hold"])
def test_inventory_and_source_substitutions_fail_closed(fixture, attack):
    root, value = fixture
    value = copy.deepcopy(value)
    pr = value["prs"][0]
    item = pr["files"][0]
    source = root / "src/module.py"
    if attack == "missing_pr":
        value["prs"].pop(0)
    elif attack == "duplicate_pr":
        value["prs"][1]["number"] = pr["number"]
    elif attack == "missing_file":
        pr["files"] = []
    elif attack == "duplicate_file":
        pr["files"].append(copy.deepcopy(item))
    elif attack in {"historical_hash", "historical_mode"}:
        item["historical"]["sha256" if attack.endswith("hash") else "mode"] = "0" * 64
    elif attack == "changed_source":
        source.write_text("value = 2\n")
    elif attack == "source_mode":
        source.chmod(0o755)
    elif attack == "symlink":
        alternate = root / "alternate.py"
        alternate.write_bytes(source.read_bytes())
        source.unlink()
        source.symlink_to(alternate)
    elif attack == "parent_symlink":
        (root / "src").rename(root / "alternate")
        (root / "src").symlink_to(root / "alternate", target_is_directory=True)
    elif attack == "escape_path":
        item["location"] = "src/../src/module.py"
    elif attack == "false_equality":
        item["relation"] = "REVIEWED_CHANGE"
    elif attack == "unreviewed_change":
        source.write_text("value = 2\n")
        item["candidate"] = gate._identity(root, "src/module.py")
        item["relation"] = "REVIEWED_CHANGE"
    elif attack == "empty_review":
        pr["disposition"] = "REVIEWED_ADAPTATION"
    elif attack == "erase_hold":
        value["prs"][-1]["disposition"] = "EXACT_SOURCE_COVERAGE"
    with pytest.raises(ValueError):
        gate._verify(root, value)


def test_manifest_cannot_self_authorize_changed_sources(fixture, monkeypatch):
    root, value = fixture
    path = root / gate.MANIFEST
    path.parent.mkdir(parents=True)
    raw = json.dumps(value).encode()
    path.write_bytes(raw)
    monkeypatch.setattr(gate, "ROOT", root)
    monkeypatch.setattr(gate, "MANIFEST_SHA256", hashlib.sha256(raw).hexdigest())
    (root / "src/module.py").write_text("value = 2\n")
    for pr in value["prs"]:
        pr["files"][0]["candidate"] = gate._identity(root, "src/module.py")
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="fixed reviewed digest"):
        gate.check()


def test_duplicate_json_keys_refused():
    with pytest.raises(ValueError, match="duplicate"):
        gate._json('{"prs":[],"prs":[117]}')


def test_workflow_transformation_preserves_commands_and_job_bodies():
    old = (b"jobs:\n  actual:\n    run: |\n"
           b"      python -m research.progress_supervisor_v1.preservation\n"
           b"      PCS_REQUIRE_PROVER=1 python -m pytest -q tests\n")
    assert gate.workflow_successor(old) == old.replace(
        b"python -m research.progress_supervisor_v1.preservation",
        b"python -m research.integration_v2.boundary research.progress_supervisor_v1.preservation")


def test_unknown_phase_profile_cannot_be_substituted():
    with pytest.raises(ValueError, match="unknown predecessor"):
        gate.workflow_successor(b"python -m research.unreviewed.preservation\n")


@pytest.mark.parametrize("profile", ["local_weights_v1", "causal_firewall_v1",
                                     "relational_release_v1", "compositional_disclosure_v1"])
def test_original_phase_guards_run_on_their_exact_existing_commit(profile):
    from .phase_contracts import PHASES, historical
    result = historical(profile)
    assert result["passed"] and result["previous_files_preserved"] == PHASES[profile][1]
    assert result["evaluated_commit"] == PHASES[profile][0]
    assert result["production_authority"] is False
    assert result["scope"] == "ORIGINAL_COMMITTED_GIT_TREES_NOT_COMBINED_WORKING_TREE"


def test_unknown_historical_phase_is_refused():
    from .phase_contracts import historical
    with pytest.raises(ValueError, match="unknown historical"):
        historical("unreviewed_source")


def test_context_plugin_does_not_handle_normal_runtime_tests():
    from .pytest_phase_context import pytest_pyfunc_call
    class Normal:
        nodeid = "research/local_weights_v1/test_local.py::test_known_official_weight_revisions_are_fixed_and_fully_sized"
    assert pytest_pyfunc_call(Normal()) is None


def test_context_plugin_refuses_arbitrary_test_execution():
    from .pytest_phase_context import run_original_test
    with pytest.raises(ValueError, match="four fixed"):
        run_original_test("untrusted.py::test_invented")


@pytest.mark.parametrize("node", [
    "research/local_weights_v1/test_local.py::test_predecessor_sources_and_modes_are_unchanged",
    "research/causal_firewall_v1/test_capture.py::test_predecessor_sources_and_modes_are_preserved",
    "research/relational_release_v1/test_release.py::test_predecessor_blobs_preserved",
    "research/compositional_disclosure_v1/test_ledger.py::test_predecessor_blobs_preserved",
])
def test_source_bound_test_files_remain_exact_original_bytes(node):
    from .pytest_phase_context import NODES
    from .phase_contracts import PHASES
    commit = PHASES[NODES[node]][0]
    name = node.split("::", 1)[0]
    assert (gate.ROOT / name).read_bytes() == gate._git(gate.ROOT, "show", commit + ":" + name)


@pytest.mark.parametrize("attack", ["drop_test", "add_verdict", "remove_required_flag"])
def test_workflow_successor_cannot_hide_other_job_changes(tmp_path, attack):
    name = ".github/workflows/example.yml"
    old = b"run: PCS_REQUIRE_PROVER=1 python -m pytest -q tests\n"
    preserved = tmp_path / "docs/integration/2026-10-28/predecessor/workflows/example.yml"
    preserved.parent.mkdir(parents=True)
    preserved.write_bytes(old)
    target = tmp_path / name
    target.parent.mkdir(parents=True)
    target.write_bytes({"drop_test": b"run: true\n",
                        "add_verdict": old + b"run: echo ACCEPT\n",
                        "remove_required_flag": old.replace(b"PCS_REQUIRE_PROVER=1 ", b"")}[attack])
    manifest = dict(workflow_predecessor_tree=gate.WORKFLOW_PREDECESSOR_TREE,
                    workflow_adaptations={name: hashlib.sha256(old).hexdigest()})
    with pytest.raises(ValueError, match="outside explicit"):
        gate._workflows(tmp_path, manifest)


def test_full_core_dependency_bootstrap_retains_every_original_command():
    old=(gate.ROOT/'docs/integration/2026-10-28/predecessor/workflows/pcs-public-full-verification.yml').read_bytes()
    current=gate.workflow_successor(old,transport_dependencies=True)
    bootstrap=(b'          source scripts/activate_lean_428.sh\n'
               b'          lake exe cache get\n'
               b'          PCS_REQUIRE_TRANSPORT_KERNEL=1 PCS_REQUIRE_TRANSPORT_TRACE_KERNEL=1 bash scripts/core_ci_cloudflare.sh\n')
    assert current.count(bootstrap)==1
    assert current.replace(bootstrap,b'          bash scripts/core_ci_cloudflare.sh\n')==old


@pytest.mark.parametrize('copies',[0,2])
def test_full_core_dependency_bootstrap_refuses_ambiguous_insertion(copies):
    old=b'          bash scripts/core_ci_cloudflare.sh\n'*copies
    with pytest.raises(ValueError,match='exact full-core dependency'):
        gate.workflow_successor(old,transport_dependencies=True)


@pytest.mark.parametrize('attack',['drop_core','fake_verdict','remove_required_flag'])
def test_dependency_bootstrap_cannot_authorize_other_full_gate_changes(tmp_path,attack):
    name='.github/workflows/pcs-public-full-verification.yml'
    old=(gate.ROOT/'docs/integration/2026-10-28/predecessor/workflows/pcs-public-full-verification.yml').read_bytes()
    current=gate.workflow_successor(old,transport_dependencies=True)
    altered={'drop_core':current.replace(b'bash scripts/core_ci_cloudflare.sh',b'true'),
             'fake_verdict':current+b'run: echo ACCEPT\n',
             'remove_required_flag':current.replace(b'PCS_REQUIRE_TRANSPORT_TRACE_KERNEL=1 ',b'')}[attack]
    preserved=tmp_path/'docs/integration/2026-10-28/predecessor/workflows/pcs-public-full-verification.yml'
    preserved.parent.mkdir(parents=True);preserved.write_bytes(old)
    target=tmp_path/name;target.parent.mkdir(parents=True);target.write_bytes(altered)
    manifest=dict(workflow_predecessor_tree=gate.WORKFLOW_PREDECESSOR_TREE,
                  workflow_adaptations={name:hashlib.sha256(old).hexdigest()})
    with pytest.raises(ValueError,match='outside explicit'):
        gate._workflows(tmp_path,manifest)


@pytest.mark.parametrize("path", ["/absolute", "../escape", "src//file", "src/./file", "a\\b", "a\0b"])
def test_ambiguous_paths_refused(path):
    with pytest.raises(ValueError):
        gate._path(path)


@pytest.fixture
def pr117_history(tmp_path):
    """Real Git add/add history. These are source fixtures, never Lean verdicts."""
    def git(*args):
        return subprocess.check_output([
            "git", "-c", "user.name=PCS source fixture",
            "-c", "user.email=fixture@example.invalid", *args], cwd=tmp_path)
    git("init", "-q")
    git("commit", "--allow-empty", "-qm", "Empty source fixture")
    base = git("rev-parse", "HEAD").decode().strip()
    paths = sorted(gate.PR117_CONFLICT_PATHS) + [
        f"research/proof-gated-self-improvement-v1/source_{i}.py" for i in range(21)]
    git("checkout", "-qb", "research")
    for name in paths:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"original source fixture\n")
    git("add", ".")
    git("commit", "-qm", "Historical research source fixture")
    research = git("rev-parse", "HEAD").decode().strip()
    git("checkout", "-qb", "protected", base)
    for name in paths:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"reviewed successor fixture\n" if name in gate.PR117_CONFLICT_PATHS
                      else b"original source fixture\n")
    codec = tmp_path / "formal/PCS/V2/ProofGatedCodec.lean"
    codec.write_bytes(b"additional protected source fixture; not a Lean proof\n")
    git("add", ".")
    git("commit", "-qm", "Protected source fixture")
    protected = git("rev-parse", "HEAD").decode().strip()
    tree = git("rev-parse", "HEAD^{tree}").decode().strip()
    merged = git("commit-tree", tree, "-p", research, "-p", protected,
                 "-m", "Resolved source fixture; no verifier result").decode().strip()
    git("checkout", "-q", "--detach", merged)
    return tmp_path, dict(protected=protected, research=research), git


def test_pr117_resolution_preserves_reviewed_bytes_and_both_histories(pr117_history):
    root, refs, _ = pr117_history
    r = gate._pr117_resolution(root, **refs)
    assert r["original_paths_checked"] == 25
    assert r["unchanged_original_paths"] == 21
    assert set(r["reviewed_successors"]) == gate.PR117_CONFLICT_PATHS
    assert r["proof_family_files_checked"] == 26
    assert r["protected_main_ancestry"] and r["original_research_ancestry"]
    assert r["pcs_authority"] is r["release_ready"] is False


@pytest.mark.parametrize("name", sorted(gate.PR117_CONFLICT_PATHS))
def test_each_old_conflict_side_is_rejected_even_if_it_previously_passed(pr117_history, name):
    root, refs, git = pr117_history
    (root / name).write_bytes(git("show", refs["research"] + ":" + name))
    with pytest.raises(ValueError, match="rollback or substitution"):
        gate._pr117_resolution(root, **refs)


@pytest.mark.parametrize("attack", ["missing", "mode", "symlink", "extra_module"])
def test_pr117_deleted_replaced_and_unreviewed_sources_fail_closed(pr117_history, attack):
    root, refs, git = pr117_history
    source = root / "formal/PCS/V2/ProofGatedCodec.lean"
    if attack == "missing":
        source.unlink()
    elif attack == "mode":
        source.chmod(0o755)
    elif attack == "symlink":
        original = root / "unchanged-contents.txt"
        original.write_bytes(source.read_bytes())
        source.unlink()
        source.symlink_to(original)
    else:
        extra = root / "formal/PCS/V2/ProofGatedUnreviewed.lean"
        extra.write_text("unreviewed source fixture\n")
        git("add", str(extra.relative_to(root)))
    with pytest.raises((ValueError, OSError)):
        gate._pr117_resolution(root, **refs)


def test_identical_source_without_protected_main_ancestry_is_insufficient(pr117_history):
    root, refs, git = pr117_history
    tree = git("rev-parse", "HEAD^{tree}").decode().strip()
    detached = git("commit-tree", tree, "-p", refs["research"],
                   "-m", "Copied files without protected ancestry").decode().strip()
    git("checkout", "-q", "--detach", detached)
    with pytest.raises(ValueError, match="retain protected main ancestry"):
        gate._pr117_resolution(root, **refs)


def test_original_main_does_not_claim_that_the_held_branch_was_merged(pr117_history):
    root, refs, git = pr117_history
    git("checkout", "-q", "--detach", refs["protected"])
    r = gate._pr117_resolution(root, **refs)
    assert r["protected_main_ancestry"] and not r["original_research_ancestry"]
    assert r["release_ready"] is False


@pytest.mark.parametrize("ref", ["main", "0" * 39, "HEAD^{tree}", "../unreviewed"])
def test_pr117_references_cannot_be_selected_by_ambiguous_names(pr117_history, ref):
    root, refs, _ = pr117_history
    with pytest.raises(ValueError, match="exact reference"):
        gate._pr117_resolution(root, protected=ref, research=refs["research"])


def test_actual_pr117_source_family_retains_the_protected_versions():
    r = gate._pr117_resolution(gate.ROOT)
    assert r["original_paths_checked"] == 25
    assert len(r["reviewed_successors"]) == 4
    assert r["proof_family_files_checked"] > 25
    assert r["release_ready"] is r["pcs_authority"] is False


def test_conflict_repair_does_not_rewrite_the_frozen_manifest_or_workflows():
    manifest = gate._json((gate.ROOT / gate.MANIFEST).read_bytes())
    assert hashlib.sha256((gate.ROOT / gate.MANIFEST).read_bytes()).hexdigest() == gate.MANIFEST_SHA256
    for name in [gate.MANIFEST, *manifest["workflow_adaptations"],
                 "formal/PCS/V2/ProofGatedArtifacts.lean",
                 "formal/PCS/V2/ProofGatedAudit.lean",
                 "formal/PCS/V2/ProofGatedInference.lean"]:
        assert (gate.ROOT / name).read_bytes() == gate._git(
            gate.ROOT, "show", gate.PR117_PROTECTED_HEAD + ":" + name)
