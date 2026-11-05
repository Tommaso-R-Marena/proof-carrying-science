"""Fast pinned-artifact integrity; full proof execution lives in research receipts."""
import gzip
import hashlib
import json
from pathlib import Path
import pytest

torch = pytest.importorskip("torch")
from pcs.experimental.prover.dag_policy_v3 import DAGPolicy
from pcs.experimental.prover.data import structural_fingerprint
from pcs.experimental.prover.induction_ir import digest

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "research/dag-policy-v3"


def read(name):
    return json.loads((FOLDER / name).read_text())


def test_frozen_domain_split_and_checkpoints():
    protocol, tasks, training = read("protocol.json"), read("tasks.json"), read("training.json")
    assert digest(tasks) == protocol["tasks_sha256"]
    assert hashlib.sha256((ROOT / protocol["training_source"]).read_bytes()).hexdigest() == protocol["training_source_sha256"]
    episodes = json.load(gzip.open(FOLDER / "checked-training.json.gz", "rt"))
    assert {e["id"] for e in episodes} == set(protocol["training_ids"])
    assert not {structural_fingerprint(e["goal"]) for e in episodes} & {structural_fingerprint(t["goal"]) for t in tasks}
    for row in training["models"]:
        model = DAGPolicy.load(FOLDER / (row["architecture"] + ".json"), row["checkpoint_sha256"])
        assert sum(p.numel() for p in model.parameters()) == row["parameters"]
        if row["architecture"] == "dag":
            assert {"edge_types.weight", "message.weight", "update.weight"} <= set(row["changed_parameters"])


def test_result_receipts_bound_to_frozen_theorems_and_no_promotion():
    tasks = {t["id"]: t for t in read("tasks.json")}
    results = json.load(gzip.open(FOLDER / "results.json.gz", "rt"))
    summary = read("summary.json")
    assert len(results) == len(tasks) * 3 == summary["comparisons"]
    assert not summary["promoted"] and not summary["scientific_authority"]
    for row in results:
        assert row["result"]["expansions"] <= 48
        if row["result"]["status"] == "verified":
            assert row["result"]["receipt"]["goal_sha256"] == digest(tasks[row["task"]]["goal"])
            assert row["independent_replay"]["proof"] == row["result"]["receipt"]["proof"]
            assert set(row["independent_replay"]["kernel"]["axioms"]) <= {"propext", "Classical.choice", "Quot.sound"}


def test_sequential_rl_positive_rewards_require_checked_terminal_receipts():
    protocol, summary = read("rl-protocol.json"), read("rl-summary.json")
    training = json.load(gzip.open(FOLDER / "rl-training.json.gz", "rt"))
    assert summary["episodes"] == protocol["episodes"] == 8
    assert training["stats"]["before"] != training["stats"]["after"]
    assert summary["weights_changed"] and not summary["promoted"]
    replayed = {r["episode"]: r["receipt"] for r in training["independent_terminal_replays"]}
    for index, episode in enumerate(training["stats"]["episodes"]):
        positives = [s for s in episode["steps"] if s["reward"] == 1.0]
        assert bool(positives) == (episode["status"] == "verified")
        for step in positives:
            assert step["status"] == "verified"
        if positives:
            assert replayed[index]["goal_sha256"] == episode["goal_sha256"]
            assert replayed[index]["proof"] == episode["receipt"]["proof"]
    DAGPolicy.load(FOLDER / "dag-rl.json", summary["checkpoint_sha256"])
    original = read("tasks.json")
    checked_training = json.load(gzip.open(FOLDER / "checked-training.json.gz", "rt"))
    assert not {structural_fingerprint(t["goal"]) for t in protocol["tasks"]} & {
        structural_fingerprint(t["goal"]) for t in original + checked_training}


def test_all_preserved_artifact_bytes_match_integrity_manifest():
    manifest = read("manifest.json")
    assert not manifest["authority"]
    for row in manifest["files"]:
        assert Path(row["path"]).name == row["path"]
        raw = (FOLDER / row["path"]).read_bytes()
        assert len(raw) == row["bytes"]
        assert hashlib.sha256(raw).hexdigest() == row["sha256"]
